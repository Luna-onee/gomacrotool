from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QComboBox, QSpinBox, QSlider, QPushButton,
    QCheckBox, QFrame, QSizePolicy, QApplication,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from modules import config_manager as config
from modules.theme import theme
from modules.gui.nerd_font import ICONS
from modules.gui.message_box import ThemedMessageBox


class SettingsDialog(QDialog):
    def showEvent(self, event):
        super().showEvent(event)
        from modules.gui.window_helpers import apply_rounded_corners
        apply_rounded_corners(self)

    def __init__(self, parent=None):
        super().__init__(None)
        self._drag_pos = None
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setMinimumWidth(400)
        self.setMinimumHeight(460)
        self.resize(440, 500)

        s = config.data.get("settings", {})
        t = theme.colors()

        # ---- Card frame ----
        card = QFrame()
        card.setProperty("class", "dialog-card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # ---- Titlebar ----
        titlebar = QFrame()
        titlebar.setProperty("class", "titlebar")
        titlebar.setFixedHeight(44)
        tb = QHBoxLayout(titlebar)
        tb.setContentsMargins(14, 0, 6, 0)
        tb.setSpacing(8)

        icon_lbl = QLabel(ICONS.COG)
        icon_lbl.setFont(QFont("Segoe UI", 11))
        icon_lbl.setStyleSheet(f"color: {t['primary']}; background: transparent; border: none;")
        tb.addWidget(icon_lbl)

        title_lbl = QLabel("Settings")
        title_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {t['text']}; background: transparent; border: none;")
        tb.addWidget(title_lbl)
        tb.addStretch()

        close_btn = QPushButton(ICONS.X)
        close_btn.setProperty("class", "titlebar-close")
        close_btn.setFixedSize(40, 28)
        close_btn.clicked.connect(self.reject)
        tb.addWidget(close_btn)
        card_layout.addWidget(titlebar)

        # ---- Content ----
        content = QFrame()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 14, 18, 14)

        # ---- Overlay section ----
        layout.addWidget(self._sec_label(ICONS.DESKTOP + "  Overlay"))

        overlay_form = QFormLayout()
        overlay_form.setSpacing(10)
        overlay_form.setContentsMargins(0, 0, 0, 0)

        self._pos_ddl = QComboBox()
        self._pos_ddl.addItems(["top-left", "top-right", "bottom-left", "bottom-right", "custom"])
        self._pos_ddl.setCurrentText(s.get("overlayPosition", "top-left"))
        overlay_form.addRow("Position:", self._pos_ddl)

        self._width_spin = QSpinBox()
        self._width_spin.setRange(160, 400)
        self._width_spin.setSingleStep(10)
        self._width_spin.setValue(s.get("overlayWidth", 230))
        overlay_form.addRow("Width:", self._width_spin)

        opacity_row = QHBoxLayout()
        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(30, 100)
        self._opacity_slider.setValue(int(s.get("overlayOpacity", 0.92) * 100))
        self._opacity_label = QLabel(f"{self._opacity_slider.value()}%")
        self._opacity_label.setFixedWidth(40)
        self._opacity_slider.valueChanged.connect(
            lambda v: self._opacity_label.setText(f"{v}%")
        )
        opacity_row.addWidget(self._opacity_slider)
        opacity_row.addWidget(self._opacity_label)
        overlay_form.addRow("Opacity:", opacity_row)

        self._clickable_chk = QCheckBox("Overlay clickable (allows drag + toggle)")
        self._clickable_chk.setChecked(s.get("overlayClickable", False))
        overlay_form.addRow(self._clickable_chk)

        layout.addLayout(overlay_form)

        # ---- General section ----
        layout.addWidget(self._sec_label(ICONS.COG + "  General"))

        gen_form = QFormLayout()
        gen_form.setSpacing(10)
        gen_form.setContentsMargins(0, 0, 0, 0)

        self._delay_spin = QSpinBox()
        self._delay_spin.setRange(0, 99999)
        self._delay_spin.setValue(s.get("defaultDelay", 50))
        gen_form.addRow("Default delay (ms):", self._delay_spin)

        self._toggle_ddl = QComboBox()
        self._toggle_ddl.addItems([
            "ScrollLock", "CapsLock", "NumLock", "Pause", "PrintScreen",
            "Insert", "F1", "F2", "F3", "F4", "F5", "F6",
            "F7", "F8", "F9", "F10", "F11", "F12",
            "XButton1", "XButton2",
        ])
        self._toggle_ddl.setCurrentText(s.get("toggleKey", "ScrollLock"))
        gen_form.addRow("Toggle key:", self._toggle_ddl)

        self._px_rate_spin = QSpinBox()
        self._px_rate_spin.setRange(10, 1000)
        self._px_rate_spin.setSingleStep(50)
        self._px_rate_spin.setValue(s.get("pixelCheckRate", 250))
        self._px_rate_spin.setToolTip("Pixel checks per second")
        gen_form.addRow("Pixel check rate:", self._px_rate_spin)

        self._auto_detect_chk = QCheckBox("Auto-detect active game")
        self._auto_detect_chk.setChecked(s.get("autoDetectGame", True))
        gen_form.addRow(self._auto_detect_chk)

        self._game_only_chk = QCheckBox("Only activate macros in-game")
        self._game_only_chk.setChecked(s.get("onlyInGame", True))
        gen_form.addRow(self._game_only_chk)

        layout.addLayout(gen_form)
        layout.addStretch()

        # ---- Buttons ----
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {theme.get('outlineVariant')}; border: none;")
        layout.addWidget(sep)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("class", "btn-text")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton(ICONS.CHECK + "  Save")
        save_btn.setProperty("class", "btn-filled")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)
        card_layout.addWidget(content)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.addWidget(card)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and e.position().y() <= 44:
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

    def _sec_label(self, text):
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {theme.get('primary')}; border: none; padding-top: 4px;")
        return lbl

    def _save(self):
        old_key = config.data["settings"].get("toggleKey", "ScrollLock")
        new_key = self._toggle_ddl.currentText()

        config.data["settings"]["overlayPosition"] = self._pos_ddl.currentText()
        config.data["settings"]["overlayWidth"] = self._width_spin.value()
        config.data["settings"]["overlayOpacity"] = self._opacity_slider.value() / 100.0
        config.data["settings"]["defaultDelay"] = self._delay_spin.value()
        config.data["settings"]["toggleKey"] = new_key
        config.data["settings"]["pixelCheckRate"] = self._px_rate_spin.value()
        config.data["settings"]["autoDetectGame"] = self._auto_detect_chk.isChecked()
        config.data["settings"]["onlyInGame"] = self._game_only_chk.isChecked()
        config.data["settings"]["overlayClickable"] = self._clickable_chk.isChecked()
        config.save()

        qapp = QApplication.instance()
        if qapp and hasattr(qapp, '_overlay'):
            ov = qapp._overlay
            ov._apply_settings()
            ov._position_overlay()
            ov._toggle_key = new_key
            ov.refresh_macros()

        if qapp and hasattr(qapp, '_setup_toggle_hook'):
            qapp._setup_toggle_hook()

        from modules.macro_engine import macro_engine
        from modules import pixel_triggers
        macro_engine.setup()
        pixel_triggers.setup()

        self.accept()
        parent = self.parent()
        if parent:
            ThemedMessageBox.information(parent, "Saved", "Settings saved successfully.")
        else:
            ThemedMessageBox.information(None, "Saved", "Settings saved successfully.")
