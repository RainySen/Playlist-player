from __future__ import annotations

from dataclasses import dataclass, field, replace

SOURCE_YTMUSIC = "ytmusic"
SOURCE_SPOTIFY = "spotify"


# pista cancion
@dataclass(frozen=True)
class Track:
    title: str
    artist: str
    duration_s: int = 0
    video_id: str = ""
    source_id: str = ""

    @property
    def playable(self) -> bool:
        return bool(self.video_id)

    def with_video(self, video_id: str) -> "Track":
        return replace(self, video_id=video_id)

    def to_dict(self) -> dict:
        return {"title": self.title, "artist": self.artist, "duration_s": self.duration_s,
                "video_id": self.video_id, "source_id": self.source_id}

    @staticmethod
    def from_dict(data: dict) -> "Track":
        return Track(
            title=str(data.get("title") or ""),
            artist=str(data.get("artist") or ""),
            duration_s=int(data.get("duration_s") or 0),
            video_id=str(data.get("video_id") or ""),
            source_id=str(data.get("source_id") or ""),
        )


# playlist importada
@dataclass(frozen=True)
class Playlist:
    source: str
    source_id: str
    title: str
    url: str = ""
    author: str = ""
    tracks: tuple[Track, ...] = field(default_factory=tuple)

    @property
    def key(self) -> str:
        return f"{self.source}:{self.source_id}"

    def with_tracks(self, tracks) -> "Playlist":
        return replace(self, tracks=tuple(tracks))

    def with_track_video(self, index: int, video_id: str) -> "Playlist":
        tracks = list(self.tracks)
        tracks[index] = tracks[index].with_video(video_id)
        return self.with_tracks(tracks)

    def to_dict(self) -> dict:
        return {"source": self.source, "source_id": self.source_id, "title": self.title, "url": self.url,
                "author": self.author, "tracks": [t.to_dict() for t in self.tracks]}

    @staticmethod
    def from_dict(data: dict) -> "Playlist":
        return Playlist(
            source=str(data["source"]),
            source_id=str(data["source_id"]),
            title=str(data.get("title") or ""),
            url=str(data.get("url") or ""),
            author=str(data.get("author") or ""),
            tracks=tuple(Track.from_dict(t) for t in data.get("tracks") or []),
        )


def format_duration(seconds: int) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"
