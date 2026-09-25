from __future__ import annotations

import logging
import random

from PySide6.QtCore import QObject, Signal

from domain.models import Track
from infra.concurrency import TaskRunner
from services.library_service import LibraryService
from services.match_service import MatchService
from services.stream_service import StreamService

log = logging.getLogger(__name__)

MATCH_KEY = "match"
RESTART_AFTER_S = 3


# reproductor cola playlist
class PlayerService(QObject):
    track_changed = Signal(str, int)
    state_changed = Signal(bool)
    position_changed = Signal(float)
    time_changed = Signal(int, int)
    message = Signal(str)
    stopped = Signal()
    shuffle_changed = Signal(bool)
    repeat_changed = Signal(bool)

    def __init__(self, audio, streams: StreamService, library: LibraryService, matcher: MatchService,
                 match_runner: TaskRunner, prefetch_runner: TaskRunner, prefetch_ahead: int,
                 max_failures: int, parent: QObject | None = None, rng: random.Random | None = None):
        super().__init__(parent)
        self._audio = audio
        self._streams = streams
        self._library = library
        self._matcher = matcher
        self._match_runner = match_runner
        self._prefetch_runner = prefetch_runner
        self._prefetch_ahead = prefetch_ahead
        self._max_failures = max_failures
        self._rng = rng or random.Random()

        self._key = ""
        self._tracks: list[Track] = []
        self._index = -1
        self._order: list[int] = []
        self._pos = -1
        self._shuffle = False
        self._repeat = False
        self._seconds = 0
        self._failures = 0
        self._matching: set[tuple[str, int]] = set()

        streams.resolved.connect(self._on_resolved)
        streams.failed.connect(self._on_stream_failed)
        audio.finished.connect(self._on_finished)
        audio.failed.connect(self._on_audio_failed)
        audio.position_changed.connect(self.position_changed)
        audio.time_changed.connect(self._on_time)

    @property
    def current_key(self) -> str:
        return self._key

    @property
    def current_index(self) -> int:
        return self._index

    @property
    def shuffle(self) -> bool:
        return self._shuffle

    @property
    def repeat(self) -> bool:
        return self._repeat

    def current_track(self) -> Track | None:
        return self._tracks[self._index] if 0 <= self._index < len(self._tracks) else None

    # reproducir playlist indice
    def play_playlist(self, key: str, index: int | None = None, shuffle: bool | None = None) -> None:
        playlist = self._library.get(key)
        if playlist is None or not playlist.tracks:
            return
        self._key = key
        self._tracks = list(playlist.tracks)
        self._failures = 0
        self._set_shuffle(self._shuffle if shuffle is None else shuffle)
        if index is None:
            index = self._rng.randrange(len(self._tracks)) if self._shuffle else 0
        self._order, self._pos = self._build_order(index)
        self._start(self._pos)

    # aleatorio orden
    def _build_order(self, start: int) -> tuple[list[int], int]:
        order = list(range(len(self._tracks)))
        if not self._shuffle:
            return order, start
        self._rng.shuffle(order)
        order.remove(start)
        order.insert(0, start)
        return order, 0

    def _set_shuffle(self, enabled: bool) -> None:
        if enabled != self._shuffle:
            self._shuffle = enabled
            self.shuffle_changed.emit(enabled)

    def set_shuffle(self, enabled: bool) -> None:
        self._set_shuffle(enabled)
        if self._tracks and self._index >= 0:
            self._order, self._pos = self._build_order(self._index)

    def set_repeat(self, enabled: bool) -> None:
        if enabled != self._repeat:
            self._repeat = enabled
            self.repeat_changed.emit(enabled)

    def toggle_pause(self) -> None:
        if self._audio.is_playing:
            self._audio.pause()
            self.state_changed.emit(False)
        elif self._audio.has_media:
            self._audio.resume()
            self.state_changed.emit(True)
        elif self.current_track() is not None:
            self._start(self._pos)

    def next(self) -> None:
        self._start(self._pos + 1)

    def previous(self) -> None:
        if self._seconds > RESTART_AFTER_S or self._pos <= 0:
            self._start(max(self._pos, 0))
        else:
            self._start(self._pos - 1)

    def seek(self, fraction: float) -> None:
        self._audio.seek(fraction)

    def set_volume(self, volume: int) -> None:
        self._audio.set_volume(volume)

    def stop(self) -> None:
        self._audio.stop()
        self._seconds = 0
        self.state_changed.emit(False)
        self.stopped.emit()

    def _start(self, pos: int) -> None:
        if not 0 <= pos < len(self._order):
            self.stop()
            return
        self._audio.stop()
        self._pos = pos
        index = self._order[pos]
        self._index = index
        self._seconds = 0
        self.track_changed.emit(self._key, index)
        self.state_changed.emit(True)
        track = self._tracks[index]
        if track.video_id:
            self._streams.request(track.video_id)
            self._prefetch(pos)
            return
        key = self._key
        self._matching.add((key, index))
        self._match_runner.submit(
            lambda: self._matcher.find_video(track),
            lambda video_id: self._on_matched(key, index, video_id, play=True),
            lambda exc: self._on_match_failed(key, index, exc, play=True),
            key=MATCH_KEY,
        )

    def _on_matched(self, key: str, index: int, video_id: str, play: bool) -> None:
        self._matching.discard((key, index))
        self._library.set_track_video(key, index, video_id)
        if key != self._key or index >= len(self._tracks):
            return
        self._tracks[index] = self._tracks[index].with_video(video_id)
        if play and index == self._index:
            self._streams.request(video_id)
            self._prefetch(self._pos)
        elif not play:
            self._streams.prefetch([video_id])

    def _on_match_failed(self, key: str, index: int, exc: Exception, play: bool) -> None:
        self._matching.discard((key, index))
        if not play or key != self._key or index != self._index:
            return
        self._fail(str(exc))

    def _prefetch(self, pos: int) -> None:
        upcoming = [self._order[p] for p in range(pos + 1, min(pos + 1 + self._prefetch_ahead, len(self._order)))]
        ready = [self._tracks[i].video_id for i in upcoming if self._tracks[i].video_id]
        self._streams.prefetch(ready)
        for i in upcoming:
            track = self._tracks[i]
            if track.video_id or (self._key, i) in self._matching:
                continue
            key = self._key
            self._matching.add((key, i))
            self._prefetch_runner.submit(
                lambda t=track: self._matcher.find_video(t),
                lambda video_id, i=i: self._on_matched(key, i, video_id, play=False),
                lambda exc, i=i: self._on_match_failed(key, i, exc, play=False),
            )

    def _on_resolved(self, video_id: str, info) -> None:
        track = self.current_track()
        if track is None or track.video_id != video_id or self._audio.is_playing or self._audio.has_media:
            return
        self._audio.play_url(info.url)
        self.state_changed.emit(True)

    def _on_stream_failed(self, video_id: str, message: str) -> None:
        track = self.current_track()
        if track is not None and track.video_id == video_id:
            self._fail(message)

    def _on_audio_failed(self) -> None:
        track = self.current_track()
        if track is not None and track.video_id:
            self._streams.invalidate(track.video_id)
        self._fail("El reproductor no pudo abrir la canción.")

    def _on_finished(self) -> None:
        self._failures = 0
        self._start(self._pos if self._repeat else self._pos + 1)

    def _on_time(self, elapsed: int, total: int) -> None:
        self._seconds = elapsed
        self._failures = 0
        self.time_changed.emit(elapsed, total)

    def _fail(self, reason: str) -> None:
        track = self.current_track()
        name = track.title if track else "la canción"
        self._failures += 1
        self.message.emit(f"No se pudo reproducir «{name}»: {reason}")
        if self._failures >= self._max_failures:
            self.stop()
            return
        self.next()
