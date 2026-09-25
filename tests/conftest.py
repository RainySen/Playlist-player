import os
import random
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from domain.models import SOURCE_YTMUSIC, Playlist, Track
from domain.stream_cache import StreamCache, StreamInfo
from infra.concurrency import TaskRunner
from infra.library_repository import LibraryRepository
from services.library_service import LibraryService
from services.match_service import MatchService
from services.player_service import PlayerService
from services.stream_service import StreamService


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


def wait_until(app, condition, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.005)
    app.processEvents()
    return condition()


class FakeAudio(QObject):
    finished = Signal()
    failed = Signal()
    position_changed = Signal(float)
    time_changed = Signal(int, int)

    def __init__(self):
        super().__init__()
        self.is_playing = False
        self.has_media = False
        self.urls = []
        self.volume = None

    def play_url(self, url):
        self.urls.append(url)
        self.is_playing = True
        self.has_media = True

    def pause(self):
        self.is_playing = False

    def resume(self):
        self.is_playing = True

    def stop(self):
        self.is_playing = False
        self.has_media = False

    def seek(self, fraction):
        self.sought = fraction

    def set_volume(self, volume):
        self.volume = volume


class FakeResolver:
    def __init__(self, failing=()):
        self.failing = set(failing)
        self.calls = []

    def resolve(self, video_id):
        self.calls.append(video_id)
        if video_id in self.failing:
            raise RuntimeError("bloqueado")
        return StreamInfo(video_id, f"http://stream/{video_id}", video_id, time.time() + 3600)


class FakeSearch:
    def __init__(self, mapping):
        self.mapping = mapping
        self.queries = []

    def search(self, query, limit):
        self.queries.append(query)
        return self.mapping.get(query, [])


class FakeSource:
    def __init__(self, playlist=None, error=None):
        self.playlist = playlist
        self.error = error
        self.fetched = []

    def fetch_playlist(self, playlist_id):
        self.fetched.append(playlist_id)
        if self.error:
            raise self.error
        return self.playlist

    def resolve_redirect(self, url):
        return self.redirect


def make_playlist(source=SOURCE_YTMUSIC, source_id="PL1", tracks=None, title="Mix"):
    tracks = tracks if tracks is not None else [
        Track("Uno", "Artista A", 100, video_id="v1", source_id="v1"),
        Track("Dos", "Artista B", 120, video_id="v2", source_id="v2"),
        Track("Tres", "Artista C", 140, video_id="v3", source_id="v3"),
    ]
    return Playlist(source, source_id, title, tracks=tuple(tracks))


class Rig:
    def __init__(self, app, tmp_path, *, playlist=None, failing=(), search=None, source=None):
        self.app = app
        self.audio = FakeAudio()
        self.resolver = FakeResolver(failing)
        self.search = FakeSearch(search or {})
        self.runners = [TaskRunner(n, max_threads=2) for n in ("import", "match", "prefetch", "play")]
        self.repo = LibraryRepository(str(tmp_path / "library.json"))
        self.ytmusic = source or FakeSource(playlist)
        self.spotify = FakeSource(playlist)
        self.library = LibraryService(self.repo, self.ytmusic, self.spotify, self.runners[0])
        self.streams = StreamService(self.resolver, StreamCache(), self.runners[3], self.runners[2])
        self.matcher = MatchService(self.search, 5, 0.45)
        self.player = PlayerService(self.audio, self.streams, self.library, self.matcher,
                                    self.runners[1], self.runners[2], 2, 3, rng=random.Random(7))

    def dispose(self):
        for runner in self.runners:
            runner.shutdown()
        self.app.processEvents()


@pytest.fixture
def rig(qapp, tmp_path):
    made = []

    def build(**kwargs):
        r = Rig(qapp, tmp_path, **kwargs)
        made.append(r)
        return r

    yield build
    for r in made:
        r.dispose()
