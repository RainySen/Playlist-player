import pytest

from domain.settings import Settings
from infra.settings_repository import SettingsRepository
from services.settings_service import SettingsService


def test_defaults_enable_background_features():
    settings = Settings()
    assert settings.background_playback and settings.mini_player
    assert settings.mini_x is None and settings.mini_y is None


@pytest.mark.parametrize("raw", [None, [], "texto", 5, {"background_playback": "no", "mini_x": "10", "mini_y": True}])
def test_from_dict_falls_back_to_defaults_on_garbage(raw):
    assert Settings.from_dict(raw) == Settings()


def test_from_dict_reads_valid_values():
    settings = Settings.from_dict({"background_playback": False, "mini_player": False, "mini_x": 40, "mini_y": -5})
    assert settings == Settings(False, False, 40, -5)


def test_with_changes_rejects_unknown_setting():
    with pytest.raises(KeyError):
        Settings().with_changes(tema="claro")


def test_repository_roundtrip_and_missing_file(tmp_path):
    repo = SettingsRepository(str(tmp_path / "settings.json"))
    assert repo.load() == Settings()
    repo.save(Settings(False, True, 1, 2))
    assert SettingsRepository(str(tmp_path / "settings.json")).load() == Settings(False, True, 1, 2)


def test_repository_ignores_corrupt_file(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{roto", encoding="utf-8")
    assert SettingsRepository(str(path)).load() == Settings()


def test_service_persists_and_emits_only_on_real_change(qapp, tmp_path):
    repo = SettingsRepository(str(tmp_path / "settings.json"))
    service = SettingsService(repo)
    seen = []
    service.changed.connect(seen.append)
    service.update(mini_player=False)
    service.update(mini_player=False)
    assert len(seen) == 1 and seen[0].mini_player is False
    assert repo.load().mini_player is False
    assert SettingsService(repo).settings.mini_player is False
