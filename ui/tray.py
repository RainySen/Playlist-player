from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from ui import theme


# bandeja sistema iconos
class TrayController(QObject):
    show_requested = Signal()
    toggle_requested = Signal()
    next_requested = Signal()
    previous_requested = Signal()
    quit_requested = Signal()

    def __init__(self, icon: QIcon, title: str):
        super().__init__()
        self._title = title
        self._tray = QSystemTrayIcon(icon)
        self._tray.setToolTip(title)
        self._menu = QMenu()
        self._menu.setStyleSheet(theme.menu_qss())
        self._menu.addAction("Abrir", self.show_requested)
        self._menu.addSeparator()
        self._toggle = self._menu.addAction("Reproducir", self.toggle_requested)
        self._menu.addAction("Anterior", self.previous_requested)
        self._menu.addAction("Siguiente", self.next_requested)
        self._menu.addSeparator()
        self._menu.addAction("Salir", self.quit_requested)
        self._tray.setContextMenu(self._menu)
        self._tray.activated.connect(self._on_activated)

    @staticmethod
    def available() -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()

    def show(self) -> None:
        if self.available():
            self._tray.show()

    def hide(self) -> None:
        self._tray.hide()

    def set_playing(self, playing: bool) -> None:
        self._toggle.setText("Pausar" if playing else "Reproducir")

    def set_track(self, text: str) -> None:
        self._tray.setToolTip(f"{text}\n{self._title}" if text else self._title)

    def notify(self, message: str) -> None:
        if self._tray.isVisible():
            self._tray.showMessage(self._title, message, QSystemTrayIcon.Information, 4000)

    def _on_activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.show_requested.emit()
