from __future__ import annotations

import logging
import threading

from domain.matching import Candidate
from domain.models import SOURCE_YTMUSIC, Playlist, Track

log = logging.getLogger(__name__)


class ImportFailed(Exception):
    pass


def _artist_text(item: dict) -> str:
    return ", ".join(a["name"] for a in item.get("artists") or [] if a.get("name"))


# ytmusic playlist publica
class YtMusicSource:
    def __init__(self, client=None):
        self._lock = threading.Lock()
        self._client = client

    def _api(self):
        with self._lock:
            if self._client is None:
                from ytmusicapi import YTMusic

                self._client = YTMusic(language="es")
            return self._client

    def fetch_playlist(self, playlist_id: str) -> Playlist:
        try:
            data = self._api().get_playlist(playlist_id, limit=None)
        except Exception as exc:
            log.warning("YT Music playlist %s failed", playlist_id, exc_info=True)
            raise ImportFailed(f"No se pudo leer la playlist de YouTube Music: {_short(exc)}") from exc
        return playlist_from_ytmusic(playlist_id, data)

    # busqueda sin filtro el filtrado de ytmusicapi sin sesion devuelve vacio
    def search(self, query: str, limit: int) -> list[Candidate]:
        results = [r for r in self._api().search(query) if r.get("videoId")]
        songs = [r for r in results if r.get("resultType") == "song"]
        videos = [r for r in results if r.get("resultType") == "video"]
        return [candidate_from_result(r) for r in (songs or videos)[:limit]]


def playlist_from_ytmusic(playlist_id: str, data: dict) -> Playlist:
    tracks = []
    for item in data.get("tracks") or []:
        video_id = item.get("videoId")
        if not video_id or item.get("isAvailable") is False:
            continue
        tracks.append(Track(
            title=item.get("title") or "",
            artist=_artist_text(item),
            duration_s=int(item.get("duration_seconds") or 0),
            video_id=video_id,
            source_id=video_id,
        ))
    if not tracks:
        raise ImportFailed("La playlist está vacía o es privada.")
    author = (data.get("author") or {}).get("name", "") if isinstance(data.get("author"), dict) else ""
    return Playlist(
        source=SOURCE_YTMUSIC,
        source_id=playlist_id,
        title=data.get("title") or "Playlist",
        url=f"https://music.youtube.com/playlist?list={playlist_id}",
        author=author,
        tracks=tuple(tracks),
    )


def candidate_from_result(result: dict) -> Candidate:
    return Candidate(
        video_id=result["videoId"],
        title=result.get("title") or "",
        artist=_artist_text(result),
        duration_s=int(result.get("duration_seconds") or 0),
    )


def _short(exc: Exception) -> str:
    text = str(exc).strip().splitlines()[0] if str(exc).strip() else exc.__class__.__name__
    return text[:160]
