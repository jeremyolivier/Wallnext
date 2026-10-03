"""The main window: current wallpaper, sources and schedule."""

import os
import threading
from collections.abc import Callable

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QCloseEvent, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
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
from wallnext.gui.sources import SOURCES, Source
from wallnext.gui.widgets import Preview
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
            refresh(settings, settings.download_dir, settings.keep)
        except WallnextError as e:
            self.failed.emit(str(e))
        else:
            self.done.emit()


class SettingsWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Wallnext")
        self.setMinimumWidth(520)
        self._settings = cfg.load()
        self._summaries: list[tuple[Source, QLabel]] = []

        self._save_timer = QTimer(self, singleShot=True, interval=_SAVE_DELAY_MS)
        self._save_timer.timeout.connect(self._save_schedule)
        self._poll = QTimer(self, interval=_STATUS_POLL_MS)
        self._poll.timeout.connect(self._refresh_status)
        self._refresher = _Refresher(self)
        self._refresher.done.connect(self._on_refreshed)
        self._refresher.failed.connect(self._on_refresh_failed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addWidget(self._header())
        layout.addLayout(self._actions())
        layout.addWidget(self._sources())
        layout.addWidget(self._schedule())
        layout.addStretch()

        self._refresh_status()
        self._poll.start()

    # --- sections ---------------------------------------------------------

    def _header(self) -> Preview:
        self._preview = Preview()
        return self._preview

    def _actions(self) -> QHBoxLayout:
        self._next = QPushButton("Next wallpaper")
        self._next.setDefault(True)
        self._next.clicked.connect(self._next_wallpaper)
        open_folder = QPushButton("Open folder")
        open_folder.clicked.connect(lambda: os.startfile(self._settings.download_dir))
        row = QHBoxLayout()
        row.addWidget(self._next)
        row.addWidget(open_folder)
        row.addStretch()
        return row

    def _sources(self) -> QGroupBox:
        box = QGroupBox("Sources")
        layout = QVBoxLayout(box)
        for source in SOURCES:
            enabled = QCheckBox(source.name)
            bold = QFont(enabled.font())
            bold.setWeight(QFont.Weight.DemiBold)
            enabled.setFont(bold)
            enabled.setChecked(self._settings.source(source.key).enabled)
            enabled.toggled.connect(
                lambda on, key=source.key: self._enable_source(key, on)
            )
            summary = QLabel(source.summary(self._settings))
            summary.setEnabled(False)  # dimmed, as secondary text
            self._summaries.append((source, summary))
            text = QVBoxLayout()
            text.setSpacing(2)
            text.addWidget(enabled)
            text.addWidget(summary)

            row = QHBoxLayout()
            row.addLayout(text, 1)
            if source.dialog:
                configure = QPushButton("Configure…")
                configure.clicked.connect(lambda _=False, s=source: self._configure(s))
                row.addWidget(configure, alignment=Qt.AlignmentFlag.AlignVCenter)
            layout.addLayout(row)
        self._no_source = QLabel(
            "No source enabled: the wallpaper will not change.", wordWrap=True
        )
        layout.addWidget(self._no_source)
        self._sync_no_source()
        return box

    def _schedule(self) -> QGroupBox:
        self._enabled = QCheckBox("Change the wallpaper automatically")
        self._enabled.toggled.connect(self._on_toggle)
        self._interval = QSpinBox(minimum=1, maximum=7 * 24 * 60, suffix=" min")
        self._interval.setValue(max(1, self._settings.interval_seconds // 60))
        self._keep = QSpinBox(minimum=1, maximum=1000, value=self._settings.keep)
        for spin in (self._interval, self._keep):
            spin.valueChanged.connect(self._save_timer.start)

        box = QGroupBox("Schedule")
        form = QFormLayout(box)
        form.addRow(self._enabled)
        form.addRow("Every", self._interval)
        form.addRow("Wallpapers kept on disk", self._keep)
        hint = QLabel(
            "Windows changes the wallpaper in the background, even when this "
            "window is closed.",
            wordWrap=True,
        )
        hint.setEnabled(False)
        form.addRow(hint)
        return box

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
            update={
                "interval_seconds": self._interval.value() * 60,
                "keep": self._keep.value(),
            }
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
        self._preview.set_caption("Wallnext", status)

    # --- actions ----------------------------------------------------------

    def _next_wallpaper(self) -> None:
        self._flush_save()
        self._next.setEnabled(False)
        self._next.setText("Fetching…")
        self._refresher.start(self._settings)

    def _on_refreshed(self) -> None:
        self._next.setEnabled(True)
        self._next.setText("Next wallpaper")
        self._refresh_status()

    def _on_refresh_failed(self, message: str) -> None:
        self._on_refreshed()
        QMessageBox.warning(self, "Wallnext", message)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._flush_save()
        super().closeEvent(event)
