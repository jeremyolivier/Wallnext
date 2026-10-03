"""The main window: the sources, and one page per feature using them."""

import threading
from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QCloseEvent, QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from wallnext import config as cfg
from wallnext import lockscreen, scheduler
from wallnext.exceptions import WallnextError
from wallnext.gui import about, theme
from wallnext.gui.history import HistoryDialog
from wallnext.gui.screensaver import ScreensaverPage
from wallnext.gui.sources import SOURCES, Source
from wallnext.gui.widgets import (
    Card,
    Navigation,
    Preview,
    glyph_icon,
    restyle,
    row_text,
    secondary,
    section_title,
    stacked,
)
from wallnext.refresh import refresh
from wallnext.sources import identify
from wallnext.wallpaper import current_wallpaper

_SAVE_DELAY_MS = 600
_STATUS_POLL_MS = 5000


def _interval_label(minutes: int) -> str:
    if minutes % (24 * 60) == 0:
        days = minutes // (24 * 60)
        return f"{days} day" + ("s" if days > 1 else "")
    if minutes % 60 == 0:
        return f"{minutes // 60} h"
    return f"{minutes} min"


class _Refresher(QObject):
    """Fetches and applies a wallpaper off the UI thread."""

    done = Signal()
    failed = Signal(str)

    def start(self, settings: cfg.Settings) -> None:
        threading.Thread(target=self._run, args=(settings,), daemon=True).start()

    def _run(self, settings: cfg.Settings) -> None:
        try:
            refresh(settings, settings.download_dir)
        except WallnextError as e:
            self.failed.emit(str(e))
        else:
            self.done.emit()


