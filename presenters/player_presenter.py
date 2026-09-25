from __future__ import annotations

from services.library_service import LibraryService
from services.player_service import PlayerService
from ui.main_window import MainWindow


# reproductor vista controles
class PlayerPresenter:
    def __init__(self, window: MainWindow, player: PlayerService, library: LibraryService):
        self._window = window
        self._player = player
        self._library = library
        bar = window.player

        window.play_requested.connect(lambda key, index: player.play_playlist(key, index))
        window.play_all_requested.connect(lambda key: player.play_playlist(key, 0, shuffle=False))
        window.shuffle_requested.connect(lambda key: player.play_playlist(key, None, shuffle=True))
        bar.repeat_toggled.connect(player.set_repeat)
        bar.toggle_requested.connect(player.toggle_pause)
        bar.next_requested.connect(player.next)
        bar.previous_requested.connect(player.previous)
        bar.seek_requested.connect(player.seek)
        bar.volume_changed.connect(player.set_volume)

        player.track_changed.connect(self._on_track)
        player.state_changed.connect(bar.set_playing)
        player.position_changed.connect(bar.set_position)
        player.time_changed.connect(bar.set_time)
        player.message.connect(window.notify)
        player.shuffle_changed.connect(window.set_shuffle_active)
        player.repeat_changed.connect(bar.set_repeat)

    def _on_track(self, key: str, index: int) -> None:
        self._window.show_now_playing(key, index, self._player.current_track())
