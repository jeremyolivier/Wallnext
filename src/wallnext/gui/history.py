"""Dialog listing past wallpapers with a link to each."""

from html import escape

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from wallnext import history
from wallnext.gui.widgets import Card, secondary


class HistoryDialog(QDialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("History")
        self.resize(640, 420)
        entries = history.entries()

        table = QTableWidget(len(entries), 3)
        table.setHorizontalHeaderLabels(["Shown", "Source", "Link"])
        table.verticalHeader().hide()
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        table.setFrameShape(QFrame.Shape.NoFrame)
        table.setShowGrid(False)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        header.setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        for row, entry in enumerate(entries):
            table.setItem(row, 0, QTableWidgetItem(f"{entry.shown_at:%Y-%m-%d %H:%M}"))
            table.setItem(row, 1, QTableWidgetItem(entry.source))
            link = QLabel(f'<a href="{escape(entry.url)}">{escape(entry.url)}</a>')
            link.setOpenExternalLinks(True)
            link.setToolTip(entry.url)
            table.setCellWidget(row, 2, link)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)

        card = Card()
        card.add_row(table if entries else secondary("No wallpaper shown yet."))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        layout.addWidget(card, 1)
        layout.addWidget(buttons)
