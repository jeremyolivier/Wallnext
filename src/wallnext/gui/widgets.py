"""Widgets Qt does not ship."""

from html import escape
from pathlib import Path

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPalette,
    QPixmap,
    QResizeEvent,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class Preview(QWidget):
    """The current wallpaper, cropped to fill, with a caption over a gradient."""

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._path: Path | None = None
        self._pixmap = QPixmap()
        self._scaled = QPixmap()  # _pixmap scaled to _scaled_for, redone on resize
        self._scaled_for = QSize()
        self._title = ""
        self._subtitle = ""
        # A real label rather than painted text, so the link is clickable.
        self._link = QLabel(self, openExternalLinks=True)
        self._link.setTextFormat(Qt.TextFormat.RichText)
        self._link.hide()

    def set_image(self, path: Path | None) -> None:
        if path == self._path:
            return
        self._path = path
        self._pixmap = QPixmap(str(path)) if path and path.exists() else QPixmap()
        self._scaled_for = QSize()
        self.update()

    def set_link(self, text: str, url: str | None) -> None:
        """Show a link to the wallpaper's web page in the bottom-right corner."""
        if not url:
            self._link.hide()
            return
        self._link.setText(
            f'<a href="{escape(url)}" style="color: white;">{escape(text)}</a>'
        )
        self._link.setToolTip(url)
        self._link.adjustSize()
        self._place_link()
        self._link.show()

    def _place_link(self) -> None:
        self._link.move(
            self.width() - self._link.width() - 20,
            self.height() - self._link.height() - 18,
        )

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._place_link()

    def set_caption(self, title: str, subtitle: str) -> None:
        self._title, self._subtitle = title, subtitle
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )
        rect = QRectF(self.rect())
        clip = QPainterPath()
        clip.addRoundedRect(rect, 8, 8)
        painter.setClipPath(clip)

        if self._pixmap.isNull():
            painter.fillRect(rect, self.palette().color(QPalette.ColorRole.Dark))
        else:
            # "Cover": scale to fill, then centre-crop.
            target = self.size() * self.devicePixelRatioF()
            if self._scaled_for != target:
                self._scaled = self._pixmap.scaled(
                    target,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self._scaled_for = target
            source = QRectF(
                (self._scaled.width() - target.width()) / 2,
                (self._scaled.height() - target.height()) / 2,
                target.width(),
                target.height(),
            )
            painter.drawPixmap(rect, self._scaled, source)

        shade = QLinearGradient(0, rect.height() * 0.35, 0, rect.height())
        shade.setColorAt(0, QColor(0, 0, 0, 0))
        shade.setColorAt(1, QColor(0, 0, 0, 190))
        painter.fillRect(rect, shade)

        painter.setPen(QColor("#ffffff"))
        title_font = QFont(self.font())
        # The Display cut of Segoe UI Variable is drawn for large sizes.
        title_font.setFamilies(["Segoe UI Variable Display", self.font().family()])
        title_font.setPointSizeF(20)
        title_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(title_font)
        painter.drawText(
            rect.adjusted(20, 0, -20, -40),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
            self._title,
        )
        sub_font = QFont(self.font())
        sub_font.setPointSizeF(9.5)
        painter.setFont(sub_font)
        painter.setPen(QColor(255, 255, 255, 210))
        painter.drawText(
            rect.adjusted(20, 0, -20, -18),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
            self._subtitle,
        )


def section_title(text: str) -> QLabel:
    label = QLabel(text)
    font = QFont(label.font())
    font.setPointSizeF(font.pointSizeF() * 1.15)
    font.setWeight(QFont.Weight.DemiBold)
    label.setFont(font)
    return label


def secondary(text: str) -> QLabel:
    """Smaller, dimmed text under a setting's name."""
    label = QLabel(text, wordWrap=True)
    label.setForegroundRole(QPalette.ColorRole.PlaceholderText)
    label.setTextFormat(Qt.TextFormat.AutoText)  # rich text when given a link
    return label


class Card(QFrame):
    """A rounded panel of setting rows, divided by thin lines (Windows 11 style)."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("card")
        # palette() follows the light/dark system theme.
        self.setStyleSheet(
            "#card { background: palette(base); border: 1px solid palette(window);"
            " border-radius: 6px; }"
        )
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

    def add_row(self, main: QWidget, *controls: QWidget | None) -> None:
        """A row: `main` on the left, `controls` (None ones skipped) on the right."""
        if self._layout.count():
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setStyleSheet("color: palette(window);")
            self._layout.addWidget(line)
        row = QHBoxLayout()
        row.setContentsMargins(16, 12, 16, 12)
        row.setSpacing(12)
        row.addWidget(main, 1)
        for control in controls:
            if control:
                row.addWidget(control, alignment=Qt.AlignmentFlag.AlignVCenter)
        self._layout.addLayout(row)


def stacked(*widgets: QWidget) -> QWidget:
    """Widgets stacked vertically and tightly, e.g. a name above its summary."""
    box = QWidget()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)
    for widget in widgets:
        layout.addWidget(widget)
    return box


def _glyph_icon(glyph: str, widget: QWidget) -> QIcon:
    """An icon drawn from Windows' own icon font, in the widget's text color."""
    families = [f for f in _ICON_FONTS if f in QFontDatabase.families()]
    ratio = widget.devicePixelRatioF()
    pixmap = QPixmap(QSize(20, 20) * ratio)
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    if families:
        painter = QPainter(pixmap)
        font = QFont(families[0])
        font.setPixelSize(16)
        painter.setFont(font)
        painter.setPen(widget.palette().color(QPalette.ColorRole.WindowText))
        painter.drawText(QRectF(0, 0, 20, 20), Qt.AlignmentFlag.AlignCenter, glyph)
        painter.end()
    return QIcon(pixmap)


# Windows 11's icon font, then Windows 10's (same code points for ours).
_ICON_FONTS = ["Segoe Fluent Icons", "Segoe MDL2 Assets"]


class Navigation(QWidget):
    """Pages listed in a pane on the left, the current one on the right.

    The layout of Windows 11's Settings app.
    """

    def __init__(self) -> None:
        super().__init__()
        self._pane = QListWidget()
        self._pane.setFixedWidth(200)
        self._pane.setIconSize(QSize(20, 20))
        self._pane.setFrameShape(QFrame.Shape.NoFrame)
        self._pane.setStyleSheet("QListWidget { background: transparent; }")
        self._pages = QStackedWidget()
        self._pane.currentRowChanged.connect(self._pages.setCurrentIndex)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 12, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._pane)
        layout.addWidget(self._pages, 1)

    def add_page(self, title: str, glyph: str, *sections: QWidget) -> None:
        """A page titled `title`, its sections stacked from the top."""
        item = QListWidgetItem(_glyph_icon(glyph, self), title)
        item.setSizeHint(QSize(0, 40))
        self._pane.addItem(item)

        heading = QLabel(title)
        font = QFont(heading.font())
        font.setFamilies(["Segoe UI Variable Display", heading.font().family()])
        font.setPointSizeF(20)
        font.setWeight(QFont.Weight.DemiBold)
        heading.setFont(font)

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 0, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(heading)
        for section in sections:
            layout.addWidget(section)
        layout.addStretch()
        self._pages.addWidget(page)
        if self._pane.count() == 1:
            self._pane.setCurrentRow(0)
