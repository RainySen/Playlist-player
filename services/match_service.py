from __future__ import annotations

from typing import Protocol

from domain.matching import Candidate, best_match
from domain.models import Track


class TrackNotFound(Exception):
    pass


class SongSearch(Protocol):
    def search(self, query: str, limit: int) -> list[Candidate]: ...


# spotify a youtube busqueda
class MatchService:
    def __init__(self, search: SongSearch, limit: int, minimum: float):
        self._search = search
        self._limit = limit
        self._minimum = minimum

    def find_video(self, track: Track) -> str:
        primary = track.artist.split(",")[0].strip()
        query = f"{primary} {track.title}".strip()
        candidates = self._search.search(query, self._limit)
        match = best_match(track, candidates, self._minimum)
        if match is None:
            raise TrackNotFound(f"No se encontró «{track.title}» en YouTube Music.")
        return match.video_id
