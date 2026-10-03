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
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from wallnext import config as cfg
from wallnext import credentials, sources
from wallnext.exceptions import WallnextError
from wallnext.gui.widgets import Card, secondary, section_title, stacked
from wallnext.sources.wallhaven.client import WallhavenRequester


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
    logo: str = ""  # file in gui/icons

    @property
    def name(self) -> str:
        return sources.SOURCES[self.key].name


# --- Wallhaven -------------------------------------------------------------

MODES = {"search": "A search", "collection": "Your collection"}
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
    if s.mode == "collection":
        return f"Collection “{s.collection_label}” · {s.username}"
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


class _SettingsDialog(QDialog):
    """A source's settings, laid out like the main window: rows in cards."""

    def __init__(self, title: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(520)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 20, 20, 20)
        self._layout.setSpacing(16)
        self._buttons = _buttons(self)
        self._layout.addWidget(self._buttons)
        self._card: Card | None = None

    def section(self, title: str) -> None:
        """Start a new card, under `title`, for the next rows."""
        self._card = Card()
        index = self._layout.indexOf(self._buttons)
        self._layout.insertWidget(index, stacked(section_title(title), self._card))

    def add_row(self, label: str, control: QWidget, hint: str | QLabel = "") -> None:
        if self._card is None:
            self._card = Card()
            self._layout.insertWidget(self._layout.indexOf(self._buttons), self._card)
        note = secondary(hint) if isinstance(hint, str) and hint else hint
        text = (
            stacked(QLabel(label), note) if isinstance(note, QLabel) else QLabel(label)
        )
        control.setMinimumWidth(220)
        self._card.add_row(text, control)


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

    def bitmask(self) -> str:
        return "".join("1" if box.isChecked() else "0" for box in self._boxes)


class WallhavenDialog(_SettingsDialog):
    def __init__(self, base: cfg.Settings, parent: QWidget) -> None:
        super().__init__("Wallhaven", parent)
        self._base = base
        settings = base.sources.wallhaven

        self._mode = _combo(MODES, settings.mode)
        self._mode.currentIndexChanged.connect(self._sync_mode)
        self.add_row("Pick from", self._mode)

        self._query = QLineEdit(
            settings.query, placeholderText="Any, e.g. nature, city night"
        )
        self._query.setClearButtonEnabled(True)
        self._sorting = _combo(SORTINGS, settings.sorting)
        self._toprange = _combo(TOPRANGES, settings.toprange)
        self._sorting.currentIndexChanged.connect(self._sync_mode)
        self._atleast = _resolution(settings.atleast)
        self._categories = _Flags(CATEGORIES, settings.categories)
        self._purity = _Flags(PURITIES, settings.purity)
        self.section("Search")
        self.add_row(
            "Keywords",
            self._query,
            "Separate several with commas: one is picked per wallpaper.",
        )
        self.add_row("Sort by", self._sorting)
        self.add_row("Period", self._toprange, "Only for Top")
        self.add_row("Minimum resolution", self._atleast)
        self.add_row("Categories", self._categories)
        self.add_row("Purity", self._purity, "Also applies to your collection")

        self._username = QLineEdit(settings.username, placeholderText="Your username")
        self._api_key = QLineEdit(credentials.get("wallhaven"))
        self._api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key.setPlaceholderText("Optional")
        key_hint = secondary(
            "For private collections and favorites. Copy it from "
            '<a href="https://wallhaven.cc/settings/account">Settings → Account'
            "</a> on Wallhaven. Kept in the Windows Credential Manager."
        )
        key_hint.setOpenExternalLinks(True)
        self._collection = QComboBox()
        if settings.collection_id is not None:
            self._collection.addItem(settings.collection_label, settings.collection_id)
        self._load = QPushButton("Load")
        self._load.clicked.connect(self._load_collections)
        collection = QWidget()
        row = QHBoxLayout(collection)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self._collection, 1)
        row.addWidget(self._load)
        self.section("Your collection")
        self.add_row("Username", self._username)
        self.add_row("API key", self._api_key, key_hint)
        self.add_row("Collection", collection, "Load lists your collections")

        self._sync_mode()

    def _sync_mode(self) -> None:
        search = self._mode.currentData() == "search"
        for widget in (self._query, self._sorting, self._atleast, self._categories):
            widget.setEnabled(search)
        self._toprange.setEnabled(search and self._sorting.currentData() == "toplist")
        for widget in (self._username, self._api_key, self._collection, self._load):
            widget.setEnabled(not search)

    def _load_collections(self) -> None:
        username = self._username.text().strip()
        key = self._api_key.text().strip()
        if not username:
            QMessageBox.warning(self, "Wallhaven", "Enter your username first.")
            return
        try:
            # With a key: all your collections; without: only the public ones.
            found = WallhavenRequester(key).collections("" if key else username)
        except WallnextError as e:
            QMessageBox.warning(self, "Wallhaven", str(e))
            return
        self._collection.clear()
        for item in found:
            self._collection.addItem(f"{item.label} ({item.count})", item.id)
        if not found:
            QMessageBox.information(self, "Wallhaven", "No collection found.")

    def accept(self) -> None:
        if self._mode.currentData() == "collection" and (
            not self._username.text().strip() or self._collection.currentData() is None
        ):
            QMessageBox.warning(
                self, "Wallhaven", "Enter your username and pick a collection."
            )
            return
        credentials.put("wallhaven", self._api_key.text().strip())
        super().accept()

    def settings(self) -> cfg.Settings:
        return self._base.with_source(
            "wallhaven",
            mode=self._mode.currentData(),
            query=self._query.text().strip(),
            sorting=self._sorting.currentData(),
            toprange=self._toprange.currentData(),
            atleast=self._atleast.text().strip(),
            categories=self._categories.bitmask(),
            purity=self._purity.bitmask(),
            username=self._username.text().strip(),
            collection_id=self._collection.currentData(),
            # Without its "(count)": the count changes as the collection grows.
            collection_label=self._collection.currentText().rsplit(" (", 1)[0],
        )


