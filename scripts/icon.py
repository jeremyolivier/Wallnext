"""Render the app logo (src/wallnext/gui/icons/wallnext.svg) for Windows and the README.

    uv run python scripts/icon.py    # or: just icon

Writes assets/wallnext.ico (every size Windows asks for, as PNG entries, which
Windows Vista and later read) and assets/wallnext.png.
"""

import struct
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QSize, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

ROOT = Path(__file__).resolve().parents[1]
LOGO = ROOT / "src" / "wallnext" / "gui" / "icons" / "wallnext.svg"
ASSETS = ROOT / "assets"
ICO_SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]
README_SIZE = 256


def render(renderer: QSvgRenderer, size: int) -> QImage:
    image = QImage(QSize(size, size), QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()
    return image


def png_bytes(image: QImage) -> bytes:
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(data.data())


def ico(images: list[bytes], sizes: list[int]) -> bytes:
    """An ICO file whose entries are PNG images."""
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = len(header) + 16 * len(images)
    entries, payload = b"", b""
    for size, png in zip(sizes, images, strict=True):
        side = 0 if size >= 256 else size  # 0 means 256 in an ICO entry
        entries += struct.pack(
            "<BBBBHHII", side, side, 0, 0, 1, 32, len(png), offset + len(payload)
        )
        payload += png
    return header + entries + payload


def main() -> None:
    QGuiApplication(sys.argv)
    renderer = QSvgRenderer(str(LOGO))
    ASSETS.mkdir(exist_ok=True)
    pngs = [png_bytes(render(renderer, size)) for size in ICO_SIZES]
    (ASSETS / "wallnext.ico").write_bytes(ico(pngs, ICO_SIZES))
    render(renderer, README_SIZE).save(str(ASSETS / "wallnext.png"))
    print(f"Wrote {ASSETS / 'wallnext.ico'} and {ASSETS / 'wallnext.png'}")


if __name__ == "__main__":
    main()
