"""Screensaver page: turn it on, its delay, the pictures it can show, a preview."""

import subprocess
import sys
import threading
from collections.abc import Callable

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from wallnext import config as cfg
from wallnext.exceptions import WallnextError
from wallnext.gui.widgets import Card, row_text, secondary
from wallnext.screensaver import cache, windows

# Pictures fetched by "Get more", and when turning it on with none ready.
_FILL_COUNT = 10
_DEFAULT_DELAY = 10  # minutes


class _Filler(QObject):
    """Downloads pictures for the screensaver off the UI thread."""

    done = Signal(int)

    def start(self, settings: cfg.Settings) -> None:
        threading.Thread(target=self._run, args=(settings,), daemon=True).start()

    def _run(self, settings: cfg.Settings) -> None:
        self.done.emit(cache.fill(settings, _FILL_COUNT))


def _preview_command() -> list[str]:
    scr = windows.scr_path()
    if scr is not None:
        return [str(scr), "/s"]
    return [sys.executable, "-m", "wallnext.screensaver"]  # from source


class ScreensaverPage(QWidget):
    def __init__(self, settings: Callable[[], cfg.Settings]) -> None:
        super().__init__()
        self._settings = settings
        installed = windows.scr_path() is not None

        self._enabled = QCheckBox()
        self._enabled.setChecked(windows.is_enabled())
        self._enabled.setEnabled(installed)
        self._enabled.toggled.connect(self._on_toggle)
        hint = (
            "A slideshow of pictures from your sources when the computer is idle. "
            "Any key or mouse move closes it on every screen."
            if installed
            else "Available in the installed app."
        )

        self._delay = QSpinBox(minimum=1, maximum=120, suffix=" min")
        self._delay.setValue(
            windows.timeout_minutes() if windows.is_enabled() else _DEFAULT_DELAY
        )
        self._delay.setMinimumWidth(120)
        self._delay.editingFinished.connect(self._on_delay)

        self._count = secondary("")
        self._more = QPushButton("Get more")
        self._more.clicked.connect(self._fill)
        self._filler = _Filler(self)
        self._filler.done.connect(self._on_filled)

        preview = QPushButton("Preview")
        preview.clicked.connect(lambda: subprocess.Popen(_preview_command()))

        card = Card()
        card.add_row(row_text("Use Wallnext as screensaver", hint), self._enabled)
        card.add_row(row_text("Start after"), self._delay)
        card.add_row(row_text("Pictures ready", self._count), self._more)
        card.add_row(row_text("Preview", "Move the mouse to close it."), preview)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(card)
        self._show_count()

    def _show_count(self) -> None:
        self._count.setText(
            f"{len(cache.pictures())} of {cache.MAX_PICTURES}; each new wallpaper "
            "is added while the screensaver is on"
        )

    def _on_toggle(self, on: bool) -> None:
        try:
            if on:
                windows.enable(self._delay.value())
                if not cache.pictures():
                    self._fill()
            else:
                windows.disable()
        except WallnextError as e:
            QMessageBox.warning(self, "Wallnext", str(e))
        self._enabled.blockSignals(True)
        self._enabled.setChecked(windows.is_enabled())
        self._enabled.blockSignals(False)

    def _on_delay(self) -> None:
        if windows.is_enabled():
            windows.set_timeout(self._delay.value())

    def _fill(self) -> None:
        self._more.setEnabled(False)
        self._more.setText("Getting…")
        self._filler.start(self._settings())

    def _on_filled(self, added: int) -> None:
        self._more.setEnabled(True)
        self._more.setText("Get more")
        self._show_count()
        if not added:
            QMessageBox.warning(
                self, "Wallnext", "No picture could be downloaded from your sources."
            )
