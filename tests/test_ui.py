from PySide6.QtGui import QIcon

from domain.models import Track
from presenters.library_presenter import LibraryPresenter
from presenters.player_presenter import PlayerPresenter
from tests.conftest import make_playlist, wait_until
from ui.components.playlist_sidebar import PlaylistSidebar
from ui.main_window import MainWindow


class UiRig:
    def __init__(self, r):
        self.r = r
        self.window = MainWindow("Test", QIcon())
        self.presenters = [PlayerPresenter(self.window, r.player, r.library), LibraryPresenter(self.window, r.library)]

    def dispose(self):
        self.window.close()
        self.window.deleteLater()
        self.r.app.processEvents()


def test_empty_library_shows_hint(rig):
    ui = UiRig(rig())
    try:
        assert ui.window.table.rowCount() == 0
        assert not ui.window.sidebar._empty.isHidden()
    finally:
        ui.dispose()


def test_existing_playlists_are_listed_and_first_selected(rig):
    r = rig()
    r.repo.put(make_playlist(source_id="PLaaaaaaaaaa1", title="Primera"))
    ui = UiRig(r)
    try:
        assert ui.window.sidebar._list.count() == 1
        assert ui.window.table.rowCount() == 3
        assert ui.window.shown_key == "ytmusic:PLaaaaaaaaaa1"
    finally:
        ui.dispose()


def test_import_flow_updates_sidebar_and_table(rig):
    playlist = make_playlist(source_id="PLabcdefghij123", title="Importada")
    r = rig(playlist=playlist)
    ui = UiRig(r)
    try:
        ui.window.sidebar._input.setText("https://music.youtube.com/playlist?list=PLabcdefghij123")
        ui.window.sidebar._submit()
        assert wait_until(r.app, lambda: ui.window.table.rowCount() == 3)
        assert ui.window.sidebar._list.count() == 1
        assert ui.window.sidebar._input.text() == ""
    finally:
        ui.dispose()


def test_bad_link_shows_notice(rig):
    ui = UiRig(rig())
    try:
        ui.window.sidebar._input.setText("hola")
        ui.window.sidebar._submit()
        assert "enlace" in ui.window.sidebar._notice.text().lower()
        assert ui.window.sidebar._button.isEnabled()
    finally:
        ui.dispose()


def test_single_click_row_plays_and_highlights(rig):
    r = rig()
    r.repo.put(make_playlist(source_id="PLaaaaaaaaaa1"))
    ui = UiRig(r)
    try:
        ui.window.table.cellClicked.emit(2, 1)
        assert wait_until(r.app, lambda: r.audio.urls)
        assert r.audio.urls[0] == "http://stream/v3"
        assert ui.window.player._title.text() == "Tres"
        assert ui.window.table._current == 2
    finally:
        ui.dispose()


def test_play_all_button_starts_from_first_track(rig):
    r = rig()
    r.repo.put(make_playlist(source_id="PLaaaaaaaaaa1"))
    ui = UiRig(r)
    try:
        ui.window._play_all.click()
        assert wait_until(r.app, lambda: r.audio.urls)
        assert r.audio.urls[0] == "http://stream/v1"
    finally:
        ui.dispose()


def test_player_bar_reflects_state(rig):
    r = rig()
    r.repo.put(make_playlist(source_id="PLaaaaaaaaaa1", tracks=[Track("Uno", "Artista", 60, "v1", "v1")]))
    ui = UiRig(r)
    try:
        ui.window.table.cellClicked.emit(0, 0)
        assert wait_until(r.app, lambda: r.audio.urls)
        r.audio.position_changed.emit(0.5)
        r.audio.time_changed.emit(30, 60)
        assert ui.window.player._seek.value() == 500
        assert ui.window.player._time.text() == "0:30 / 1:00"
        ui.window.player._toggle.click()
        assert not r.audio.is_playing
    finally:
        ui.dispose()


def _first_row_widget(ui):
    sidebar = ui.window.sidebar
    return sidebar._list.itemWidget(sidebar._list.item(0))


def test_kebab_menu_deletes_after_confirmation(rig, monkeypatch):
    r = rig()
    r.repo.put(make_playlist(source_id="PLaaaaaaaaaa1", title="Borrame"))
    ui = UiRig(r)
    try:
        monkeypatch.setattr(PlaylistSidebar, "_run_menu", staticmethod(lambda menu, pos: menu.actions()[0]))
        asked = []
        monkeypatch.setattr("ui.main_window.dialogs.confirm", lambda *a, **k: asked.append(a) or True)
        _first_row_widget(ui).button.click()
        assert asked and "Borrame" in asked[0][2]
        assert r.library.get("ytmusic:PLaaaaaaaaaa1") is None
        assert ui.window.table.rowCount() == 0
    finally:
        ui.dispose()


def test_kebab_menu_keeps_playlist_when_cancelled(rig, monkeypatch):
    r = rig()
    r.repo.put(make_playlist(source_id="PLaaaaaaaaaa1"))
    ui = UiRig(r)
    try:
        monkeypatch.setattr(PlaylistSidebar, "_run_menu", staticmethod(lambda menu, pos: menu.actions()[0]))
        monkeypatch.setattr("ui.main_window.dialogs.confirm", lambda *a, **k: False)
        _first_row_widget(ui).button.click()
        assert r.library.get("ytmusic:PLaaaaaaaaaa1") is not None
    finally:
        ui.dispose()


def test_menu_dismissed_without_choice_does_nothing(rig, monkeypatch):
    r = rig()
    r.repo.put(make_playlist(source_id="PLaaaaaaaaaa1"))
    ui = UiRig(r)
    try:
        monkeypatch.setattr(PlaylistSidebar, "_run_menu", staticmethod(lambda menu, pos: None))
        _first_row_widget(ui).button.click()
        assert r.library.get("ytmusic:PLaaaaaaaaaa1") is not None
    finally:
        ui.dispose()


def test_confirm_dialog_has_themed_buttons(rig):
    from PySide6.QtWidgets import QPushButton

    from ui.components.dialogs import ConfirmDialog

    ui = UiRig(rig())
    try:
        dialog = ConfirmDialog(ui.window, "¿Eliminar playlist?", "Mensaje", ok="Eliminar", cancel="Cancelar")
        labels = [b.text() for b in dialog.findChildren(QPushButton)]
        assert labels == ["Cancelar", "Eliminar"]
        dialog.deleteLater()
    finally:
        ui.dispose()


def test_shuffle_button_starts_shuffled_playback_and_lights_up(rig):
    r = rig()
    r.repo.put(make_playlist(source_id="PLaaaaaaaaaa1"))
    ui = UiRig(r)
    try:
        ui.window._shuffle.click()
        assert wait_until(r.app, lambda: r.audio.urls)
        assert r.player.shuffle
        assert "background: #ffffff" in ui.window._shuffle.styleSheet()
        ui.window._play_all.click()
        assert not r.player.shuffle
        assert "background: #ffffff" not in ui.window._shuffle.styleSheet()
    finally:
        ui.dispose()


def test_repeat_button_toggles_service_and_stays_in_sync(rig):
    r = rig()
    ui = UiRig(r)
    try:
        ui.window.player._repeat.click()
        assert r.player.repeat and ui.window.player._repeat.isChecked()
        r.player.set_repeat(False)
        assert not ui.window.player._repeat.isChecked()
    finally:
        ui.dispose()
