from __future__ import annotations

import qtawesome as qta
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu, QPushButton,
                               QVBoxLayout, QWidget)

from domain.models import SOURCE_SPOTIFY, Playlist
from ui import theme
from ui.components.elided_label import ElidedLabel
from ui.components.icon_button import icon_button

KEY_ROLE = Qt.UserRole
ROW_HEIGHT = 62


# fila playlist tres puntos
class PlaylistRow(QWidget):
    menu_requested = Signal(object)

    def __init__(self, playlist: Playlist):
        super().__init__()
        origin = "Spotify" if playlist.source == SOURCE_SPOTIFY else "YouTube Music"
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 4, 0)
        layout.setSpacing(4)

        texts = QVBoxLayout()
        texts.setSpacing(2)
        texts.addStretch(1)
        title = ElidedLabel(playlist.title)
        title.setStyleSheet(f"color: {theme.TEXT}; font-size: 14px; font-weight: 600; background: transparent;")
        title.setToolTip(playlist.title)
        subtitle = ElidedLabel(f"{origin} · {len(playlist.tracks)} canciones")
        subtitle.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 12px; background: transparent;")
        texts.addWidget(title)
        texts.addWidget(subtitle)
        texts.addStretch(1)
        layout.addLayout(texts, 1)

        self.button = QPushButton()
        self.button.setIcon(qta.icon("fa5s.ellipsis-v", color=theme.TEXT))
        self.button.setFixedSize(32, 32)
        self.button.setCursor(Qt.PointingHandCursor)
        self.button.setToolTip("Más opciones")
        self.button.setStyleSheet("""
            QPushButton { background: transparent; border: none; border-radius: 16px; }
            QPushButton:hover { background: rgba(255,255,255,0.14); }
        """)
        self.button.clicked.connect(self._emit_menu)
        layout.addWidget(self.button)

    def _emit_menu(self) -> None:
        self.menu_requested.emit(self.button.mapToGlobal(self.button.rect().bottomLeft()))


# lista playlists importar enlace
class PlaylistSidebar(QWidget):
    import_requested = Signal(str)
    playlist_selected = Signal(str)
    delete_requested = Signal(str)
    settings_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedWidth(300)
        self.setObjectName("sidebar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"#sidebar {{ background: {theme.SURFACE}; }} QLabel {{ background: transparent; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Mis playlists")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {theme.TEXT}; background: transparent;")
        header.addWidget(title, 1)
        gear = icon_button("fa5s.cog", 34, "Configuración")
        gear.clicked.connect(self.settings_requested)
        header.addWidget(gear)
        layout.addLayout(header)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Pega el enlace de YouTube Music o Spotify")
        self._input.setStyleSheet(theme.input_qss("QLineEdit"))
        self._input.returnPressed.connect(self._submit)
        layout.addWidget(self._input)

        self._button = QPushButton("Importar")
        self._button.setCursor(Qt.PointingHandCursor)
        self._button.setStyleSheet(theme.button_qss("primary", height=36))
        self._button.clicked.connect(self._submit)
        layout.addWidget(self._button)

        self._notice = QLabel()
        self._notice.setWordWrap(True)
        self._notice.hide()
        layout.addWidget(self._notice)

        self._list = QListWidget()
        self._list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_context_menu)
        self._list.currentItemChanged.connect(self._on_current)
        self._list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self._list.setStyleSheet(f"""
            QListWidget {{ background: transparent; border: none; outline: none; color: {theme.TEXT}; }}
            QListWidget::item {{ border-radius: 8px; }}
            QListWidget::item:hover {{ background: rgba(255,255,255,0.08); }}
            QListWidget::item:selected {{ background: rgba(255,255,255,0.16); color: {theme.TEXT}; }}
        """)
        layout.addWidget(self._list, 1)

        self._empty = QLabel("Todavía no importaste ninguna playlist.")
        self._empty.setWordWrap(True)
        self._empty.setAlignment(Qt.AlignCenter)
        self._empty.setStyleSheet(f"color: {theme.TEXT_MUTED}; background: transparent;")
        layout.addWidget(self._empty)

    def set_playlists(self, playlists: list[Playlist], select_key: str = "") -> None:
        keep = select_key or self.selected_key()
        self._list.blockSignals(True)
        self._list.clear()
        for playlist in playlists:
            item = QListWidgetItem()
            item.setData(KEY_ROLE, playlist.key)
            item.setSizeHint(QSize(0, ROW_HEIGHT))
            self._list.addItem(item)
            row = PlaylistRow(playlist)
            row.menu_requested.connect(lambda pos, key=playlist.key: self._open_menu(key, pos))
            self._list.setItemWidget(item, row)
            if playlist.key == keep:
                self._list.setCurrentItem(item)
        self._list.blockSignals(False)
        self._empty.setVisible(not playlists)

    def selected_key(self) -> str:
        item = self._list.currentItem()
        return item.data(KEY_ROLE) if item else ""

    def set_busy(self, busy: bool) -> None:
        self._button.setEnabled(not busy)
        self._input.setEnabled(not busy)
        self._button.setText("Importando..." if busy else "Importar")
        if busy:
            self.show_notice("", error=False)

    def show_notice(self, text: str, error: bool) -> None:
        color = theme.DANGER if error else theme.TEXT
        self._notice.setStyleSheet(f"color: {color}; background: transparent;")
        self._notice.setText(text)
        self._notice.setVisible(bool(text))

    def clear_input(self) -> None:
        self._input.clear()

    def _submit(self) -> None:
        text = self._input.text().strip()
        if text:
            self.import_requested.emit(text)

    def _on_current(self, item: QListWidgetItem | None, _previous) -> None:
        if item is not None:
            self.playlist_selected.emit(item.data(KEY_ROLE))

    def _on_context_menu(self, pos) -> None:
        item = self._list.itemAt(pos)
        if item is not None:
            self._open_menu(item.data(KEY_ROLE), self._list.viewport().mapToGlobal(pos))

    def _open_menu(self, key: str, global_pos) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(theme.menu_qss())
        remove = menu.addAction(qta.icon("fa5s.trash-alt", color=theme.TEXT), "Eliminar playlist")
        if self._run_menu(menu, global_pos) is remove:
            self.delete_requested.emit(key)

    @staticmethod
    def _run_menu(menu: QMenu, global_pos):
        return menu.exec(global_pos)
