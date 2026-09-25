from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QIcon

from core import config
from core.config import AppPaths
from domain.stream_cache import StreamCache
from infra.audio_backend import VlcAudioBackend
from infra.concurrency import TaskRunner
from infra.library_repository import LibraryRepository
from infra.settings_repository import SettingsRepository
from infra.spotify_source import SpotifySource
from infra.stream_resolver import YtDlpStreamResolver
from infra.ytmusic_source import YtMusicSource
from presenters.background_presenter import BackgroundPresenter
from presenters.library_presenter import LibraryPresenter
from presenters.player_presenter import PlayerPresenter
from services.library_service import LibraryService
from services.match_service import MatchService
from services.player_service import PlayerService
from services.settings_service import SettingsService
from services.stream_service import StreamService
from ui.components.mini_player import MiniPlayer
from ui.main_window import MainWindow
from ui.tray import TrayController


# raiz composicion
@dataclass
class UserInterface:
    window: MainWindow
    library: LibraryService
    player: PlayerService
    runners: list[TaskRunner]
    presenters: list[object]
    tray: TrayController
    mini: MiniPlayer

    def shutdown(self) -> None:
        self.mini.hide()
        self.tray.hide()
        self.player.stop()
        for runner in self.runners:
            runner.shutdown()


def build(paths: AppPaths, icon: QIcon) -> UserInterface:
    import_runner = TaskRunner("import", max_threads=2)
    match_runner = TaskRunner("match", max_threads=2)
    prefetch_runner = TaskRunner("prefetch", max_threads=2)
    play_runner = TaskRunner("play", max_threads=2)

    ytmusic = YtMusicSource()
    spotify = SpotifySource()
    library = LibraryService(LibraryRepository(paths.library_file), ytmusic, spotify, import_runner)

    audio = VlcAudioBackend(config.NETWORK_CACHING_MS)
    streams = StreamService(YtDlpStreamResolver(paths.ytdlp_cache_dir),
                            StreamCache(margin=config.STREAM_EXPIRY_MARGIN_S), play_runner, prefetch_runner)
    matcher = MatchService(ytmusic, config.MATCH_SEARCH_LIMIT, config.MATCH_MIN_SCORE)
    player = PlayerService(audio, streams, library, matcher, match_runner, prefetch_runner,
                           config.PREFETCH_AHEAD, config.MAX_CONSECUTIVE_FAILURES)

    window = MainWindow(config.APP_NAME, icon)
    settings = SettingsService(SettingsRepository(paths.settings_file))
    tray = TrayController(icon, config.APP_NAME)
    mini = MiniPlayer()
    presenters = [PlayerPresenter(window, player, library), LibraryPresenter(window, library),
                  BackgroundPresenter(window, tray, mini, player, settings)]
    return UserInterface(window, library, player, [import_runner, match_runner, prefetch_runner, play_runner],
                         presenters, tray, mini)
