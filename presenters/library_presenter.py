from __future__ import annotations

from services.library_service import OUTCOME_UNCHANGED, OUTCOME_UPDATED, LibraryService
from ui.main_window import MainWindow


# biblioteca vista enlaces
class LibraryPresenter:
    def __init__(self, window: MainWindow, library: LibraryService):
        self._window = window
        self._library = library
        sidebar = window.sidebar

        sidebar.import_requested.connect(library.import_link)
        sidebar.playlist_selected.connect(self._show)
        sidebar.delete_requested.connect(self._delete)
        library.changed.connect(self.refresh)
        library.import_started.connect(lambda: sidebar.set_busy(True))
        library.import_finished.connect(self._on_imported)
        library.import_outcome.connect(self._on_outcome)
        library.import_failed.connect(self._on_failed)
        self.refresh()

    def refresh(self) -> None:
        playlists = self._library.playlists()
        self._window.sidebar.set_playlists(playlists, select_key=self._window.shown_key)
        if self._window.shown_key and self._library.get(self._window.shown_key) is None:
            self._window.show_playlist(None)
        elif not self._window.shown_key and playlists:
            self._show(playlists[0].key)
            self._window.sidebar.set_playlists(playlists, select_key=playlists[0].key)

    def _show(self, key: str) -> None:
        self._window.show_playlist(self._library.get(key))

    def _delete(self, key: str) -> None:
        playlist = self._library.get(key)
        if playlist is not None and self._window.confirm_delete(playlist.title):
            self._library.remove(key)

    def _on_imported(self, key: str) -> None:
        sidebar = self._window.sidebar
        sidebar.set_busy(False)
        sidebar.clear_input()
        sidebar.set_playlists(self._library.playlists(), select_key=key)
        self._show(key)

    def _on_outcome(self, outcome: str, added: int) -> None:
        if outcome == OUTCOME_UNCHANGED:
            message = "La playlist ya existe, no hay canciones nuevas."
        elif outcome == OUTCOME_UPDATED:
            message = f"Playlist actualizada: {added} canción nueva." if added == 1 \
                else f"Playlist actualizada: {added} canciones nuevas."
        else:
            message = "Playlist importada."
        self._window.sidebar.show_notice(message, error=False)

    def _on_failed(self, message: str) -> None:
        self._window.sidebar.set_busy(False)
        self._window.sidebar.show_notice(message, error=True)
