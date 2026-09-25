import pytest

from domain.links import LinkError, parse_link
from domain.models import SOURCE_SPOTIFY, SOURCE_YTMUSIC

SPOTIFY_ID = "37i9dQZF1DXcBWIGoYBM5M"


@pytest.mark.parametrize("text", [
    f"https://open.spotify.com/playlist/{SPOTIFY_ID}",
    f"https://open.spotify.com/playlist/{SPOTIFY_ID}?si=abc123",
    f"https://open.spotify.com/intl-es/playlist/{SPOTIFY_ID}?si=abc123",
    f"open.spotify.com/playlist/{SPOTIFY_ID}",
    f"spotify:playlist:{SPOTIFY_ID}",
    f"  <https://open.spotify.com/playlist/{SPOTIFY_ID}>  ",
])
def test_spotify_links(text):
    ref = parse_link(text)
    assert (ref.source, ref.source_id, ref.needs_redirect) == (SOURCE_SPOTIFY, SPOTIFY_ID, False)


@pytest.mark.parametrize("text,expected", [
    ("https://music.youtube.com/playlist?list=PLabcdefghij123", "PLabcdefghij123"),
    ("https://www.youtube.com/playlist?list=PLabcdefghij123&si=xyz", "PLabcdefghij123"),
    ("https://www.youtube.com/watch?v=abcdefghijk&list=RDCLAK5uy_kabc123456", "RDCLAK5uy_kabc123456"),
    ("https://music.youtube.com/browse/VLOLAK5uy_abcdefghij", "OLAK5uy_abcdefghij"),
    ("https://music.youtube.com/playlist?list=VLPLabcdefghij123", "PLabcdefghij123"),
])
def test_youtube_links(text, expected):
    ref = parse_link(text)
    assert (ref.source, ref.source_id) == (SOURCE_YTMUSIC, expected)


def test_short_spotify_link_needs_redirect():
    ref = parse_link("https://spotify.link/AbCdEf123")
    assert ref.needs_redirect and ref.raw == "https://spotify.link/AbCdEf123"


@pytest.mark.parametrize("text", [
    "",
    "   ",
    "hola mundo",
    "https://example.com/playlist/abc",
    "https://www.youtube.com/watch?v=abcdefghijk",
    "https://open.spotify.com/album/" + SPOTIFY_ID,
    "https://open.spotify.com/track/" + SPOTIFY_ID,
    "https://open.spotify.com/playlist/corto",
])
def test_invalid_links(text):
    with pytest.raises(LinkError):
        parse_link(text)
