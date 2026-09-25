import os
import sys
from dataclasses import dataclass

APP_NAME = "Playlist Player"
DATA_DIR_NAME = "data"

NETWORK_CACHING_MS = 3000
STREAM_EXPIRY_MARGIN_S = 120
PREFETCH_AHEAD = 2
MAX_CONSECUTIVE_FAILURES = 3
SPOTIFY_EMBED_LIMIT = 100
MATCH_SEARCH_LIMIT = 5
MATCH_MIN_SCORE = 0.45


# rutas archivos datos
@dataclass(frozen=True)
class AppPaths:
    base_dir: str

    @staticmethod
    def detect() -> "AppPaths":
        if getattr(sys, "frozen", False):
            return AppPaths(os.path.dirname(sys.executable))
        return AppPaths(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    @property
    def data_dir(self) -> str:
        return os.path.join(self.base_dir, DATA_DIR_NAME)

    @property
    def library_file(self) -> str:
        return os.path.join(self.data_dir, "library.json")

    @property
    def settings_file(self) -> str:
        return os.path.join(self.data_dir, "settings.json")

    @property
    def ytdlp_cache_dir(self) -> str:
        return os.path.join(self.data_dir, ".yt-dlp-cache")

    @property
    def log_file(self) -> str:
        return os.path.join(self.data_dir, "playlist-player.log")

    def ensure_dirs(self) -> None:
        os.makedirs(self.ytdlp_cache_dir, exist_ok=True)
