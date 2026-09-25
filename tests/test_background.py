from PySide6.QtGui import QIcon

from infra.settings_repository import SettingsRepository
from presenters.background_presenter import BackgroundPresenter
from presenters.library_presenter import LibraryPresenter
from presenters.player_presenter import PlayerPresenter
from services.settings_service import SettingsService
from tests.conftest import make_playlist, wait_until
from ui.components.mini_player import MiniPlayer
from ui.main_window import MainWindow
from ui.settings_dialog import SettingsDialog
from ui.tray import TrayController


class BackgroundRig:
    def __init__(self, r, tmp_path, monkeypatch, tray_available=True):
        monkeypatch.setattr(TrayController, "available", staticmethod(lambda: tray_available))
        self.r = r
        self.settings = SettingsService(SettingsRepository(str(tmp_path / "settings.json")))
        self.window = MainWindow("Test", QIcon())
        self.tray = TrayController(QIcon(), "Test")
        self.mini = MiniPlayer()
        self.presenters = [
            PlayerPresenter(self.window, r.player, r.library),
            LibraryPresenter(self.window, r.library),
            BackgroundPresenter(self.window, self.tray, self.mini, r.player, self.settings),
        ]
        self.closed = []
        self.window.closed.connect(lambda: self.closed.append(1))

    def play_first(self):
        self.r.repo.put(make_playlist(source_id="PLaaaaaaaaaa1"))
        self.r.library.changed.emit()
        self.r.player.play_playlist("ytmusic:PLaaaaaaaaaa1", 0)
        assert wait_until(self.r.app, lambda: self.r.audio.urls)

    def dispose(self):
        self.mini.hide()
        self.mini.deleteLater()
        self.window._quitting = True
        self.window.close()
        self.window.deleteLater()
        self.r.app.processEvents()


def make(rig, tmp_path, monkeypatch, **kwargs):
    return BackgroundRig(rig(), tmp_path, monkeypatch, **kwargs)


def test_closing_hides_to_tray_and_keeps_playing(rig, tmp_path, monkeypatch):
    b = make(rig, tmp_path, monkeypatch)
    try:
        b.window.show()
        b.play_first()
        b.window.close()
        assert not b.window.isVisible() and not b.closed
        assert b.r.audio.is_playing
        b.window.quit_app()
        assert b.closed == [1]
    finally:
        b.dispose()


def test_closing_quits_when_background_playback_disabled(rig, tmp_path, monkeypatch):
    b = make(rig, tmp_path, monkeypatch)
    try:
        b.settings.update(background_playback=False)
        b.window.show()
        b.window.close()
        assert b.closed == [1]
    finally:
        b.dispose()


def test_closing_quits_when_system_has_no_tray(rig, tmp_path, monkeypatch):
    b = make(rig, tmp_path, monkeypatch, tray_available=False)
    try:
        b.window.show()
        b.window.close()
        assert b.closed == [1]
    finally:
        b.dispose()


def test_mini_player_appears_when_window_is_hidden_and_a_track_is_loaded(rig, tmp_path, monkeypatch):
    b = make(rig, tmp_path, monkeypatch)
    try:
        b.window.show()
        b.play_first()
        assert not b.mini.isVisible()
        b.window.close()
        assert b.mini.isVisible()
        assert b.mini._title.text() == "Uno"
        b.window.restore()
        assert not b.mini.isVisible()
    finally:
        b.dispose()


def test_mini_player_needs_a_track(rig, tmp_path, monkeypatch):
    b = make(rig, tmp_path, monkeypatch)
    try:
        b.window.show()
        b.window.close()
        assert not b.mini.isVisible()
    finally:
        b.dispose()


def test_mini_player_can_be_disabled_live(rig, tmp_path, monkeypatch):
    b = make(rig, tmp_path, monkeypatch)
    try:
        b.window.show()
        b.play_first()
        b.window.close()
        assert b.mini.isVisible()
        b.settings.update(mini_player=False)
        assert not b.mini.isVisible()
        b.settings.update(mini_player=True)
        assert b.mini.isVisible()
    finally:
        b.dispose()


