from __future__ import annotations

import logging
from typing import Protocol

from PySide6.QtCore import QObject, Signal

from domain.links import LinkError, LinkRef, parse_link
from domain.models import SOURCE_SPOTIFY, SOURCE_YTMUSIC, Playlist, Track
from infra.concurrency import TaskRunner
from infra.library_repository import LibraryRepository
from infra.ytmusic_source import ImportFailed

log = logging.getLogger(__name__)

IMPORT_KEY = "import"

OUTCOME_CREATED = "created"
OUTCOME_UPDATED = "updated"
OUTCOME_UNCHANGED = "unchanged"


def _track_identity(track: Track) -> tuple[str, ...]:
    if track.source_id:
        return (track.source_id,)
    return (track.title.casefold(), track.artist.casefold())


def _count_new_tracks(previous: Playlist, fetched: Playlist) -> int:
    known = {_track_identity(t) for t in previous.tracks}
    return sum(1 for t in fetched.tracks if _track_identity(t) not in known)


class PlaylistSource(Protocol):
    def fetch_playlist(self, playlist_id: str) -> Playlist: ...


# biblioteca importar playlists
class LibraryService(QObject):
    changed = Signal()
    import_started = Signal()
    import_finished = Signal(str)
    import_outcome = Signal(str, int)
    import_failed = Signal(str)

    def __init__(self, repo: LibraryRepository, ytmusic: PlaylistSource, spotify, runner: TaskRunner,
                 parent: QObject | None = None):
        super().__init__(parent)
        self._repo = repo
        self._sources = {SOURCE_YTMUSIC: ytmusic, SOURCE_SPOTIFY: spotify}
        self._spotify = spotify
        self._runner = runner

    def playlists(self) -> list[Playlist]:
        return self._repo.all()

    def get(self, key: str) -> Playlist | None:
        return self._repo.get(key)

    def remove(self, key: str) -> None:
        if self._repo.remove(key):
            self.changed.emit()

    def set_track_video(self, key: str, index: int, video_id: str) -> None:
        playlist = self._repo.get(key)
        if playlist is None or not 0 <= index < len(playlist.tracks):
            return
        self._repo.put(playlist.with_track_video(index, video_id))

    # importar enlace compartir
    def import_link(self, text: str) -> None:
        try:
            ref = parse_link(text)
        except LinkError as exc:
            self.import_failed.emit(str(exc))
            return
        self.import_started.emit()
        self._runner.submit(lambda: self._fetch(ref), self._on_fetched, self._on_failed, key=IMPORT_KEY)

    def _fetch(self, ref: LinkRef) -> Playlist:
        if ref.needs_redirect:
            ref = parse_link(self._spotify.resolve_redirect(ref.raw))
        return self._sources[ref.source].fetch_playlist(ref.source_id)

    def _on_fetched(self, playlist: Playlist) -> None:
        previous = self._repo.get(playlist.key)
        added = 0 if previous is None else _count_new_tracks(previous, playlist)
        if previous is None or added:
            self._repo.put(self._keep_matches(playlist))
            self.changed.emit()
        self.import_finished.emit(playlist.key)
        outcome = OUTCOME_CREATED if previous is None else OUTCOME_UPDATED if added else OUTCOME_UNCHANGED
        self.import_outcome.emit(outcome, added)

    def _keep_matches(self, playlist: Playlist) -> Playlist:
        previous = self._repo.get(playlist.key)
        if previous is None:
            return playlist
        known = {t.source_id: t.video_id for t in previous.tracks if t.video_id and t.source_id}
        return playlist.with_tracks(
            t if t.video_id or t.source_id not in known else t.with_video(known[t.source_id])
            for t in playlist.tracks
        )

    def _on_failed(self, exc: Exception) -> None:
        if not isinstance(exc, (ImportFailed, LinkError)):
            log.error("Import failed", exc_info=exc)
            self.import_failed.emit("No se pudo importar la playlist. Revisa el enlace y tu conexión.")
            return
        self.import_failed.emit(str(exc))
