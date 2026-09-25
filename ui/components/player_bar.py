from __future__ import annotations

import qtawesome as qta
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSlider, QVBoxLayout, QWidget

from domain.models import format_duration
from ui import theme
from ui.components.icon_button import icon_button

SEEK_STEPS = 1000


class ClickSlider(QSlider):
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.maximum() > 0:
            span = max(1, self.width())
            self.setValue(round(self.maximum() * min(max(event.position().x(), 0), span) / span))
            self.sliderReleased.emit()
        super().mousePressEvent(event)


def _slider_qss() -> str:
    return f"""
        QSlider::groove:horizontal {{ height: 4px; background: rgba(255,255,255,0.2); border-radius: 2px; }}
        QSlider::sub-page:horizontal {{ background: {theme.TEXT}; border-radius: 2px; }}
        QSlider::handle:horizontal {{ width: 12px; height: 12px; margin: -4px 0; border-radius: 6px;
                                     background: {theme.TEXT}; }}
    """


# controles reproductor barra
class PlayerBar(QWidget):
    toggle_requested = Signal()
    next_requested = Signal()
    previous_requested = Signal()
    seek_requested = Signal(float)
    volume_changed = Signal(int)
    repeat_toggled = Signal(bool)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(92)
        self.setObjectName("playerBar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"#playerBar {{ background: {theme.SURFACE}; border-top: 1px solid {theme.BORDER}; }} "
                           f"QLabel {{ background: transparent; border: none; }}")

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 8, 20, 8)
        root.setSpacing(4)

        self._seek = ClickSlider(Qt.Horizontal)
        self._seek.setRange(0, SEEK_STEPS)
        self._seek.setStyleSheet(_slider_qss())
        self._seek.sliderReleased.connect(lambda: self.seek_requested.emit(self._seek.value() / SEEK_STEPS))
        root.addWidget(self._seek)

        row = QHBoxLayout()
        row.setSpacing(12)
        root.addLayout(row)

        info = QVBoxLayout()
        info.setSpacing(0)
        self._title = QLabel("Nada en reproducción")
        self._title.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {theme.TEXT};")
        self._artist = QLabel("")
        self._artist.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_SECONDARY};")
        info.addWidget(self._title)
        info.addWidget(self._artist)
        row.addLayout(info, 1)

        self._previous = icon_button("fa5s.step-backward", 36, "Anterior")
        self._toggle = icon_button("fa5s.play", 44, "Reproducir o pausar")
        self._next = icon_button("fa5s.step-forward", 36, "Siguiente")
        self._repeat = icon_button("mdi6.repeat-once", 36, "Repetir canción en bucle", checkable=True)
        self._previous.clicked.connect(self.previous_requested)
        self._toggle.clicked.connect(self.toggle_requested)
        self._next.clicked.connect(self.next_requested)
        self._repeat.toggled.connect(self._on_repeat)
        for button in (self._previous, self._toggle, self._next, self._repeat):
            row.addWidget(button)

        right = QHBoxLayout()
        right.setSpacing(8)
        self._time = QLabel("0:00 / 0:00")
        self._time.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_SECONDARY};")
        right.addStretch(1)
        right.addWidget(self._time)
        volume_icon = QLabel()
        volume_icon.setPixmap(qta.icon("fa5s.volume-up", color=theme.TEXT_SECONDARY).pixmap(16, 16))
        right.addWidget(volume_icon)
        self._volume = QSlider(Qt.Horizontal)
        self._volume.setRange(0, 100)
        self._volume.setValue(100)
        self._volume.setFixedWidth(90)
        self._volume.setStyleSheet(_slider_qss())
        self._volume.valueChanged.connect(self.volume_changed)
        right.addWidget(self._volume)
        row.addLayout(right, 1)

    def _on_repeat(self, active: bool) -> None:
        self._repeat.setIcon(qta.icon("mdi6.repeat-once", color=theme.LINK if active else theme.TEXT))
        self.repeat_toggled.emit(active)

    def set_repeat(self, active: bool) -> None:
        self._repeat.blockSignals(True)
        self._repeat.setChecked(active)
        self._repeat.blockSignals(False)
        self._repeat.setIcon(qta.icon("mdi6.repeat-once", color=theme.LINK if active else theme.TEXT))

    def set_track(self, title: str, artist: str) -> None:
        self._title.setText(title or "Nada en reproducción")
        self._artist.setText(artist)
        self.set_position(0.0)
        self.set_time(0, 0)

    def set_playing(self, playing: bool) -> None:
        self._toggle.setIcon(qta.icon("fa5s.pause" if playing else "fa5s.play", color=theme.TEXT))

    def set_position(self, fraction: float) -> None:
        if not self._seek.isSliderDown():
            self._seek.setValue(round(max(0.0, min(1.0, fraction)) * SEEK_STEPS))

    def set_time(self, elapsed: int, total: int) -> None:
        self._time.setText(f"{format_duration(elapsed)} / {format_duration(total)}")
