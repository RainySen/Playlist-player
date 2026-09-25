from __future__ import annotations

import qtawesome as qta
from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget

from domain.models import SOURCE_SPOTIFY, Playlist, Track
from ui import theme
from ui.components import dialogs
from ui.components.player_bar import PlayerBar
from ui.components.playlist_sidebar import PlaylistSidebar
from ui.components.track_table import TrackTable


# ventana principal
class MainWindow(QMainWindow):
    play_requested = Signal(str, int)
    play_all_requested = Signal(str)
    shuffle_requested = Signal(str)
    settings_requested = Signal()
    presence_changed = Signal(bool)
    closed = Signal()

    def __init__(self, title: str, icon: QIcon):
        super().__init__()
        self.setWindowTitle(title)
        self.setWindowIcon(icon)
        self.resize(1080, 680)
        self.setMinimumSize(860, 520)
        self.setStyleSheet(f"QMainWindow, QWidget#content {{ background: {theme.BG}; }} "
                           f"QLabel {{ background: transparent; }}")
        self._shown_key = ""
        self._playing_key = ""
        self._playing_index = -1
        self._close_to_tray = False
        self._quitting = False
        self._presented = False

        self.sidebar = PlaylistSidebar()
        self.table = TrackTable()
        self.player = PlayerBar()

        content = QWidget()
        content.setObjectName("content")
        column = QVBoxLayout(content)
        column.setContentsMargins(28, 24, 28, 12)
        column.setSpacing(6)

        self._title = QLabel("Importa una playlist para empezar")
        self._title.setWordWrap(True)
        self._title.setStyleSheet(f"font-size: 26px; font-weight: 700; color: {theme.TEXT};")
        self._subtitle = QLabel("Pega un enlace de compartir de YouTube Music o de Spotify en el panel izquierdo.")
        self._subtitle.setWordWrap(True)
        self._subtitle.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_SECONDARY};")
        column.addWidget(self._title)
        column.addWidget(self._subtitle)

        self._play_all = QPushButton("Reproducir")
        self._play_all.setCursor(Qt.PointingHandCursor)
        self._play_all.setStyleSheet(theme.button_qss("primary", height=38))
        self._play_all.setIcon(qta.icon("fa5s.play", color="#0f0f0f"))
        self._play_all.clicked.connect(lambda: self._emit_for_shown(self.play_all_requested))
        self._play_all.hide()
        self._shuffle = QPushButton("Aleatorio")
        self._shuffle.setCursor(Qt.PointingHandCursor)
        self._shuffle.setIcon(qta.icon("fa5s.random", color=theme.TEXT))
        self._shuffle.clicked.connect(lambda: self._emit_for_shown(self.shuffle_requested))
        self._shuffle.hide()
        self.set_shuffle_active(False)
        actions = QHBoxLayout()
        actions.setContentsMargins(0, 10, 0, 6)
        actions.setSpacing(10)
        actions.addWidget(self._play_all)
        actions.addWidget(self._shuffle)
        actions.addStretch(1)
        column.addLayout(actions)
        column.addWidget(self.table, 1)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self.sidebar)
        body.addWidget(content, 1)
        body_widget = QWidget()
        body_widget.setLayout(body)

        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(body_widget, 1)
        root.addWidget(self.player)
        holder = QWidget()
        holder.setLayout(root)
        self.setCentralWidget(holder)

        self.sidebar.settings_requested.connect(self.settings_requested)
        self.table.play_requested.connect(lambda index: self.play_requested.emit(self._shown_key, index))

    @property
    def shown_key(self) -> str:
        return self._shown_key

    def show_playlist(self, playlist: Playlist | None) -> None:
        self._shown_key = playlist.key if playlist else ""
        self.table.set_playlist(playlist)
        self._play_all.setVisible(playlist is not None)
        self._shuffle.setVisible(playlist is not None)
        if playlist is None:
            self._title.setText("Importa una playlist para empezar")
            self._subtitle.setText("Pega un enlace de compartir de YouTube Music o de Spotify en el panel izquierdo.")
            return
        origin = "Spotify" if playlist.source == SOURCE_SPOTIFY else "YouTube Music"
        by = f" · de {playlist.author}" if playlist.author else ""
        self._title.setText(playlist.title)
        self._subtitle.setText(f"{origin}{by} · {len(playlist.tracks)} canciones")
        self._highlight()

    def show_now_playing(self, key: str, index: int, track: Track | None) -> None:
        self._playing_key, self._playing_index = key, index
        self.player.set_track(track.title if track else "", track.artist if track else "")
        self._highlight()

    def _highlight(self) -> None:
        if self._shown_key and self._shown_key == self._playing_key:
            self.table.set_current(self._playing_index)

    def confirm_delete(self, title: str) -> bool:
        return dialogs.confirm(
            self, "¿Eliminar playlist?",
            f"«{title}» se quitará de tu biblioteca. La playlist original en YouTube Music o Spotify no se modifica.",
            ok="Eliminar", cancel="Cancelar")

    def set_shuffle_active(self, active: bool) -> None:
        self._shuffle.setStyleSheet(theme.button_qss("primary" if active else "tonal", height=38))
        self._shuffle.setIcon(qta.icon("fa5s.random", color="#0f0f0f" if active else theme.TEXT))

    def notify(self, text: str) -> None:
        self.statusBar().showMessage(text, 6000)

    def _emit_for_shown(self, signal) -> None:
        if self._shown_key:
            signal.emit(self._shown_key)

    @property
    def is_presented(self) -> bool:
        return self.isVisible() and not self.isMinimized()

    def set_close_to_tray(self, enabled: bool) -> None:
        self._close_to_tray = enabled

    def restore(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def quit_app(self) -> None:
        self._quitting = True
        self.close()

    def _emit_presence(self) -> None:
        presented = self.is_presented
        if presented != self._presented:
            self._presented = presented
            self.presence_changed.emit(presented)

    def showEvent(self, event):
        super().showEvent(event)
        self._emit_presence()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._emit_presence()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange:
            self._emit_presence()

    def closeEvent(self, event):
        if self._close_to_tray and not self._quitting:
            event.ignore()
            self.hide()
            return
        self.closed.emit()
        super().closeEvent(event)
