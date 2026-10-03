"""Widgets Qt does not ship."""

from html import escape
from pathlib import Path

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPalette,
    QPixmap,
    QResizeEvent,
)
from PySide6.QtWidgets import QLabel, QSizePolicy, QWidget


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
