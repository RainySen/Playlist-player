from __future__ import annotations

import logging

from domain.models import Playlist
from infra.json_store import read_json, write_json_atomic

log = logging.getLogger(__name__)


# biblioteca playlists json
class LibraryRepository:
    def __init__(self, path: str):
        self._path = path
        self._items: dict[str, Playlist] = {}
        self._load()

    def _load(self) -> None:
        for raw in read_json(self._path, default=[]) or []:
            try:
                playlist = Playlist.from_dict(raw)
            except (KeyError, TypeError, ValueError):
                log.warning("Skipping unreadable playlist entry")
                continue
            self._items[playlist.key] = playlist

    def all(self) -> list[Playlist]:
        return list(self._items.values())

    def get(self, key: str) -> Playlist | None:
        return self._items.get(key)

    def put(self, playlist: Playlist) -> None:
        self._items[playlist.key] = playlist
        self._save()

    def remove(self, key: str) -> bool:
        if self._items.pop(key, None) is None:
            return False
        self._save()
        return True

    def _save(self) -> None:
        write_json_atomic(self._path, [p.to_dict() for p in self._items.values()])
