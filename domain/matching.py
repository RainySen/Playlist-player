from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

from domain.models import Track

_BRACKETS = re.compile(r"[\(\[][^)\]]*[\)\]]")
_SUFFIX = re.compile(r"\s+-\s+(remaster(ed)?|single|radio edit|live|version|mono|stereo|\d{4}).*$")
_NOISE = re.compile(r"[^a-z0-9 ]+")
_SPLIT = re.compile(r"\s*(?:,|&|;| feat\.? | ft\.? | x | con | with )\s*")


@dataclass(frozen=True)
class Candidate:
    video_id: str
    title: str
    artist: str
    duration_s: int = 0


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
    text = _BRACKETS.sub(" ", text)
    text = _SUFFIX.sub("", text)
    text = _NOISE.sub(" ", text)
    return " ".join(text.split())


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def _artist_names(text: str) -> set[str]:
    return {n for n in (normalize(part) for part in _SPLIT.split(text or "")) if n}


def _artist_score(wanted: str, found: str) -> float:
    left, right = _artist_names(wanted), _artist_names(found)
    if not left or not right:
        return 0.0
    hits = sum(1 for name in left if any(name == other or name in other or other in name for other in right))
    return hits / len(left)


def _duration_score(wanted: int, found: int) -> float:
    if wanted <= 0 or found <= 0:
        return -1.0
    diff = abs(wanted - found)
    if diff <= 3:
        return 1.0
    if diff >= 30:
        return 0.0
    return 1.0 - (diff - 3) / 27


# puntuar coincidencia cancion
def score(track: Track, candidate: Candidate) -> float:
    title = _similarity(normalize(track.title), normalize(candidate.title))
    artist = _artist_score(track.artist, candidate.artist)
    duration = _duration_score(track.duration_s, candidate.duration_s)
    if duration < 0:
        return 0.65 * title + 0.35 * artist
    return 0.5 * title + 0.3 * artist + 0.2 * duration


# elegir mejor candidato
def best_match(track: Track, candidates: list[Candidate], minimum: float) -> Candidate | None:
    best, best_score = None, 0.0
    for candidate in candidates:
        value = score(track, candidate)
        if value > best_score:
            best, best_score = candidate, value
    return best if best is not None and best_score >= minimum else None
