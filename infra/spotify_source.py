from __future__ import annotations

import json
import logging
import re

import requests

from domain.models import SOURCE_SPOTIFY, Playlist, Track
from infra.ytmusic_source import ImportFailed

log = logging.getLogger(__name__)

EMBED_URL = "https://open.spotify.com/embed/playlist/{}"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
_NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)


# spotify embed sin cuenta
class SpotifySource:
    def __init__(self, timeout: int = 15):
        self._timeout = timeout

    def resolve_redirect(self, url: str) -> str:
        try:
            response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=self._timeout, allow_redirects=True)
        except requests.RequestException as exc:
            raise ImportFailed(f"No se pudo abrir el enlace corto de Spotify: {exc.__class__.__name__}") from exc
        return response.url

    def fetch_playlist(self, playlist_id: str) -> Playlist:
        try:
            response = requests.get(EMBED_URL.format(playlist_id), headers={"User-Agent": USER_AGENT},
                                    timeout=self._timeout)
        except requests.RequestException as exc:
            raise ImportFailed(f"No se pudo conectar con Spotify: {exc.__class__.__name__}") from exc
        if response.status_code == 404:
            raise ImportFailed("La playlist de Spotify no existe o es privada.")
        if response.status_code != 200:
            raise ImportFailed(f"Spotify respondió con el código {response.status_code}.")
        return playlist_from_embed(playlist_id, response.text)


def _entity(html: str) -> dict:
    match = _NEXT_DATA.search(html)
    if not match:
        raise ImportFailed("Spotify cambió el formato de la página y no se pudo leer la playlist.")
    try:
        data = json.loads(match.group(1))
        return data["props"]["pageProps"]["state"]["data"]["entity"]
    except (ValueError, KeyError, TypeError) as exc:
        raise ImportFailed("Spotify cambió el formato de la página y no se pudo leer la playlist.") from exc


def playlist_from_embed(playlist_id: str, html: str) -> Playlist:
    entity = _entity(html)
    tracks = []
    for item in entity.get("trackList") or []:
        title = (item.get("title") or "").strip()
        if not title or item.get("entityType", "track") != "track":
            continue
        uri = item.get("uri") or ""
        tracks.append(Track(
            title=title,
            artist=(item.get("subtitle") or "").replace("\xa0", " ").strip(),
            duration_s=int(round((item.get("duration") or 0) / 1000)),
            source_id=uri.rsplit(":", 1)[-1],
        ))
    if not tracks:
        raise ImportFailed("La playlist de Spotify está vacía o es privada.")
    return Playlist(
        source=SOURCE_SPOTIFY,
        source_id=playlist_id,
        title=entity.get("name") or entity.get("title") or "Playlist",
        url=f"https://open.spotify.com/playlist/{playlist_id}",
        author=entity.get("subtitle") or "",
        tracks=tuple(tracks),
    )
