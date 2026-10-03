"""Wallpaper sources listed in the window, with their settings dialogs.

To add a source to the window: append it to SOURCES, with a dialog editing its
[sources.<key>] settings if it has any besides `enabled`.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QWidget,
)

from wallnext import config as cfg
from wallnext import sources


class SourceDialog(Protocol):
    """A modal dialog editing one source's settings."""

    def __init__(self, settings: cfg.Settings, parent: QWidget) -> None: ...

    def exec(self) -> int: ...

    def settings(self) -> cfg.Settings: ...


@dataclass(frozen=True)
class Source:
    key: str  # as in wallnext.sources.SOURCES and config.toml
    summary: Callable[[cfg.Settings], str]  # one line describing its settings
    dialog: type[SourceDialog] | None = None

    @property
    def name(self) -> str:
        return sources.SOURCES[self.key].name


# --- Wallhaven -------------------------------------------------------------

SORTINGS = {
    "toplist": "Top",
    "random": "Random",
    "date_added": "Latest",
    "views": "Most viewed",
    "favorites": "Most favorited",
}
TOPRANGES = {
    "1d": "Last day",
    "3d": "Last 3 days",
    "1w": "Last week",
    "1M": "Last month",
    "3M": "Last 3 months",
    "6M": "Last 6 months",
    "1y": "Last year",
}
# Wallhaven bitmasks: one flag per checkbox, in this order.
CATEGORIES = ["General", "Anime", "People"]
PURITIES = ["SFW", "Sketchy", "NSFW"]


def wallhaven_summary(settings: cfg.Settings) -> str:
    s = settings.sources.wallhaven
    parts = [
        f"“{s.query}”" if s.query else "Any keyword",
        SORTINGS.get(s.sorting, s.sorting),
    ]
    if s.sorting == "toplist":
        parts.append(TOPRANGES.get(s.toprange, s.toprange).lower())
    if s.atleast:
        parts.append(f"≥ {s.atleast}")
    return " · ".join(parts)


def _combo(items: dict[str, str], current: str) -> QComboBox:
    combo = QComboBox()
    for value, text in items.items():
        combo.addItem(text, value)
    combo.setCurrentIndex(max(0, combo.findData(current)))
    return combo


def _resolution(value: str) -> QLineEdit:
    field = QLineEdit(value, placeholderText="Any, e.g. 2560x1440")
    field.setValidator(
        QRegularExpressionValidator(QRegularExpression(r"(\d{1,5}x\d{1,5})?"))
    )
    return field


def _buttons(dialog: QDialog) -> QDialogButtonBox:
    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    return buttons


class _Flags(QWidget):
    """A row of checkboxes edited as a Wallhaven bitmask such as "110"."""

    def __init__(self, labels: list[str], value: str) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._boxes = [QCheckBox(text) for text in labels]
        for box, bit in zip(self._boxes, value, strict=False):
            box.setChecked(bit == "1")
            layout.addWidget(box)
        layout.addStretch()

    def bitmask(self) -> str:
        return "".join("1" if box.isChecked() else "0" for box in self._boxes)


class WallhavenDialog(QDialog):
    def __init__(self, base: cfg.Settings, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("Wallhaven")
        self.setMinimumWidth(420)
        self._base = base
        settings = base.sources.wallhaven

        self._query = QLineEdit(settings.query, placeholderText="Any")
        self._query.setClearButtonEnabled(True)
        self._sorting = _combo(SORTINGS, settings.sorting)
        self._toprange = _combo(TOPRANGES, settings.toprange)
        self._sorting.currentIndexChanged.connect(self._sync_toprange)
        self._sync_toprange()
        self._atleast = _resolution(settings.atleast)
        self._categories = _Flags(CATEGORIES, settings.categories)
        self._purity = _Flags(PURITIES, settings.purity)

        form = QFormLayout(self)
        form.addRow("Keywords", self._query)
        form.addRow("Sort by", self._sorting)
        form.addRow("Period", self._toprange)
        form.addRow("Minimum resolution", self._atleast)
        form.addRow("Categories", self._categories)
        form.addRow("Purity", self._purity)
        form.addRow(_buttons(self))

    def _sync_toprange(self) -> None:
        self._toprange.setEnabled(self._sorting.currentData() == "toplist")

    def settings(self) -> cfg.Settings:
        return self._base.with_source(
            "wallhaven",
            query=self._query.text().strip(),
            sorting=self._sorting.currentData(),
            toprange=self._toprange.currentData(),
            atleast=self._atleast.text().strip(),
            categories=self._categories.bitmask(),
            purity=self._purity.bitmask(),
        )


# --- NASA APOD -------------------------------------------------------------


def apod_summary(settings: cfg.Settings) -> str:
    atleast = settings.sources.apod.atleast
    return "Astronomy Picture of the Day · landscape" + (
        f" · ≥ {atleast}" if atleast else ""
    )


class ApodDialog(QDialog):
    def __init__(self, base: cfg.Settings, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("NASA APOD")
        self.setMinimumWidth(360)
        self._base = base
        self._atleast = _resolution(base.sources.apod.atleast)

        form = QFormLayout(self)
        form.addRow("Minimum resolution", self._atleast)
        hint = QLabel(
            "Many older pictures are small: a high minimum skips them.",
            wordWrap=True,
        )
        hint.setEnabled(False)
        form.addRow(hint)
        form.addRow(_buttons(self))

    def settings(self) -> cfg.Settings:
        return self._base.with_source("apod", atleast=self._atleast.text().strip())


SOURCES = [
    Source(key="wallhaven", summary=wallhaven_summary, dialog=WallhavenDialog),
    Source(key="apod", summary=apod_summary, dialog=ApodDialog),
]
