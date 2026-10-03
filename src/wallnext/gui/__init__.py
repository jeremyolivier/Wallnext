"""Settings window, opened when wallnext is launched without a command."""

import sys

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from wallnext import config as cfg
from wallnext.gui import theme
from wallnext.gui.window import SettingsWindow

# Corbel ships with Windows since Vista; elsewhere Qt keeps its default.
_FONT = "Corbel"
_FONT_SIZE = 11


def run(page: str | None = None) -> None:
    app = QApplication(sys.argv)
    app.setApplicationDisplayName("Wallnext")
    if _FONT in QFontDatabase.families():
        app.setFont(QFont(_FONT, _FONT_SIZE))
    theme.apply(cfg.load().theme)
    window = SettingsWindow(page)
    window.show()
    app.exec()
