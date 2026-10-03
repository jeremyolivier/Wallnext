"""Light or dark: follow Windows, or force one."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

THEMES = ["system", "light", "dark"]
LABELS = {"system": "System", "light": "Light", "dark": "Dark"}
# Segoe Fluent Icons: System, Brightness (sun), QuietHours (moon).
GLYPHS = {"system": "", "light": "", "dark": ""}
# Fixed colors, readable on both themes, like the navigation icons.
COLORS = {"system": "#0078D4", "light": "#E8A317", "dark": "#8764B8"}
_SCHEMES = {
    "system": Qt.ColorScheme.Unknown,
    "light": Qt.ColorScheme.Light,
    "dark": Qt.ColorScheme.Dark,
}


def apply(theme: str) -> None:
    QGuiApplication.styleHints().setColorScheme(_SCHEMES[theme])


def following(theme: str) -> str:
    return THEMES[(THEMES.index(theme) + 1) % len(THEMES)]
