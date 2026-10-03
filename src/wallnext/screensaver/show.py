"""The screensaver itself: one full-screen slideshow window per screen.

Any key, click or mouse move closes every window at once. When anything is
wrong (no picture, the scene fails to load, another instance runs), it exits
right away instead of leaving a black screen.
"""

import random
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QEvent, QLockFile, QObject, Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QCursor, QGuiApplication
from PySide6.QtQuick import QQuickView

from wallnext.screensaver import cache

_QML = Path(__file__).with_name("slideshow.qml")
# Mouse travel (px) tolerated before quitting: mice jitter on their own.
_MOUSE_SLACK = 12


class _QuitOnInput(QObject):
    """Quit on a key, a click, or a real mouse move.

    The cursor is polled rather than read from mouse events: they do not reliably
    reach an application-wide filter for Qt Quick windows.
    """

    def __init__(self, app: QGuiApplication) -> None:
        super().__init__(app)
        self._app = app
        self._origin = QCursor.pos()
        self._poll = QTimer(self, interval=100)
        self._poll.timeout.connect(self._check_cursor)
        self._poll.start()
        app.installEventFilter(self)

    def _check_cursor(self) -> None:
        if (QCursor.pos() - self._origin).manhattanLength() > _MOUSE_SLACK:
            self._app.quit()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() in (
            QEvent.Type.KeyPress,
            QEvent.Type.MouseButtonPress,
            QEvent.Type.Wheel,
        ):
            self._app.quit()
        return False


def run() -> None:
    """Show the screensaver until a key, a click or the mouse moves."""
    # Windows may start it again while it runs: only one instance at a time.
    lock = QLockFile(str(Path(tempfile.gettempdir()) / "wallnext-screensaver.lock"))
    if not lock.tryLock(0):
        return
    pictures = [QUrl.fromLocalFile(str(p)) for p in cache.pictures()]
    if not pictures:
        return

    app = QGuiApplication(sys.argv)
    views = []
    for screen in app.screens():
        # Each screen gets its own order, so they rarely show the same picture.
        view = QQuickView()
        view.setColor(QColor("black"))
        view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        view.setInitialProperties({"pictures": random.sample(pictures, len(pictures))})
        view.setSource(QUrl.fromLocalFile(str(_QML)))
        if view.status() != QQuickView.Status.Ready:
            print(view.errors(), file=sys.stderr)
            return
        view.setScreen(screen)
        view.setGeometry(screen.geometry())
        view.showFullScreen()
        views.append(view)

    app.setOverrideCursor(Qt.CursorShape.BlankCursor)
    _QuitOnInput(app)
    app.exec()
