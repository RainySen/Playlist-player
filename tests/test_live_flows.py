import os
import time

import pytest

from core import config
from domain.links import parse_link
from infra.spotify_source import SpotifySource
from infra.stream_resolver import YtDlpStreamResolver
from infra.ytmusic_source import YtMusicSource
from services.match_service import MatchService

pytestmark = pytest.mark.skipif(os.environ.get("YTMUSIC_LIVE_TESTS") != "1", reason="usa la red real")

SPOTIFY_URL = "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M?si=live"


def test_import_public_youtube_music_playlist():
    from ytmusicapi import YTMusic

    source = YtMusicSource()
    assert source.search("Miley Cyrus Bass Persuades", 3)
    hits = [r for r in YTMusic(language="es").search("Miley Cyrus Bass Persuades") if r.get("resultType") == "playlist"]
    ref = parse_link("https://music.youtube.com/browse/" + hits[0]["browseId"])
    playlist = source.fetch_playlist(ref.source_id)
    assert playlist.tracks and all(t.video_id for t in playlist.tracks)


def test_import_public_spotify_playlist_and_match_first_track():
    ref = parse_link(SPOTIFY_URL)
    playlist = SpotifySource().fetch_playlist(ref.source_id)
    assert len(playlist.tracks) >= 10
    assert all(t.title and t.artist for t in playlist.tracks)
    matcher = MatchService(YtMusicSource(), config.MATCH_SEARCH_LIMIT, config.MATCH_MIN_SCORE)
    matched = sum(1 for t in playlist.tracks[:5] if _safe_find(matcher, t))
    assert matched >= 4


def _safe_find(matcher, track):
    try:
        return matcher.find_video(track)
    except Exception:
        return None


def test_resolve_stream_and_play_with_vlc(qapp, tmp_path):
    from infra.audio_backend import VlcAudioBackend

    playlist = SpotifySource().fetch_playlist(parse_link(SPOTIFY_URL).source_id)
    matcher = MatchService(YtMusicSource(), config.MATCH_SEARCH_LIMIT, config.MATCH_MIN_SCORE)
    video_id = matcher.find_video(playlist.tracks[0])
    info = YtDlpStreamResolver(str(tmp_path)).resolve(video_id)
    audio = VlcAudioBackend(config.NETWORK_CACHING_MS)
    audio.set_volume(0)
    times = []
    audio.time_changed.connect(lambda elapsed, total: times.append(elapsed))
    audio.play_url(info.url)
    end = time.time() + 20
    while time.time() < end and (not times or max(times) < 2):
        qapp.processEvents()
        time.sleep(0.05)
    audio.stop()
    assert times and max(times) >= 2
