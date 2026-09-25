from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem, QWidget

from domain.models import Playlist, format_duration
from ui import theme

COLUMNS = ("#", "Título", "Artista", "Duración")


# tabla canciones un clic
class TrackTable(QTableWidget):
    play_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(0, len(COLUMNS), parent)
        self.setHorizontalHeaderLabels(COLUMNS)
        for column in range(len(COLUMNS)):
            align = Qt.AlignRight if column in (0, 3) else Qt.AlignLeft
            self.horizontalHeaderItem(column).setTextAlignment(align | Qt.AlignVCenter)
        self.verticalHeader().hide()
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setShowGrid(False)
        self.setFocusPolicy(Qt.NoFocus)
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        self.setColumnWidth(0, 48)
        self.setColumnWidth(3, 90)
        self.setStyleSheet(f"""
            QTableWidget {{ background: transparent; border: none; color: {theme.TEXT}; outline: none; }}
            QTableWidget::item {{ padding: 6px 8px; border: none; }}
            QTableWidget::item:hover {{ background: rgba(255,255,255,0.06); }}
            QTableWidget::item:selected {{ background: rgba(255,255,255,0.14); color: {theme.TEXT}; }}
            QHeaderView::section {{ background: transparent; color: {theme.TEXT_MUTED}; border: none;
                                    border-bottom: 1px solid {theme.BORDER}; padding: 6px 8px; text-align: left; }}
        """)
        self.cellClicked.connect(lambda row, _column: self.play_requested.emit(row))
        self._current = -1

    def set_playlist(self, playlist: Playlist | None) -> None:
        self.setRowCount(0)
        self._current = -1
        if playlist is None:
            return
        self.setRowCount(len(playlist.tracks))
        for row, track in enumerate(playlist.tracks):
            values = (str(row + 1), track.title, track.artist, format_duration(track.duration_s) if track.duration_s else "")
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in (0, 3):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.setItem(row, column, item)

    def set_current(self, index: int) -> None:
        self._paint(self._current, None)
        self._current = index
        self._paint(index, QColor(theme.LINK))

    def _paint(self, row: int, color: QColor | None) -> None:
        if not 0 <= row < self.rowCount():
            return
        for column in range(self.columnCount()):
            item = self.item(row, column)
            if item is not None:
                item.setForeground(QBrush(color) if color else QBrush(QColor(theme.TEXT)))
