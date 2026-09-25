from domain.models import SOURCE_SPOTIFY, Track
from infra.library_repository import LibraryRepository
from infra.ytmusic_source import ImportFailed
from tests.conftest import FakeSource, make_playlist, wait_until


def test_repository_roundtrip_and_remove(tmp_path):
    path = str(tmp_path / "lib.json")
    repo = LibraryRepository(path)
    playlist = make_playlist()
    repo.put(playlist)
    reloaded = LibraryRepository(path)
    assert reloaded.get(playlist.key) == playlist
    assert reloaded.remove(playlist.key) is True
    assert reloaded.remove(playlist.key) is False
    assert LibraryRepository(path).all() == []


def test_repository_ignores_corrupt_file(tmp_path):
    path = tmp_path / "lib.json"
    path.write_text("{no es json", encoding="utf-8")
    assert LibraryRepository(str(path)).all() == []


def test_import_ytmusic_link(rig):
    r = rig(playlist=make_playlist(source_id="PLabcdefghij123"))
    done, changed = [], []
    r.library.import_finished.connect(done.append)
    r.library.changed.connect(lambda: changed.append(1))
    r.library.import_link("https://music.youtube.com/playlist?list=PLabcdefghij123")
    assert wait_until(r.app, lambda: done)
    assert r.ytmusic.fetched == ["PLabcdefghij123"]
    assert done == ["ytmusic:PLabcdefghij123"] and changed
    assert r.library.get(done[0]).title == "Mix"


def test_import_spotify_link_uses_spotify_source(rig):
    playlist = make_playlist(source=SOURCE_SPOTIFY, source_id="37i9dQZF1DXcBWIGoYBM5M", tracks=[Track("Uno", "A")])
    r = rig(playlist=playlist)
    done = []
    r.library.import_finished.connect(done.append)
    r.library.import_link("https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M?si=1")
    assert wait_until(r.app, lambda: done)
    assert r.spotify.fetched == ["37i9dQZF1DXcBWIGoYBM5M"] and r.ytmusic.fetched == []


def test_short_spotify_link_is_resolved_first(rig):
    playlist = make_playlist(source=SOURCE_SPOTIFY, source_id="37i9dQZF1DXcBWIGoYBM5M", tracks=[Track("Uno", "A")])
    r = rig(playlist=playlist)
    r.spotify.redirect = "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
    done = []
    r.library.import_finished.connect(done.append)
    r.library.import_link("https://spotify.link/AbCdEf123")
    assert wait_until(r.app, lambda: done)
    assert r.spotify.fetched == ["37i9dQZF1DXcBWIGoYBM5M"]


def test_invalid_link_fails_without_starting(rig):
    r = rig()
    started, failed = [], []
    r.library.import_started.connect(lambda: started.append(1))
    r.library.import_failed.connect(failed.append)
    r.library.import_link("hola")
    assert failed and not started


def test_source_error_message_reaches_ui(rig):
    r = rig(source=FakeSource(error=ImportFailed("La playlist está vacía o es privada.")))
    failed = []
    r.library.import_failed.connect(failed.append)
    r.library.import_link("https://music.youtube.com/playlist?list=PLabcdefghij123")
    assert wait_until(r.app, lambda: failed)
    assert failed == ["La playlist está vacía o es privada."]


def test_unexpected_error_gets_generic_message(rig):
    r = rig(source=FakeSource(error=RuntimeError("boom")))
    failed = []
    r.library.import_failed.connect(failed.append)
    r.library.import_link("https://music.youtube.com/playlist?list=PLabcdefghij123")
    assert wait_until(r.app, lambda: failed)
    assert "boom" not in failed[0]


def test_reimport_keeps_resolved_videos(rig):
    tracks = [Track("Uno", "A", 100, source_id="s1"), Track("Dos", "B", 100, source_id="s2")]
    fresh = make_playlist(source=SOURCE_SPOTIFY, source_id="37i9dQZF1DXcBWIGoYBM5M", tracks=tracks)
    r = rig(playlist=fresh)
    r.repo.put(fresh.with_track_video(0, "found1"))
    done = []
    r.library.import_finished.connect(done.append)
    r.library.import_link("https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M")
    assert wait_until(r.app, lambda: done)
    stored = r.library.get(fresh.key)
    assert [t.video_id for t in stored.tracks] == ["found1", ""]


def test_reimport_without_new_tracks_reports_unchanged(rig):
    playlist = make_playlist(source_id="PLabcdefghij123", tracks=[Track("Uno", "A", source_id="s1")])
    r = rig(playlist=playlist)
    r.repo.put(playlist)
    outcomes, changed = [], []
    r.library.import_outcome.connect(lambda kind, added: outcomes.append((kind, added)))
    r.library.changed.connect(lambda: changed.append(1))
    r.library.import_link(f"https://music.youtube.com/playlist?list={playlist.source_id}")
    assert wait_until(r.app, lambda: outcomes)
    assert outcomes == [("unchanged", 0)] and not changed


def test_reimport_with_new_tracks_updates_playlist(rig):
    old = make_playlist(source_id="PLabcdefghij123", tracks=[Track("Uno", "A", source_id="s1", video_id="v1")])
    fresh = old.with_tracks([Track("Uno", "A", source_id="s1"), Track("Dos", "B", source_id="s2")])
    r = rig(playlist=fresh)
    r.repo.put(old)
    outcomes = []
    r.library.import_outcome.connect(lambda kind, added: outcomes.append((kind, added)))
    r.library.import_link(f"https://music.youtube.com/playlist?list={fresh.source_id}")
    assert wait_until(r.app, lambda: outcomes)
    assert outcomes == [("updated", 1)]
    assert [t.source_id for t in r.library.get(fresh.key).tracks] == ["s1", "s2"]
    assert r.library.get(fresh.key).tracks[0].video_id == "v1"


def test_first_import_reports_created(rig):
    playlist = make_playlist(source_id="PLabcdefghij123")
    r = rig(playlist=playlist)
    outcomes = []
    r.library.import_outcome.connect(lambda kind, added: outcomes.append(kind))
    r.library.import_link(f"https://music.youtube.com/playlist?list={playlist.source_id}")
    assert wait_until(r.app, lambda: outcomes)
    assert outcomes == ["created"]


def test_remove_emits_changed(rig):
    playlist = make_playlist()
    r = rig(playlist=playlist)
    r.repo.put(playlist)
    changed = []
    r.library.changed.connect(lambda: changed.append(1))
    r.library.remove(playlist.key)
    assert changed and r.library.get(playlist.key) is None


def test_set_track_video_persists(rig):
    playlist = make_playlist(tracks=[Track("Uno", "A")])
    r = rig(playlist=playlist)
    r.repo.put(playlist)
    r.library.set_track_video(playlist.key, 0, "vid")
    r.library.set_track_video(playlist.key, 9, "ignorado")
    assert LibraryRepository(r.repo._path).get(playlist.key).tracks[0].video_id == "vid"
