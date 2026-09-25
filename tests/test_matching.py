from domain.matching import Candidate, best_match, normalize, score
from domain.models import Track

TRACK = Track("Bass Persuades", "Miley Cyrus", 202)


def test_normalize_drops_brackets_accents_and_suffixes():
    assert normalize("Canción (feat. Otro) - Remastered 2011") == "cancion"
    assert normalize("  Hello,   World!! ") == "hello world"


def test_exact_match_scores_high():
    exact = Candidate("a", "Bass Persuades", "Miley Cyrus", 203)
    assert score(TRACK, exact) > 0.95


def test_picks_original_over_live_cover():
    good = Candidate("good", "Bass Persuades", "Miley Cyrus", 202)
    cover = Candidate("cover", "Bass Persuades (Piano Cover)", "Some Kid", 260)
    other = Candidate("other", "Completely Different", "Miley Cyrus", 202)
    assert best_match(TRACK, [cover, other, good], 0.45).video_id == "good"


def test_multiple_artists_still_match():
    track = Track("Song", "Artist One, Artist Two", 180)
    candidate = Candidate("x", "Song", "Artist Two & Artist One", 181)
    assert best_match(track, [candidate], 0.45) is not None


def test_below_minimum_returns_none():
    wrong = Candidate("w", "Otra cosa totalmente", "Nadie", 30)
    assert best_match(TRACK, [wrong], 0.45) is None


def test_no_candidates():
    assert best_match(TRACK, [], 0.45) is None


def test_missing_durations_do_not_break_scoring():
    track = Track("Song", "Artist", 0)
    assert best_match(track, [Candidate("x", "Song", "Artist", 0)], 0.45).video_id == "x"