class SettingsWindow(QWidget):
    def __init__(self, page: str | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Wallnext")
        self.setMinimumWidth(780)
        self._settings = cfg.load()
        self._summaries: list[tuple[Source, QLabel]] = []

        self._save_timer = QTimer(self, singleShot=True, interval=_SAVE_DELAY_MS)
        self._save_timer.timeout.connect(self._save_schedule)
        self._poll = QTimer(self, interval=_STATUS_POLL_MS)
        self._poll.timeout.connect(self._refresh_status)
        self._refresher = _Refresher(self)
        self._refresher.done.connect(self._on_next_done)
        self._refresher.failed.connect(self._on_next_failed)

        # Segoe Fluent Icons code points: Globe, Personalize, TVMonitor, Info;
        # colored like the icons of Windows 11's Settings.
        navigation = Navigation()
        navigation.add_page("Sources", "", "#0078D4", self._sources())
        navigation.add_page(
            "Wallpaper",
            "",
            "#8764B8",
            self._header(),
            self._actions(),
            self._schedule(),
        )
        navigation.add_page(
            "Screensaver", "", "#00A3A3", ScreensaverPage(lambda: self._settings)
        )
        navigation.add_page("About", "", "#7A7574", *about.sections(self))
        self._theme = QPushButton(flat=True)
        self._theme.setToolTip("Light or dark: follow Windows, or force one")
        self._theme.clicked.connect(self._next_theme)
        self._show_theme()
        navigation.add_footer(self._theme)
        QGuiApplication.styleHints().colorSchemeChanged.connect(
            lambda _: QTimer.singleShot(0, self._on_theme_changed)
        )
        if page:
            navigation.select(page)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(navigation)

        self._refresh_status()
        self._poll.start()

    # --- sections ---------------------------------------------------------

    def _header(self) -> Preview:
        self._preview = Preview()
        return self._preview

    def _actions(self) -> QWidget:
        self._next = QPushButton("Next wallpaper")
        self._next.setDefault(True)
        self._next.clicked.connect(self._next_wallpaper)
        show_history = QPushButton("History…")
        show_history.clicked.connect(lambda: HistoryDialog(self).exec())
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._next)
        layout.addWidget(show_history)
        layout.addStretch()
        return row

    def _sources(self) -> QWidget:
        card = Card()
        for source in SOURCES:
            enabled = QCheckBox()
            enabled.setChecked(self._settings.source(source.key).enabled)
            enabled.toggled.connect(
                lambda on, key=source.key: self._enable_source(key, on)
            )
            summary = secondary(source.summary(self._settings))
            self._summaries.append((source, summary))
            configure = None
            if source.dialog:
                configure = QPushButton("Configure…")
                configure.clicked.connect(lambda _=False, s=source: self._configure(s))
            card.add_row(
                row_text(source.name, summary, source.logo), configure, enabled
            )
        self._no_source = secondary("No source enabled: nothing to pick from.")
        self._sync_no_source()
        intro = secondary(
            "Each new picture comes from one of the enabled sources, at random."
        )
        return stacked(intro, card, self._no_source)

    def _schedule(self) -> QWidget:
        self._enabled = QCheckBox()
        self._enabled.toggled.connect(self._on_toggle)
        self._interval = QSpinBox(minimum=1, maximum=7 * 24 * 60, suffix=" min")
        self._interval.setValue(max(1, self._settings.interval_seconds // 60))
        self._interval.setMinimumWidth(120)
        self._interval.valueChanged.connect(self._save_timer.start)

        self._lock_screen = QCheckBox()
        self._lock_screen.setChecked(self._settings.lock_screen)
        self._lock_screen.toggled.connect(self._on_lock_screen)

        card = Card()
        card.add_row(
            row_text(
                "Change the wallpaper automatically",
                "Windows does it in the background, even with this window closed.",
            ),
            self._enabled,
        )
        card.add_row(row_text("Every"), self._interval)
        card.add_row(
            row_text(
                "Lock screen", "Use each new wallpaper as the lock screen picture too."
            ),
            self._lock_screen,
        )
        return stacked(section_title("Schedule"), card)

    # --- sources ----------------------------------------------------------

    def _enable_source(self, key: str, on: bool) -> None:
        self._flush_save()
        self._settings = self._settings.with_source(key, enabled=on)
        cfg.save(self._settings)
        self._sync_no_source()

    def _sync_no_source(self) -> None:
        self._no_source.setVisible(
            not any(self._settings.source(s.key).enabled for s in SOURCES)
        )

    def _configure(self, source: Source) -> None:
        assert source.dialog  # only sources with a dialog get the button
        self._flush_save()
        dialog = source.dialog(self._settings, self)
        if dialog.exec():
            self._settings = dialog.settings()
            cfg.save(self._settings)
            for entry, summary in self._summaries:
                summary.setText(entry.summary(self._settings))

    # --- schedule ---------------------------------------------------------

    def _save_schedule(self) -> None:
        settings = self._settings.model_copy(
            update={"interval_seconds": self._interval.value() * 60}
        )
        cfg.save(settings)
        # The interval lives in the scheduled task's trigger.
        interval_changed = settings.interval_seconds != self._settings.interval_seconds
        self._settings = settings
        if interval_changed and scheduler.is_installed():
            self._run(lambda: scheduler.set_interval(settings.interval_seconds))

    def _flush_save(self) -> None:
        if self._save_timer.isActive():
            self._save_timer.stop()
            self._save_schedule()

    def _next_theme(self) -> None:
        self._flush_save()
        self._settings = self._settings.model_copy(
            update={"theme": theme.following(self._settings.theme)}
        )
        cfg.save(self._settings)
        theme.apply(self._settings.theme)
        self._show_theme()

    def _on_theme_changed(self) -> None:
        restyle(self)

    def _show_theme(self) -> None:
        current = self._settings.theme
        self._theme.setText(f"Theme: {theme.LABELS[current]}")
        self._theme.setIcon(
            glyph_icon(theme.GLYPHS[current], self, theme.COLORS[current])
        )

    def _on_lock_screen(self, on: bool) -> None:
        self._flush_save()
        self._settings = self._settings.model_copy(update={"lock_screen": on})
        cfg.save(self._settings)
        wallpaper = current_wallpaper()
        if on and wallpaper:  # don't wait for the next change
            self._run(lambda: lockscreen.set_picture(wallpaper))

    def _on_toggle(self, on: bool) -> None:
        self._flush_save()
        if not on:
            self._run(scheduler.stop)
        elif scheduler.is_installed():
            self._run(scheduler.start)
        else:
            self._run(lambda: scheduler.install(self._settings.interval_seconds))

    def _run(self, action: Callable[[], object]) -> None:
        try:
            action()
        except WallnextError as e:
            QMessageBox.warning(self, "Wallnext", str(e))
        self._refresh_status()

    def _refresh_status(self) -> None:
        wallpaper = current_wallpaper()
        self._preview.set_image(wallpaper)
        origin = identify(wallpaper) if wallpaper else None
        if origin:
            source, url = origin
            self._preview.set_link(f"View on {source.name}", url)
        else:
            self._preview.set_link("", None)

        state = None
        if scheduler.is_installed():
            try:
                state = scheduler.status()
            except WallnextError:
                pass
        active = state is not None and state.state != scheduler.State.DISABLED
        # Reflect the task without re-triggering _on_toggle.
        self._enabled.blockSignals(True)
        self._enabled.setChecked(active)
        self._enabled.blockSignals(False)

        if state is None:
            status = "Automatic refresh off"
        elif not active:
            status = "Paused"
        else:
            every = _interval_label(self._interval.value())
            when = f"{state.next_run:%H:%M}" if state.next_run else "—"
            status = f"Every {every} · next at {when}"
        self._preview.set_caption("Current wallpaper", status)

    # --- actions ----------------------------------------------------------

    def _next_wallpaper(self) -> None:
        self._flush_save()
        self._next.setEnabled(False)
        self._next.setText("Fetching…")
        self._refresher.start(self._settings)

    def _on_next_done(self) -> None:
        self._reset_next_button()
        if self._enabled.isChecked():
            self._run(
                lambda: scheduler.restart_countdown(self._settings.interval_seconds)
            )
        else:
            self._refresh_status()

    def _on_next_failed(self, message: str) -> None:
        self._reset_next_button()
        self._refresh_status()
        QMessageBox.warning(self, "Wallnext", message)

    def _reset_next_button(self) -> None:
        self._next.setEnabled(True)
        self._next.setText("Next wallpaper")

    def closeEvent(self, event: QCloseEvent) -> None:
        self._flush_save()
        super().closeEvent(event)
