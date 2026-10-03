"""About page: version, license, third-party software, pictures and privacy."""

import importlib.metadata
import sys
from collections.abc import Callable

import win32api
from PySide6.QtCore import QSize
from PySide6.QtGui import QFont, QFontDatabase, QIcon
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from wallnext import notices
from wallnext.gui.widgets import LOGO, Card, secondary, section_title, stacked

AUTHOR = "Jérémy Olivier"
REPOSITORY = "https://github.com/jeremyolivier/wallnext"


def version() -> str:
    if "__compiled__" in globals():
        # Packaged by Nuitka: read the version `just build` put in the exe.
        info = win32api.GetFileVersionInfo(sys.executable, "\\")
        major_minor, patch = info["FileVersionMS"], info["FileVersionLS"]
        return f"{major_minor >> 16}.{major_minor & 0xFFFF}.{patch >> 16}"
    return importlib.metadata.version("wallnext")


class _TextDialog(QDialog):
    """A long read-only text, such as a license."""

    def __init__(self, title: str, text: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(720, 560)
        view = QPlainTextEdit(text, readOnly=True)
        view.setFrameShape(QFrame.Shape.NoFrame)
        view.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        card = Card()
        card.add_row(view)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        layout.addWidget(card, 1)
        layout.addWidget(buttons)


def _link(text: str, url: str) -> QLabel:
    label = QLabel(f'<a href="{url}">{text}</a>')
    label.setOpenExternalLinks(True)
    return label


def _button(text: str, on_click: Callable[[], None]) -> QPushButton:
    button = QPushButton(text)
    button.clicked.connect(on_click)
    return button


def sections(parent: QWidget) -> list[QWidget]:
    def show(title: str, text: Callable[[], str]) -> None:
        _TextDialog(title, text(), parent).exec()

    name = QLabel(f"Wallnext {version()}")
    font = QFont(name.font())
    font.setWeight(QFont.Weight.DemiBold)
    name.setFont(font)
    app = Card()
    logo = QLabel()
    logo.setPixmap(QIcon(str(LOGO)).pixmap(QSize(48, 48), logo.devicePixelRatioF()))
    identity = QWidget()
    row = QHBoxLayout(identity)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(14)
    row.addWidget(logo)
    row.addWidget(stacked(name, secondary(f"© 2026 {AUTHOR} · MIT License")), 1)
    app.add_row(identity, _link("Source code", REPOSITORY))
    app.add_row(
        stacked(QLabel("License"), secondary("Provided as is, without warranty.")),
        _button("View…", lambda: show("License", notices.license_text)),
    )
    app.add_row(
        stacked(
            QLabel("Third-party software"),
            secondary("Python, Qt (LGPLv3), pydantic, httpx2 and others."),
        ),
        _button("View…", lambda: show("Third-party software", notices.text)),
    )

    pictures = Card()
    pictures.add_row(
        secondary(
            "Pictures belong to their authors. Wallnext shows them as your "
            "wallpaper for personal use; “View on …” opens each picture's page, "
            "with its author and license. Wallnext is not affiliated with "
            "Wallhaven, NASA, the Wikimedia Foundation or Microsoft, whose logos "
            "belong to them."
        )
    )

    privacy = Card()
    privacy.add_row(
        secondary(
            "No account, no tracking: Wallnext only contacts the sources you "
            "enable. Settings and history stay in %APPDATA%\\wallnext; the "
            "Wallhaven API key, in the Windows Credential Manager."
        )
    )

    return [
        app,
        stacked(section_title("Pictures"), pictures),
        stacked(section_title("Privacy"), privacy),
    ]
