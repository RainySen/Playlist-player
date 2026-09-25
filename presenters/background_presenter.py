from __future__ import annotations

from PySide6.QtWidgets import QApplication

from domain.settings import Settings
from services.player_service import PlayerService
from services.settings_service import SettingsService
from ui.components.mini_player import MiniPlayer
from ui.main_window import MainWindow
from ui.settings_dialog import SettingsDialog
from ui.tray import TrayController

MINI_MARGIN = 24


# segundo plano bandeja mini reproductor
class BackgroundPresenter:
    def __init__(self, window: MainWindow, tray: TrayController, mini: MiniPlayer, player: PlayerService,
                 settings: SettingsService):
        self._window = window
        self._tray = tray
        self._mini = mini
        self._player = player
        self._settings = settings
        self._announced = False
        self._tray_available = tray.available()

        window.settings_requested.connect(self.open_settings)
        window.presence_changed.connect(self._on_presence)
        settings.changed.connect(lambda _: self._apply())

        player.track_changed.connect(self._on_track)
        player.state_changed.connect(self._on_state)
        player.position_changed.connect(mini.set_position)

        tray.show_requested.connect(window.restore)
        tray.toggle_requested.connect(player.toggle_pause)
        tray.next_requested.connect(player.next)
        tray.previous_requested.connect(player.previous)
        tray.quit_requested.connect(window.quit_app)

        mini.toggle_requested.connect(player.toggle_pause)
        mini.next_requested.connect(player.next)
        mini.previous_requested.connect(player.previous)
        mini.expand_requested.connect(window.restore)
        mini.moved.connect(lambda x, y: settings.update(mini_x=x, mini_y=y))

        tray.show()
        self._apply()

    def open_settings(self) -> None:
        current = self._settings.settings
        dialog = SettingsDialog(self._window, current, self._tray_available, self._settings.update)
        dialog.exec()

    def _apply(self) -> None:
        settings = self._settings.settings
        self._window.set_close_to_tray(settings.background_playback and self._tray_available)
        self._refresh_mini()

    def _on_track(self, _key: str, _index: int) -> None:
        track = self._player.current_track()
        title, artist = (track.title, track.artist) if track else ("", "")
        self._mini.set_track(title, artist)
        self._tray.set_track(f"{title} · {artist}" if track else "")
        self._refresh_mini()

    def _on_state(self, playing: bool) -> None:
        self._mini.set_playing(playing)
        self._tray.set_playing(playing)

    def _on_presence(self, presented: bool) -> None:
        self._refresh_mini()
        if not presented and not self._window.isMinimized() and not self._announced and self._player.current_track():
            self._announced = True
            self._tray.notify("Sigue sonando en segundo plano. Usa el icono de la bandeja para volver.")

    def _refresh_mini(self) -> None:
        settings = self._settings.settings
        wanted = (settings.mini_player and not self._window.is_presented and self._player.current_track() is not None)
        if wanted:
            self._place_mini(settings)
            self._mini.show()
        else:
            self._mini.hide()

    def _place_mini(self, settings: Settings) -> None:
        if self._mini.isVisible():
            return
        if settings.mini_x is not None and settings.mini_y is not None:
            self._mini.move(settings.mini_x, settings.mini_y)
            return
        screen = QApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            self._mini.move(area.right() - self._mini.width() - MINI_MARGIN,
                            area.bottom() - self._mini.height() - MINI_MARGIN)