def test_mini_player_controls_drive_the_player(rig, tmp_path, monkeypatch):
    b = make(rig, tmp_path, monkeypatch)
    try:
        b.window.show()
        b.play_first()
        b.window.close()
        b.mini._toggle.click()
        assert not b.r.audio.is_playing
        b.mini._toggle.click()
        assert b.r.audio.is_playing
        b.mini._next.click()
        assert wait_until(b.r.app, lambda: b.r.audio.urls[-1] == "http://stream/v2")
        assert b.mini._title.text() == "Dos"
        b.r.audio.position_changed.emit(0.5)
        assert b.mini._progress.value() == 500
    finally:
        b.dispose()


def test_mini_expand_button_restores_main_window(rig, tmp_path, monkeypatch):
    b = make(rig, tmp_path, monkeypatch)
    try:
        b.window.show()
        b.play_first()
        b.window.close()
        b.mini._expand.click()
        assert b.window.isVisible() and not b.mini.isVisible()
    finally:
        b.dispose()


def test_mini_position_is_saved_and_reused(rig, tmp_path, monkeypatch):
    b = make(rig, tmp_path, monkeypatch)
    try:
        b.mini.moved.emit(120, 240)
        assert (b.settings.settings.mini_x, b.settings.settings.mini_y) == (120, 240)
        b.window.show()
        b.play_first()
        b.window.close()
        assert (b.mini.x(), b.mini.y()) == (120, 240)
    finally:
        b.dispose()


def test_tray_actions_control_playback_and_quit(rig, tmp_path, monkeypatch):
    b = make(rig, tmp_path, monkeypatch)
    try:
        b.window.show()
        b.play_first()
        b.tray.toggle_requested.emit()
        assert not b.r.audio.is_playing
        b.window.close()
        b.tray.show_requested.emit()
        assert b.window.isVisible()
        b.tray.quit_requested.emit()
        assert b.closed == [1]
    finally:
        b.dispose()


def test_tray_menu_labels_follow_state(rig, tmp_path, monkeypatch):
    b = make(rig, tmp_path, monkeypatch)
    try:
        b.window.show()
        b.play_first()
        assert b.tray._toggle.text() == "Pausar"
        b.r.player.toggle_pause()
        assert b.tray._toggle.text() == "Reproducir"
    finally:
        b.dispose()


def test_settings_button_opens_dialog_with_current_values(rig, tmp_path, monkeypatch):
    b = make(rig, tmp_path, monkeypatch)
    try:
        opened = []
        monkeypatch.setattr(SettingsDialog, "exec", lambda self: opened.append((self.background.isChecked(), self.mini.isChecked())))
        b.settings.update(mini_player=False)
        b.window.sidebar.settings_requested.emit()
        assert opened == [(True, False)]
    finally:
        b.dispose()


def test_dialog_toggles_apply_immediately(rig, tmp_path, monkeypatch):
    b = make(rig, tmp_path, monkeypatch)
    try:
        changes = []
        dialog = SettingsDialog(b.window, b.settings.settings, True, lambda **kw: changes.append(kw))
        dialog.mini.setChecked(False)
        dialog.background.setChecked(False)
        assert changes == [{"mini_player": False}, {"background_playback": False}]
        dialog.deleteLater()
    finally:
        b.dispose()


def test_dialog_disables_background_option_without_tray(rig, tmp_path, monkeypatch):
    b = make(rig, tmp_path, monkeypatch, tray_available=False)
    try:
        dialog = SettingsDialog(b.window, b.settings.settings, False, lambda **kw: None)
        assert not dialog.background.isEnabled() and not dialog.background.isChecked()
        assert dialog.mini.isEnabled()
        dialog.deleteLater()
    finally:
        b.dispose()


def test_minimizing_shows_mini_player(rig, tmp_path, monkeypatch):
    b = make(rig, tmp_path, monkeypatch)
    try:
        b.window.show()
        b.play_first()
        b.window.showMinimized()
        b.r.app.processEvents()
        assert b.window.isMinimized() and b.mini.isVisible()
        b.window.restore()
        assert not b.mini.isVisible()
    finally:
        b.dispose()
