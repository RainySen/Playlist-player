from domain.matching import Candidate
from domain.models import SOURCE_SPOTIFY, Track
from tests.conftest import make_playlist, wait_until


def setup_playlist(r, playlist):
    r.repo.put(playlist)
    return playlist.key


def test_plays_selected_track_with_stream_url(rig):
    r = rig()
    key = setup_playlist(r, make_playlist())
    r.player.play_playlist(key, 1)
    assert wait_until(r.app, lambda: r.audio.urls)
    assert r.audio.urls[0] == "http://stream/v2"
    assert r.player.current_index == 1 and r.player.current_track().title == "Dos"


def test_next_previous_and_restart_rule(rig):
    r = rig()
    key = setup_playlist(r, make_playlist())
    r.player.play_playlist(key, 0)
    assert wait_until(r.app, lambda: len(r.audio.urls) == 1)
    r.player.next()
    assert wait_until(r.app, lambda: len(r.audio.urls) == 2)
    assert r.audio.urls[-1] == "http://stream/v2"
    r.audio.time_changed.emit(10, 100)
    r.player.previous()
    assert wait_until(r.app, lambda: len(r.audio.urls) == 3)
    assert r.audio.urls[-1] == "http://stream/v2"
    r.audio.time_changed.emit(1, 100)
    r.player.previous()
    assert wait_until(r.app, lambda: len(r.audio.urls) == 4)
    assert r.audio.urls[-1] == "http://stream/v1"


def test_finished_advances_and_last_track_stops(rig):
    r = rig()
    key = setup_playlist(r, make_playlist(tracks=[Track("Uno", "A", 1, "v1", "v1"), Track("Dos", "B", 1, "v2", "v2")]))
    stopped = []
    r.player.stopped.connect(lambda: stopped.append(1))
    r.player.play_playlist(key, 0)
    assert wait_until(r.app, lambda: len(r.audio.urls) == 1)
    r.audio.finished.emit()
    assert wait_until(r.app, lambda: len(r.audio.urls) == 2)
    r.audio.finished.emit()
    assert wait_until(r.app, lambda: stopped)
    assert not r.audio.is_playing


def test_toggle_pause_and_resume(rig):
    r = rig()
    key = setup_playlist(r, make_playlist())
    states = []
    r.player.state_changed.connect(states.append)
    r.player.play_playlist(key, 0)
    assert wait_until(r.app, lambda: r.audio.urls)
    r.player.toggle_pause()
    assert not r.audio.is_playing and states[-1] is False
    r.player.toggle_pause()
    assert r.audio.is_playing and states[-1] is True


def test_failed_stream_skips_to_next_track(rig):
    r = rig(failing={"v1"})
    key = setup_playlist(r, make_playlist())
    messages = []
    r.player.message.connect(messages.append)
    r.player.play_playlist(key, 0)
    assert wait_until(r.app, lambda: r.audio.urls)
    assert r.audio.urls[0] == "http://stream/v2"
    assert messages and "Uno" in messages[0]


def test_stops_after_consecutive_failures(rig):
    r = rig(failing={"v1", "v2", "v3"})
    key = setup_playlist(r, make_playlist())
    stopped = []
    r.player.stopped.connect(lambda: stopped.append(1))
    r.player.play_playlist(key, 0)
    assert wait_until(r.app, lambda: stopped)
    assert r.audio.urls == []


def test_spotify_track_is_matched_then_played_and_saved(rig):
    tracks = [Track("Bass Persuades", "Miley Cyrus", 202, source_id="s1")]
    playlist = make_playlist(source=SOURCE_SPOTIFY, source_id="37i9dQZF1DXcBWIGoYBM5M", tracks=tracks)
    r = rig(search={"Miley Cyrus Bass Persuades": [
        Candidate("wrong", "Otra canción", "Alguien", 90),
        Candidate("right", "Bass Persuades", "Miley Cyrus", 202),
    ]})
    key = setup_playlist(r, playlist)
    r.player.play_playlist(key, 0)
    assert wait_until(r.app, lambda: r.audio.urls)
    assert r.audio.urls[0] == "http://stream/right"
    assert r.library.get(key).tracks[0].video_id == "right"


def test_spotify_track_without_match_is_skipped(rig):
    tracks = [Track("Inexistente", "Nadie", 100, source_id="s1"), Track("Dos", "B", 100, "v2", "v2")]
    playlist = make_playlist(source=SOURCE_SPOTIFY, source_id="37i9dQZF1DXcBWIGoYBM5M", tracks=tracks)
    r = rig()
    key = setup_playlist(r, playlist)
    messages = []
    r.player.message.connect(messages.append)
    r.player.play_playlist(key, 0)
    assert wait_until(r.app, lambda: r.audio.urls)
    assert r.audio.urls[0] == "http://stream/v2"
    assert "Inexistente" in messages[0]


