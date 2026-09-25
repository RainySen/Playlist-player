import json

import pytest

from infra.spotify_source import playlist_from_embed
from infra.ytmusic_source import ImportFailed, YtMusicSource, candidate_from_result, playlist_from_ytmusic


def embed_html(entity):
    data = {"props": {"pageProps": {"state": {"data": {"entity": entity}}}}}
    return f'<html><script id="__NEXT_DATA__" type="application/json">{json.dumps(data)}</script></html>'


def test_spotify_embed_parsing():
    html = embed_html({
        "name": "Mi Mix", "subtitle": "Rainy",
        "trackList": [
            {"uri": "spotify:track:AAA", "title": "Uno", "subtitle": "Artista A, Artista B", "duration": 200500,
             "entityType": "track"},
            {"uri": "spotify:track:BBB", "title": "Dos", "subtitle": "Artista\xa0C", "duration": 0, "entityType": "track"},
            {"uri": "spotify:episode:CCC", "title": "Podcast", "subtitle": "X", "entityType": "episode"},
            {"uri": "spotify:track:DDD", "title": "  ", "subtitle": "Nadie"},
        ],
    })
    playlist = playlist_from_embed("PLID", html)
    assert playlist.title == "Mi Mix" and playlist.author == "Rainy"
    assert playlist.url == "https://open.spotify.com/playlist/PLID"
    assert [t.title for t in playlist.tracks] == ["Uno", "Dos"]
    assert playlist.tracks[0].artist == "Artista A, Artista B"
    assert playlist.tracks[0].duration_s == 200
    assert playlist.tracks[0].source_id == "AAA" and playlist.tracks[0].video_id == ""
    assert playlist.tracks[1].artist == "Artista C"


def test_spotify_page_without_data_fails_cleanly():
    with pytest.raises(ImportFailed):
        playlist_from_embed("X", "<html>nada</html>")


def test_spotify_empty_playlist_fails():
    with pytest.raises(ImportFailed):
        playlist_from_embed("X", embed_html({"name": "Vacía", "trackList": []}))


def test_ytmusic_playlist_conversion_skips_unavailable():
    data = {
        "title": "Rock", "author": {"name": "Canal"},
        "tracks": [
            {"videoId": "v1", "title": "Uno", "artists": [{"name": "A"}, {"name": "B"}], "duration_seconds": 180,
             "isAvailable": True},
            {"videoId": None, "title": "Sin id", "artists": []},
            {"videoId": "v3", "title": "Borrada", "artists": [], "isAvailable": False},
            {"videoId": "v4", "title": "Cuatro", "artists": None, "duration_seconds": None},
        ],
    }
    playlist = playlist_from_ytmusic("PL9", data)
    assert playlist.key == "ytmusic:PL9" and playlist.author == "Canal"
    assert [t.video_id for t in playlist.tracks] == ["v1", "v4"]
    assert playlist.tracks[0].artist == "A, B" and playlist.tracks[0].duration_s == 180
    assert playlist.tracks[1].artist == "" and playlist.tracks[1].duration_s == 0


def test_ytmusic_empty_playlist_fails():
    with pytest.raises(ImportFailed):
        playlist_from_ytmusic("PL9", {"title": "x", "tracks": []})


class FakeClient:
    def __init__(self, results):
        self.results = results

    def search(self, query):
        return self.results


def test_search_prefers_songs_and_caps_results():
    results = [
        {"resultType": "video", "videoId": "vid", "title": "Video", "artists": []},
        {"resultType": "song", "videoId": "s1", "title": "Uno", "artists": [{"name": "A"}]},
        {"resultType": "playlist", "browseId": "PL", "title": "Lista"},
        {"resultType": "song", "videoId": "s2", "title": "Dos", "artists": [{"name": "A"}]},
        {"resultType": "song", "videoId": "s3", "title": "Tres", "artists": [{"name": "A"}]},
    ]
    found = YtMusicSource(FakeClient(results)).search("x", 2)
    assert [c.video_id for c in found] == ["s1", "s2"]


def test_search_falls_back_to_videos():
    results = [{"resultType": "video", "videoId": "vid", "title": "Video", "artists": [{"name": "A"}]}]
    assert [c.video_id for c in YtMusicSource(FakeClient(results)).search("x", 3)] == ["vid"]


def test_candidate_from_result():
    candidate = candidate_from_result({"videoId": "z", "title": "T", "artists": [{"name": "A"}], "duration_seconds": 10})
    assert (candidate.video_id, candidate.artist, candidate.duration_s) == ("z", "A", 10)
