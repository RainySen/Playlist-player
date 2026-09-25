from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from domain.settings import Settings
from ui import theme
from ui.components.dialogs import Modal
from ui.components.switch import Switch


def _option(title: str, hint: str, checked: bool, enabled: bool = True) -> tuple[QWidget, Switch]:
    holder = QWidget()
    layout = QVBoxLayout(holder)
    layout.setContentsMargins(0, 4, 0, 4)
    layout.setSpacing(4)
    row = QHBoxLayout()
    label = QLabel(title)
    label.setStyleSheet(f"color: {theme.TEXT if enabled else theme.TEXT_MUTED}; font-size: 15px; font-weight: 600; "
                        f"background: transparent;")
    switch = Switch(checked)
    switch.setEnabled(enabled)
    row.addWidget(label, 1)
    row.addWidget(switch)
    note = QLabel(hint)
    note.setWordWrap(True)
    note.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 13px; background: transparent;")
    layout.addLayout(row)
    layout.addWidget(note)
    return holder, switch


# configuracion ajustes modal
class SettingsDialog(Modal):
    def __init__(self, parent, settings: Settings, tray_available: bool, on_change):
        super().__init__(parent, "Configuración", width=480)
        hint = "Al cerrar la ventana la música sigue sonando y la app queda en la bandeja del sistema."
        if not tray_available:
            hint = "No disponible: este sistema no tiene bandeja del sistema."
        holder, self.background = _option("Seguir en segundo plano", hint, settings.background_playback and tray_available,
                                          tray_available)
        self.body.addWidget(holder)
        holder, self.mini = _option("Mini reproductor",
                                    "Muestra una ventana pequeña con los controles cuando minimizas la app o la cierras "
                                    "a la bandeja. Puedes moverla y recuerda su posición.", settings.mini_player)
        self.body.addWidget(holder)
        self.background.toggled.connect(lambda value: on_change(background_playback=value))
        self.mini.toggled.connect(lambda value: on_change(mini_player=value))
        self.add_button("Listo", "primary", self.accept, default=True)
