"""Wallpaper sources listed in the window, each with its own settings dialog.

To add a source: write a dialog editing its settings and append it to SOURCES.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
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
    QLineEdit,
    QWidget,
)

from wallnext import config as cfg
from wallnext.sources.wallhaven import source as wallhaven


class SourceDialog(Protocol):
    """A modal dialog editing one source's settings."""

    def __init__(self, settings: cfg.Settings, parent: QWidget) -> None: ...

    def exec(self) -> int: ...

    def settings(self) -> cfg.Settings: ...


@dataclass(frozen=True)
class Source:
    name: str
    dialog: type[SourceDialog]
    summary: Callable[[cfg.Settings], str]  # one line describing its settings
    page_url: Callable[[Path], str | None]  # web page of a wallpaper it downloaded


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


def wallhaven_summary(s: cfg.Settings) -> str:
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
    def __init__(self, settings: cfg.Settings, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("Wallhaven")
        self.setMinimumWidth(420)
        self._base = settings

        self._query = QLineEdit(settings.query, placeholderText="Any")
        self._query.setClearButtonEnabled(True)
        self._sorting = _combo(SORTINGS, settings.sorting)
        self._toprange = _combo(TOPRANGES, settings.toprange)
        self._sorting.currentIndexChanged.connect(self._sync_toprange)
        self._sync_toprange()
        self._atleast = QLineEdit(
            settings.atleast, placeholderText="Any, e.g. 2560x1440"
        )
        self._atleast.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"(\d{1,5}x\d{1,5})?"))
        )
        self._categories = _Flags(CATEGORIES, settings.categories)
        self._purity = _Flags(PURITIES, settings.purity)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        form = QFormLayout(self)
        form.addRow("Keywords", self._query)
        form.addRow("Sort by", self._sorting)
        form.addRow("Period", self._toprange)
        form.addRow("Minimum resolution", self._atleast)
        form.addRow("Categories", self._categories)
        form.addRow("Purity", self._purity)
        form.addRow(buttons)

    def _sync_toprange(self) -> None:
        self._toprange.setEnabled(self._sorting.currentData() == "toplist")

    def settings(self) -> cfg.Settings:
        return self._base.model_copy(
            update={
                "query": self._query.text().strip(),
                "sorting": self._sorting.currentData(),
                "toprange": self._toprange.currentData(),
                "atleast": self._atleast.text().strip(),
                "categories": self._categories.bitmask(),
                "purity": self._purity.bitmask(),
            }
        )


SOURCES = [
    Source(
        name="Wallhaven",
        dialog=WallhavenDialog,
        summary=wallhaven_summary,
        page_url=wallhaven.page_url,
    ),
]


def identify(wallpaper: Path) -> tuple[Source, str] | None:
    """The source a wallpaper came from and its web page, if known."""
    for source in SOURCES:
        if url := source.page_url(wallpaper):
            return source, url
    return None
