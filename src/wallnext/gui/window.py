"""The main window: the sources, and one page per feature using them."""

import threading
from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QCloseEvent
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
from wallnext import scheduler
from wallnext.exceptions import WallnextError
from wallnext.gui import about
from wallnext.gui.history import HistoryDialog
from wallnext.gui.sources import SOURCES, Source
from wallnext.gui.widgets import (
    Card,
    Navigation,
    Preview,
    secondary,
    section_title,
    stacked,
)
from wallnext.refresh import refresh
from wallnext.sources import identify
from wallnext.wallpaper import current_wallpaper

_SAVE_DELAY_MS = 600
_STATUS_POLL_MS = 5000
# Room taken by a checkbox's box, so text under it lines up with its label.
_CHECKBOX_INDENT = 28


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
    def __init__(self) -> None:
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

        # Segoe Fluent Icons code points: Globe, Personalize, TVMonitor, Info.
        navigation = Navigation()
        navigation.add_page("Sources", "", self._sources())
        navigation.add_page(
            "Wallpaper", "", self._header(), self._actions(), self._schedule()
        )
        navigation.add_page("Screensaver", "", self._screensaver())
        navigation.add_page("About", "", *about.sections(self))
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
            enabled = QCheckBox(source.name)
            enabled.setChecked(self._settings.source(source.key).enabled)
            enabled.toggled.connect(
                lambda on, key=source.key: self._enable_source(key, on)
            )
            summary = secondary(source.summary(self._settings))
            summary.setIndent(_CHECKBOX_INDENT)  # line up with the name, not the box
            self._summaries.append((source, summary))
            configure = None
            if source.dialog:
                configure = QPushButton("Configure…")
                configure.clicked.connect(lambda _=False, s=source: self._configure(s))
            card.add_row(stacked(enabled, summary), configure)
        self._no_source = secondary("No source enabled: nothing to pick from.")
        self._sync_no_source()
        intro = secondary(
            "Each new picture comes from one of the enabled sources, at random."
        )
        return stacked(intro, card, self._no_source)

    def _schedule(self) -> QWidget:
        self._enabled = QCheckBox("Change the wallpaper automatically")
        self._enabled.toggled.connect(self._on_toggle)
        hint = secondary(
            "Windows does it in the background, even with this window closed."
        )
        hint.setIndent(_CHECKBOX_INDENT)
        self._interval = QSpinBox(minimum=1, maximum=7 * 24 * 60, suffix=" min")
        self._interval.setValue(max(1, self._settings.interval_seconds // 60))
        self._interval.setMinimumWidth(120)
        self._interval.valueChanged.connect(self._save_timer.start)

        card = Card()
        card.add_row(stacked(self._enabled, hint))
        card.add_row(QLabel("Every"), self._interval)
        return stacked(section_title("Schedule"), card)

    def _screensaver(self) -> QWidget:
        card = Card()
        card.add_row(
            stacked(
                QLabel("Coming soon"),
                secondary("A screensaver showing pictures from your sources."),
            )
        )
        return card

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