def test_upcoming_spotify_tracks_are_matched_ahead(rig):
    tracks = [Track("Uno", "A", 100, "v1", "v1"), Track("Dos", "B", 100, source_id="s2")]
    playlist = make_playlist(source=SOURCE_SPOTIFY, source_id="37i9dQZF1DXcBWIGoYBM5M", tracks=tracks)
    r = rig(search={"B Dos": [Candidate("v2", "Dos", "B", 100)]})
    key = setup_playlist(r, playlist)
    r.player.play_playlist(key, 0)
    assert wait_until(r.app, lambda: r.library.get(key).tracks[1].video_id == "v2")
    assert wait_until(r.app, lambda: "v2" in r.resolver.calls)


def test_empty_or_unknown_playlist_is_ignored(rig):
    r = rig()
    r.player.play_playlist("nope:1", 0)
    assert r.audio.urls == [] and r.player.current_track() is None


def test_seek_and_volume_pass_through(rig):
    r = rig()
    r.player.seek(0.5)
    r.player.set_volume(40)
    assert r.audio.sought == 0.5 and r.audio.volume == 40


def five_tracks():
    return [Track(f"T{i}", "A", 100, f"v{i}", f"v{i}") for i in range(5)]


def played_until_stop(r):
    stopped = []
    r.player.stopped.connect(lambda: stopped.append(1))
    seen = []
    for _ in range(12):
        count = len(seen)
        assert wait_until(r.app, lambda: len(r.audio.urls) > count or stopped)
        if stopped:
            break
        seen.append(r.audio.urls[count])
        r.audio.finished.emit()
    return seen


def test_shuffle_plays_every_track_once_starting_from_chosen(rig):
    r = rig()
    key = setup_playlist(r, make_playlist(tracks=five_tracks()))
    flags = []
    r.player.shuffle_changed.connect(flags.append)
    r.player.play_playlist(key, 2, shuffle=True)
    seen = played_until_stop(r)
    assert seen[0] == "http://stream/v2"
    assert sorted(seen) == sorted(f"http://stream/v{i}" for i in range(5))
    assert flags == [True] and r.player.shuffle


def test_shuffle_without_index_starts_anywhere_and_covers_all(rig):
    r = rig()
    key = setup_playlist(r, make_playlist(tracks=five_tracks()))
    r.player.play_playlist(key, None, shuffle=True)
    assert len(set(played_until_stop(r))) == 5


def test_sequential_play_turns_shuffle_off(rig):
    r = rig()
    key = setup_playlist(r, make_playlist(tracks=five_tracks()))
    r.player.play_playlist(key, 0, shuffle=True)
    assert wait_until(r.app, lambda: r.audio.urls)
    r.audio.urls.clear()
    r.player.play_playlist(key, 0, shuffle=False)
    assert not r.player.shuffle
    assert played_until_stop(r) == [f"http://stream/v{i}" for i in range(5)]


def test_previous_follows_shuffled_order(rig):
    r = rig()
    key = setup_playlist(r, make_playlist(tracks=five_tracks()))
    r.player.play_playlist(key, 3, shuffle=True)
    assert wait_until(r.app, lambda: len(r.audio.urls) == 1)
    r.player.next()
    assert wait_until(r.app, lambda: len(r.audio.urls) == 2)
    r.audio.time_changed.emit(1, 100)
    r.player.previous()
    assert wait_until(r.app, lambda: len(r.audio.urls) == 3)
    assert r.audio.urls[2] == r.audio.urls[0] == "http://stream/v3"


def test_turning_shuffle_off_midway_continues_in_order(rig):
    r = rig()
    key = setup_playlist(r, make_playlist(tracks=five_tracks()))
    r.player.play_playlist(key, 1, shuffle=True)
    assert wait_until(r.app, lambda: r.audio.urls)
    r.player.set_shuffle(False)
    r.player.next()
    assert wait_until(r.app, lambda: len(r.audio.urls) == 2)
    assert r.audio.urls[1] == "http://stream/v2"


def test_repeat_replays_same_track_until_disabled(rig):
    r = rig()
    key = setup_playlist(r, make_playlist())
    flags = []
    r.player.repeat_changed.connect(flags.append)
    r.player.set_repeat(True)
    r.player.play_playlist(key, 1)
    assert wait_until(r.app, lambda: len(r.audio.urls) == 1)
    r.audio.finished.emit()
    assert wait_until(r.app, lambda: len(r.audio.urls) == 2)
    r.audio.finished.emit()
    assert wait_until(r.app, lambda: len(r.audio.urls) == 3)
    assert set(r.audio.urls) == {"http://stream/v2"}
    r.player.next()
    assert wait_until(r.app, lambda: len(r.audio.urls) == 4)
    assert r.audio.urls[-1] == "http://stream/v3"
    r.player.set_repeat(False)
    assert flags == [True, False]
    r.audio.finished.emit()
    assert wait_until(r.app, lambda: not r.audio.is_playing)
