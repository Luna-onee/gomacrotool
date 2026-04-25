from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QComboBox, QPushButton, QCheckBox, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
     QFrame,
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QTimer
import ctypes

from modules import config_manager as config
from modules import utils
from modules.theme import theme
from modules.macro_engine import macro_engine
from modules.gui.main_window import HOTKEY_OPTIONS, KEY_OPTIONS
from modules.gui.nerd_font import ICONS
from modules.gui.message_box import ThemedMessageBox


# ------------------------------------------------------------------ #
#  MacroEditor — Material Design 3 Dialog
# ------------------------------------------------------------------ #
class MacroEditor(QDialog):
    def showEvent(self, event):
        super().showEvent(event)
        from modules.gui.window_helpers import apply_rounded_corners
        apply_rounded_corners(self)

    def __init__(self, parent=None, existing=None, idx=0):
        super().__init__(None)  # no parent — prevents silent crashes
        self._owner = parent     # stored for callbacks, NOT set as Qt parent
        self._existing = existing
        self._idx = idx
        self._temp_keys = []
        self._drag_pos = None
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setMinimumSize(560, 640)
        self._init_ui()
        self.resize(620, 680)
        if existing:
            self._load(existing)

    # ------------------------------------------------------------------ #
    #  Drag support for frameless titlebar
    # ------------------------------------------------------------------ #
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

    # ------------------------------------------------------------------ #
    #  UI
    # ------------------------------------------------------------------ #
    def _init_ui(self):
        t = theme.colors()

        # Outer card
        card = QFrame()
        card.setProperty("class", "dialog-card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # Titlebar — Material Design
        titlebar = QFrame()
        titlebar.setProperty("class", "titlebar")
        titlebar.setFixedHeight(44)
        tb = QHBoxLayout(titlebar)
        tb.setContentsMargins(14, 0, 6, 0)
        tb.setSpacing(8)

        icon_lbl = QLabel(chr(10002))   # ✦ styled marker
        icon_lbl.setFont(QFont("Segoe UI", 11))
        icon_lbl.setStyleSheet(f"color: {t['primary']}; background: transparent; border: none;")
        tb.addWidget(icon_lbl)

        title_txt = "Add Macro" if not self._idx else "Edit Macro"
        title_lbl = QLabel(title_txt)
        title_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {t['text']}; background: transparent; border: none;")
        tb.addWidget(title_lbl)
        tb.addStretch()

        close_btn = QPushButton(ICONS.X)
        close_btn.setFixedSize(34, 30)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                color: {t['textSecondary']};
                background: transparent;
                border: none;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: #C42B1C;
                color: white;
            }}
        """)
        close_btn.clicked.connect(self.reject)
        tb.addWidget(close_btn)
        card_layout.addWidget(titlebar)

        # Content area
        content = QFrame()
        content.setObjectName("content")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 12, 16, 12)
        content_layout.setSpacing(6)

        # Top grid: Name / Key
        top_grid = QGridLayout()
        top_grid.setSpacing(6)

        lbl = QLabel("Name:")
        lbl.setStyleSheet(f"color: {t['textSecondary']}; background: transparent; border: none;")
        top_grid.addWidget(lbl, 0, 0)
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Macro name…")
        top_grid.addWidget(self._name_edit, 0, 1, 1, 3)

        lbl2 = QLabel("Hotkey:")
        lbl2.setStyleSheet(f"color: {t['textSecondary']}; background: transparent; border: none;")
        top_grid.addWidget(lbl2, 1, 0)
        self._hk_ddl = QComboBox()
        self._hk_ddl.setEditable(True)
        self._hk_ddl.addItems(HOTKEY_OPTIONS)
        self._hk_ddl.setPlaceholderText("Select or type…")
        top_grid.addWidget(self._hk_ddl, 1, 1, 1, 2)
        bind_btn = QPushButton("Bind")
        bind_btn.setProperty("class", "btn-tonal")
        bind_btn.clicked.connect(self._bind_key)
        top_grid.addWidget(bind_btn, 1, 3)
        top_grid.setColumnStretch(1, 1)
        content_layout.addLayout(top_grid)

        # Second grid: Delay / Hold / IKD / Enabled
        mid_grid = QGridLayout()
        mid_grid.setSpacing(6)

        lbl3 = QLabel("Delay (ms):")
        lbl3.setStyleSheet(f"color: {t['textSecondary']}; background: transparent; border: none;")
        mid_grid.addWidget(lbl3, 0, 0)
        self._delay_edit = QLineEdit(str(config.data["settings"]["defaultDelay"]))
        self._delay_edit.setFixedWidth(70)
        mid_grid.addWidget(self._delay_edit, 0, 1)

        self._hold_chk = QCheckBox("Hold Mode")
        mid_grid.addWidget(self._hold_chk, 0, 2)

        self._enabled_chk = QCheckBox("Enabled")
        self._enabled_chk.setChecked(True)
        mid_grid.addWidget(self._enabled_chk, 0, 3)
        mid_grid.setColumnStretch(2, 1)

        lbl5 = QLabel("Inter-Key Delay (ms):")
        lbl5.setStyleSheet(f"color: {t['textSecondary']}; background: transparent; border: none;")
        mid_grid.addWidget(lbl5, 1, 0)
        self._ikd_edit = QLineEdit("0")
        self._ikd_edit.setFixedWidth(70)
        mid_grid.addWidget(self._ikd_edit, 1, 1)
        mid_grid.setRowStretch(1, 0)
        content_layout.addLayout(mid_grid)

        # Key sequence
        seq_header = QLabel("Key Sequence")
        seq_header.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        seq_header.setStyleSheet(f"color: {t['textSecondary']}; background: transparent; border: none; text-transform: uppercase; letter-spacing: 0.5px;")
        content_layout.addWidget(seq_header)

        seq_layout = QHBoxLayout()
        seq_layout.setSpacing(8)

        self._key_table = QTableWidget(0, 2)
        self._key_table.setObjectName("key-table")
        self._key_table.setHorizontalHeaderLabels(["#", "Key"])
        self._key_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._key_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._key_table.verticalHeader().setVisible(False)
        self._key_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._key_table.setColumnWidth(0, 32)
        self._key_table.horizontalHeader().setStretchLastSection(True)
        self._key_table.setMinimumHeight(160)
        seq_layout.addWidget(self._key_table, 1)

        key_btn_layout = QVBoxLayout()
        key_btn_layout.setSpacing(10)
        self._key_ddl = QComboBox()
        self._key_ddl.setEditable(True)
        self._key_ddl.addItems(HOTKEY_OPTIONS)
        self._key_ddl.setPlaceholderText("Select key…")
        key_btn_layout.addWidget(self._key_ddl)

        add_key_btn = QPushButton("Add")
        add_key_btn.setProperty("class", "btn-filled")
        add_key_btn.clicked.connect(self._add_key)
        key_btn_layout.addWidget(add_key_btn)

        rem_key_btn = QPushButton("Remove")
        rem_key_btn.setProperty("class", "btn-outlined")
        rem_key_btn.clicked.connect(self._remove_key)
        key_btn_layout.addWidget(rem_key_btn)

        up_btn = QPushButton("Move Up")
        up_btn.setProperty("class", "btn-tonal")
        up_btn.clicked.connect(self._move_up)
        key_btn_layout.addWidget(up_btn)

        dn_btn = QPushButton("Move Down")
        dn_btn.setProperty("class", "btn-tonal")
        dn_btn.clicked.connect(self._move_down)
        key_btn_layout.addWidget(dn_btn)

        clear_btn = QPushButton("Clear All")
        clear_btn.setProperty("class", "btn-outlined")
        clear_btn.clicked.connect(self._clear_keys)
        key_btn_layout.addWidget(clear_btn)

        key_btn_layout.addStretch()
        seq_layout.addLayout(key_btn_layout)
        content_layout.addLayout(seq_layout, 1)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("class", "btn-text")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setProperty("class", "btn-filled")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)
        content_layout.addLayout(btn_layout)

        card_layout.addWidget(content)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.addWidget(card)

    # ------------------------------------------------------------------ #
    #  Data
    # ------------------------------------------------------------------ #
    def _load(self, ex):
        self._name_edit.setText(ex.get("name", ""))
        hk = ex.get("hotkey", "")
        idx = self._hk_ddl.findText(hk)
        if idx >= 0:
            self._hk_ddl.setCurrentIndex(idx)
        else:
            self._hk_ddl.setCurrentText(hk)
        self._delay_edit.setText(str(ex.get("delay", 0)))
        self._hold_chk.setChecked(ex.get("holdMode", False))
        self._enabled_chk.setChecked(ex.get("enabled", True))
        self._ikd_edit.setText(str(ex.get("interKeyDelay", 0)))
        self._temp_keys = list(ex.get("keys", []))
        self._refresh_key_table()

    def _refresh_key_table(self):
        self._key_table.setRowCount(0)
        for i, k in enumerate(self._temp_keys):
            row = self._key_table.rowCount()
            self._key_table.insertRow(row)
            self._key_table.setItem(row, 0, QTableWidgetItem(str(i + 1)))
            self._key_table.setItem(row, 1, QTableWidgetItem(k))
        self._key_table.setColumnWidth(0, 32)
        self._key_table.resizeColumnsToContents()

    def _add_key(self):
        sel = self._key_ddl.currentText().strip()
        if not sel:
            return
        self._temp_keys.append(sel)
        self._refresh_key_table()

    def _remove_key(self):
        row = self._key_table.currentRow()
        if row < 0 or row >= len(self._temp_keys):
            return
        self._temp_keys.pop(row)
        self._refresh_key_table()

    def _move_up(self):
        row = self._key_table.currentRow()
        if row <= 0 or row >= len(self._temp_keys):
            return
        self._temp_keys[row], self._temp_keys[row - 1] = self._temp_keys[row - 1], self._temp_keys[row]
        self._refresh_key_table()
        self._key_table.selectRow(row - 1)

    def _move_down(self):
        row = self._key_table.currentRow()
        if row < 0 or row >= len(self._temp_keys) - 1:
            return
        self._temp_keys[row], self._temp_keys[row + 1] = self._temp_keys[row + 1], self._temp_keys[row]
        self._refresh_key_table()
        self._key_table.selectRow(row + 1)

    def _clear_keys(self):
        self._temp_keys.clear()
        self._refresh_key_table()

    def _bind_key(self):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel
        dlg = QDialog(self)
        dlg.setWindowTitle("Bind Key")
        dlg.setFixedSize(220, 90)
        dlg.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        layout = QVBoxLayout(dlg)
        lbl = QLabel("Press a key or mouse button…\n(Escape to cancel)")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"color: {theme.colors()['text']}; background: transparent; border: none;")
        layout.addWidget(lbl)

        VK_MAP = {
            0x01: "LButton", 0x02: "RButton", 0x04: "MButton", 0x05: "XButton1", 0x06: "XButton2",
            0x08: "Backspace", 0x09: "Tab", 0x0D: "Enter", 0x1B: "Escape", 0x20: "Space",
            0x21: "PgUp", 0x22: "PgDn", 0x23: "End", 0x24: "Home", 0x25: "Left",
            0x26: "Up", 0x27: "Right", 0x28: "Down", 0x2D: "Insert", 0x2E: "Delete",
            0x30: "0", 0x31: "1", 0x32: "2", 0x33: "3", 0x34: "4",
            0x35: "5", 0x36: "6", 0x37: "7", 0x38: "8", 0x39: "9",
            0x41: "a", 0x42: "b", 0x43: "c", 0x44: "d", 0x45: "e",
            0x46: "f", 0x47: "g", 0x48: "h", 0x49: "i", 0x4A: "j",
            0x4B: "k", 0x4C: "l", 0x4D: "m", 0x4E: "n", 0x4F: "o",
            0x50: "p", 0x51: "q", 0x52: "r", 0x53: "s", 0x54: "t",
            0x55: "u", 0x56: "v", 0x57: "w", 0x58: "x", 0x59: "y", 0x5A: "z",
            0x60: "Numpad0", 0x61: "Numpad1", 0x62: "Numpad2", 0x63: "Numpad3",
            0x64: "Numpad4", 0x65: "Numpad5", 0x66: "Numpad6", 0x67: "Numpad7",
            0x68: "Numpad8", 0x69: "Numpad9",
            0x70: "F1", 0x71: "F2", 0x72: "F3", 0x73: "F4", 0x74: "F5",
            0x75: "F6", 0x76: "F7", 0x77: "F8", 0x78: "F9", 0x79: "F10",
            0x7A: "F11", 0x7B: "F12",
            0x10: "Shift", 0x11: "Ctrl", 0x12: "Alt",
            0x14: "CapsLock", 0x90: "NumLock", 0x91: "ScrollLock",
        }
        u32 = ctypes.windll.user32
        mouse_keys = {0x01, 0x02, 0x04, 0x05, 0x06}
        check_vks = set(VK_MAP.keys()) | mouse_keys

        def poll():
            mods = ""
            if u32.GetAsyncKeyState(0x11) & 0x8000:
                mods = "^"
            elif u32.GetAsyncKeyState(0x12) & 0x8000:
                mods = "!"
            elif u32.GetAsyncKeyState(0x10) & 0x8000:
                mods = "+"

            for vk in check_vks:
                if vk in (0x10, 0x11, 0x12):
                    continue
                if u32.GetAsyncKeyState(vk) & 0x8000:
                    name = VK_MAP.get(vk, str(vk))
                    result = mods + name
                    self._hk_ddl.setCurrentText(result)
                    dlg.accept()
                    return

            # Escape to cancel
            if u32.GetAsyncKeyState(0x1B) & 0x8000:
                dlg.reject()

        timer = QTimer(dlg)
        timer.timeout.connect(poll)
        timer.start(20)
        dlg.exec()
        timer.stop()

    def _save(self):
        n = self._name_edit.text().strip()
        hk = self._hk_ddl.currentText().strip()
        if not n or not hk:
            ThemedMessageBox.information(self, "Validation", "Name and Hotkey are required.")
            return
        if not self._temp_keys:
            ThemedMessageBox.information(self, "Validation", "Add at least one key to the sequence.")
            return

        if config._get_spec() is None:
            ThemedMessageBox.information(self, "Validation", "Select a Game > Class > Spec first.")
            return

        d = utils.safe_int(self._delay_edit.text(), 0)
        d = max(0, d)
        ikd = utils.safe_int(self._ikd_edit.text(), 0)
        ikd = max(0, ikd)

        macro = {
            "name": n,
            "hotkey": hk,
            "delay": d,
            "holdMode": self._hold_chk.isChecked(),
            "enabled": self._enabled_chk.isChecked(),
            "keys": list(self._temp_keys),
            "interKeyDelay": ikd,
        }

        macros = config.get_macros()
        for i, existing in enumerate(macros):
            if i + 1 == self._idx:
                continue
            if existing.get("hotkey") == hk:
                if ThemedMessageBox.question(
                    self, "Hotkey Conflict",
                    f"Hotkey '{hk}' is already used by '{existing['name']}'.\n\nReplace it?"
                ) != ThemedMessageBox.Yes:
                    return
                macros.pop(i)
                if self._idx > i + 1:
                    self._idx -= 1
                break

        if 0 < self._idx <= len(macros):
            macros[self._idx - 1] = macro
        else:
            macros.append(macro)

        config.save()
        if self._owner and hasattr(self._owner, '_refresh_macro_list'):
            self._owner._refresh_macro_list()
        if self._owner and hasattr(self._owner, 'refresh_overlay'):
            self._owner.refresh_overlay()
        macro_engine.setup()
        self.accept()
