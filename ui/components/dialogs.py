import qtawesome as qta
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from ui import theme

_CARD_QSS = f"#modal_card {{ background: {theme.SURFACE}; border: 1px solid {theme.BORDER}; border-radius: 16px; }}"
_CLOSE_QSS = """
    QPushButton { background: transparent; border: none; border-radius: 18px; }
    QPushButton:hover { background: rgba(255,255,255,0.12); }
"""


# modal dialogos
class Modal(QDialog):
    def __init__(self, parent, title, *, width=440, height=None, closable=True):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.setModal(True)
        self.setAttribute(Qt.WA_TranslucentBackground)
        if height:
            self.setFixedSize(width, height)
        else:
            self.setFixedWidth(width)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.card = QFrame()
        self.card.setObjectName("modal_card")
        self.card.setStyleSheet(_CARD_QSS)
        outer.addWidget(self.card)
        root = QVBoxLayout(self.card)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(24, 20, 16 if closable else 24, 8)
        heading = QLabel(title)
        heading.setWordWrap(True)
        heading.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {theme.TEXT};")
        header.addWidget(heading, stretch=1)
        if closable:
            close = QPushButton()
            close.setIcon(qta.icon("fa5s.times", color="white"))
            close.setFixedSize(36, 36)
            close.setCursor(Qt.PointingHandCursor)
            close.setStyleSheet(_CLOSE_QSS)
            close.setToolTip("Cerrar")
            close.clicked.connect(self.reject)
            header.addWidget(close, alignment=Qt.AlignTop)
        root.addLayout(header)

        self._body_holder = QWidget()
        self._body_holder.setStyleSheet("background: transparent;")
        self.body = QVBoxLayout(self._body_holder)
        self.body.setContentsMargins(24, 8, 24, 8)
        self.body.setSpacing(12)
        root.addWidget(self._body_holder, stretch=1)

        self.footer = QHBoxLayout()
        self.footer.setContentsMargins(24, 12, 24, 22)
        self.footer.setSpacing(10)
        self.footer.addStretch()
        root.addLayout(self.footer)

    def add_button(self, text, kind="primary", on_click=None, *, default=False, icon=None):
        button = QPushButton(text)
        button.setCursor(Qt.PointingHandCursor)
        button.setStyleSheet(theme.button_qss(kind))
        button.setMinimumWidth(104)
        if icon:
            button.setIcon(qta.icon(icon, color="#0f0f0f" if kind == "primary" else "white"))
        button.clicked.connect(on_click or self.reject)
        if default:
            button.setDefault(True)
            button.setAutoDefault(True)
        else:
            button.setAutoDefault(False)
        self.footer.addWidget(button)
        return button

    def add_text(self, text, *, secondary=False):
        label = QLabel(text)
        label.setWordWrap(True)
        color = theme.TEXT_SECONDARY if secondary else theme.TEXT
        label.setStyleSheet(f"font-size: 14px; color: {color};")
        self.body.addWidget(label)
        return label

    def exec(self):
        scrim = self._show_scrim()
        try:
            return super().exec()
        finally:
            if scrim is not None:
                scrim.deleteLater()

    def _show_scrim(self):
        parent = self.parentWidget()
        if parent is None:
            return None
        window = parent.window()
        scrim = QWidget(window)
        scrim.setAttribute(Qt.WA_StyledBackground)
        scrim.setStyleSheet(f"background: {theme.SCRIM};")
        scrim.setGeometry(window.rect())
        scrim.show()
        scrim.raise_()
        return scrim


class ConfirmDialog(Modal):
    def __init__(self, parent, title, message, *, ok="Aceptar", cancel="Cancelar"):
        super().__init__(parent, title, closable=False)
        self.add_text(message, secondary=True)
        if cancel:
            self.add_button(cancel, "tonal", self.reject)
        self.add_button(ok, "primary", self.accept, default=True)


def confirm(parent, title, message, *, ok="Aceptar", cancel="Cancelar") -> bool:
    return ConfirmDialog(parent, title, message, ok=ok, cancel=cancel).exec() == QDialog.Accepted


def notify(parent, title, message) -> None:
    ConfirmDialog(parent, title, message, ok="Entendido", cancel=None).exec()