# --- Sources filtered by resolution only ------------------------------------


def _with_resolution(text: str, atleast: str) -> str:
    return f"{text} · ≥ {atleast}" if atleast else text


class _ResolutionDialog(_SettingsDialog):
    """Settings of a source filtered by a minimum resolution."""

    KEY: str
    HINT: str = ""

    def __init__(self, base: cfg.Settings, parent: QWidget) -> None:
        super().__init__(sources.SOURCES[self.KEY].name, parent)
        self._base = base
        self._atleast = _resolution(getattr(base.sources, self.KEY).atleast)
        self._add_rows()

    def _add_rows(self) -> None:
        self.add_row("Minimum resolution", self._atleast, self.HINT)

    def settings(self) -> cfg.Settings:
        return self._base.with_source(self.KEY, atleast=self._atleast.text().strip())


class ApodDialog(_ResolutionDialog):
    KEY = "apod"
    HINT = "Many older pictures are small: a high minimum skips them."


class WikimediaDialog(_ResolutionDialog):
    KEY = "wikimedia"


# --- NASA Images -----------------------------------------------------------


def nasa_images_summary(settings: cfg.Settings) -> str:
    s = settings.sources.nasa_images
    return _with_resolution(f"“{s.query}”", s.atleast)


class NasaImagesDialog(_ResolutionDialog):
    KEY = "nasa_images"

    def _add_rows(self) -> None:
        self._query = QLineEdit(self._base.sources.nasa_images.query)
        self._query.setClearButtonEnabled(True)
        self.add_row("Keywords", self._query)
        super()._add_rows()

    def settings(self) -> cfg.Settings:
        query = self._query.text().strip() or self._base.sources.nasa_images.query
        return super().settings().with_source("nasa_images", query=query)


SOURCES = [
    Source(
        key="wallhaven",
        summary=wallhaven_summary,
        dialog=WallhavenDialog,
        logo="wallhaven.ico",
    ),
    Source(
        key="apod",
        summary=lambda s: _with_resolution(
            "Astronomy Picture of the Day", s.sources.apod.atleast
        ),
        dialog=ApodDialog,
        logo="nasa.svg",
    ),
    Source(
        key="nasa_images",
        summary=nasa_images_summary,
        dialog=NasaImagesDialog,
        logo="nasa.svg",
    ),
    Source(
        key="wikimedia",
        summary=lambda s: _with_resolution(
            "Picture of the day", s.sources.wikimedia.atleast
        ),
        dialog=WikimediaDialog,
        logo="wikimedia.svg",
    ),
    Source(
        key="bing",
        summary=lambda _: "Picture of the day · last 8 days · 4K",
        logo="bing.png",
    ),
    Source(
        key="spotlight",
        summary=lambda _: "Windows lock screen pictures · 4K",
        logo="windows.svg",
    ),
]
