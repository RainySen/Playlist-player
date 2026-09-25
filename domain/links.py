from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

from domain.models import SOURCE_SPOTIFY, SOURCE_YTMUSIC

_YT_HOSTS = {"music.youtube.com", "www.youtube.com", "youtube.com", "m.youtube.com"}
_SPOTIFY_HOSTS = {"open.spotify.com", "play.spotify.com"}
_SHORT_HOSTS = {"spotify.link", "spoti.fi"}
_SPOTIFY_ID = re.compile(r"^[A-Za-z0-9]{22}$")
_SPOTIFY_URI = re.compile(r"^spotify:playlist:([A-Za-z0-9]{22})$")
_YT_ID = re.compile(r"^[A-Za-z0-9_-]{10,64}$")


class LinkError(ValueError):
    pass


# enlace compartir origen
@dataclass(frozen=True)
class LinkRef:
    source: str
    source_id: str
    needs_redirect: bool = False
    raw: str = ""


# leer enlace playlist
def parse_link(text: str) -> LinkRef:
    raw = (text or "").strip().strip("<>\"'")
    if not raw:
        raise LinkError("Pega un enlace de una playlist.")

    uri = _SPOTIFY_URI.match(raw)
    if uri:
        return LinkRef(SOURCE_SPOTIFY, uri.group(1), raw=raw)

    if "://" not in raw:
        raw = "https://" + raw
    parsed = urlparse(raw)
    host = (parsed.hostname or "").lower()

    if host in _SHORT_HOSTS:
        return LinkRef("", "", needs_redirect=True, raw=raw)

    if host in _SPOTIFY_HOSTS:
        return _parse_spotify_path(parsed.path, raw)

    if host in _YT_HOSTS:
        return _parse_youtube(parsed, raw)

    raise LinkError("El enlace no es de YouTube Music ni de Spotify.")


def _parse_spotify_path(path: str, raw: str) -> LinkRef:
    parts = [p for p in path.split("/") if p]
    if parts and parts[0].startswith("intl-"):
        parts = parts[1:]
    if len(parts) >= 2 and parts[0] == "playlist" and _SPOTIFY_ID.match(parts[1]):
        return LinkRef(SOURCE_SPOTIFY, parts[1], raw=raw)
    if parts and parts[0] in ("album", "track", "artist"):
        raise LinkError("Solo se pueden importar playlists de Spotify, no álbumes, canciones ni artistas.")
    raise LinkError("No se reconoce el enlace de Spotify.")


def _parse_youtube(parsed, raw: str) -> LinkRef:
    values = parse_qs(parsed.query).get("list")
    playlist_id = values[0] if values else ""
    if not playlist_id and parsed.path.startswith("/browse/VL"):
        playlist_id = parsed.path[len("/browse/VL"):]
    if playlist_id.startswith("VL"):
        playlist_id = playlist_id[2:]
    if not _YT_ID.match(playlist_id):
        raise LinkError("El enlace de YouTube no contiene una playlist (falta el parámetro list=).")
    return LinkRef(SOURCE_YTMUSIC, playlist_id, raw=raw)
