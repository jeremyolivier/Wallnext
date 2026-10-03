"""Settings window, opened when wallnext is launched without a command."""

import sys

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from wallnext.gui.window import SettingsWindow

# Windows 11's own UI font (Settings, Explorer); older Windows lack it.
_FONT = "Segoe UI Variable Text"


def run() -> None:
    app = QApplication(sys.argv)
    app.setApplicationDisplayName("Wallnext")
    if _FONT in QFontDatabase.families():
        app.setFont(QFont(_FONT, 10))
    window = SettingsWindow()
    window.show()
    app.exec()
