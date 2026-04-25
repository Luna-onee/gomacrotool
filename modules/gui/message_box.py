"""Themed message box dialog to replace native QMessageBox."""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from modules.theme import theme
from modules.gui.nerd_font import ICONS


class ThemedMessageBox(QDialog):
    """Frameless card-styled message box matching the app theme."""

    # Return values matching QMessageBox.StandardButton
    Yes = 1
    No = 0
    Ok = 1
    Cancel = 0

    def __init__(self, parent=None, title="", text="", icon_type="info", buttons=("ok",)):
        super().__init__(parent)
        self._result = self.Cancel
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setMinimumWidth(320)
        self.setMaximumWidth(480)
        self._drag_pos = None
        self._init_ui(title, text, icon_type, buttons)

    def _init_ui(self, title, text, icon_type, buttons):
        t = theme.colors()

        card = QFrame()
        card.setProperty("class", "dialog-card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # Titlebar
        titlebar = QFrame()
        titlebar.setProperty("class", "titlebar")
        titlebar.setFixedHeight(40)
        tb = QHBoxLayout(titlebar)
        tb.setContentsMargins(14, 0, 6, 0)
        tb.setSpacing(8)

        icon_map = {
            "info": (ICONS.INFO, t["primary"]),
            "warning": (ICONS.EXCLAMATION, t["tertiary"]),
            "error": (ICONS.TIMES, t["error"]),
            "question": (ICONS.QUESTION, t["secondary"]),
        }
        icon_char, icon_color = icon_map.get(icon_type, icon_map["info"])

        icon_lbl = QLabel(icon_char)
        icon_lbl.setFont(QFont("Segoe UI", 12))
        icon_lbl.setStyleSheet(f"color: {icon_color}; background: transparent; border: none;")
        tb.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {t['text']}; background: transparent; border: none;")
        tb.addWidget(title_lbl)
        tb.addStretch()

        close_btn = QPushButton(ICONS.X)
        close_btn.setProperty("class", "titlebar-close")
        close_btn.setFixedSize(36, 26)
        close_btn.clicked.connect(self._on_cancel)
        tb.addWidget(close_btn)
        card_layout.addWidget(titlebar)

        # Content
        content = QFrame()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(12)

        big_icon = QLabel(icon_char)
        big_icon.setFont(QFont("Segoe UI", 28))
        big_icon.setStyleSheet(f"color: {icon_color}; background: transparent; border: none;")
        content_layout.addWidget(big_icon, alignment=Qt.AlignmentFlag.AlignTop)

        msg_lbl = QLabel(text)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet(f"color: {t['text']}; background: transparent; border: none; font-size: 10pt;")
        content_layout.addWidget(msg_lbl, 1)
        card_layout.addWidget(content)

        # Buttons
        btn_frame = QFrame()
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(16, 8, 16, 16)
        btn_layout.setSpacing(8)
        btn_layout.addStretch()

        for btn_name in buttons:
            if btn_name == "ok":
                btn = QPushButton("OK")
                btn.setProperty("class", "btn-filled")
                btn.clicked.connect(self._on_ok)
            elif btn_name == "yes":
                btn = QPushButton("Yes")
                btn.setProperty("class", "btn-filled")
                btn.clicked.connect(self._on_yes)
            elif btn_name == "no":
                btn = QPushButton("No")
                btn.setProperty("class", "btn-outlined")
                btn.clicked.connect(self._on_no)
            elif btn_name == "cancel":
                btn = QPushButton("Cancel")
                btn.setProperty("class", "btn-text")
                btn.clicked.connect(self._on_cancel)
            else:
                continue
            btn_layout.addWidget(btn)

        card_layout.addWidget(btn_frame)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.addWidget(card)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and e.position().y() <= 40:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            e.accept()
        else:
            super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._drag_pos is not None and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)
            e.accept()
        else:
            super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None
        super().mouseReleaseEvent(e)

    def _on_ok(self):
        self._result = self.Ok
        self.accept()

    def _on_yes(self):
        self._result = self.Yes
        self.accept()

    def _on_no(self):
        self._result = self.No
        self.accept()

    def _on_cancel(self):
        self._result = self.Cancel
        self.reject()

    def result(self):
        return self._result

    @staticmethod
    def information(parent, title, text):
        dlg = ThemedMessageBox(parent, title, text, "info", ("ok",))
        dlg.exec()
        return dlg.result()

    @staticmethod
    def warning(parent, title, text):
        dlg = ThemedMessageBox(parent, title, text, "warning", ("ok",))
        dlg.exec()
        return dlg.result()

    @staticmethod
    def critical(parent, title, text):
        dlg = ThemedMessageBox(parent, title, text, "error", ("ok",))
        dlg.exec()
        return dlg.result()

    @staticmethod
    def question(parent, title, text):
        dlg = ThemedMessageBox(parent, title, text, "question", ("yes", "no"))
        dlg.exec()
        return dlg.result()
