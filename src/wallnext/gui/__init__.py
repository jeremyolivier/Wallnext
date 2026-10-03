"""Settings window, opened when wallnext is launched without a command."""

import sys

from PySide6.QtWidgets import QApplication

from wallnext.gui.window import SettingsWindow


def run() -> None:
    app = QApplication(sys.argv)
    app.setApplicationDisplayName("Wallnext")
    window = SettingsWindow()
    window.show()
    app.exec()
