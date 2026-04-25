from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QComboBox, QPushButton, QCheckBox, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
     QFrame, QWidget,
)
from PyQt6.QtGui import QPainter, QColor, QBrush, QFont, QPen
from PyQt6.QtCore import Qt

from modules import config_manager as config
from modules import utils
from modules.theme import theme
from modules.macro_engine import macro_engine
from modules.gui.main_window import HOTKEY_OPTIONS, KEY_OPTIONS
from modules.gui.nerd_font import ICONS
from modules.gui.message_box import ThemedMessageBox


# ------------------------------------------------------------------ #
#  Custom table items
# ------------------------------------------------------------------ #
class ColorSwatchItem(QTableWidgetItem):
    def __init__(self, color_hex, editable=True):
        super().__init__(color_hex)
        self._color_hex = color_hex
        if editable:
            self.setFlags(self.flags() | Qt.ItemFlag.ItemIsEditable)
        else:
            self.setFlags(self.flags() & ~Qt.ItemFlag.ItemIsEditable)

    def setData(self, role, value):
        super().setData(role, value)
        if role == Qt.ItemDataRole.EditRole:
            self._color_hex = str(value).strip()

    def paint(self, painter, option, widget=None):
        painter.save()
        sw = 14
        mg = 3
        swatch_rect = option.rect.adjusted(mg, mg, 0, 0)
        swatch_rect.setWidth(sw)
        swatch_rect.setHeight(min(sw, option.rect.height() - 2 * mg))
        swatch_rect.moveTop(option.rect.top() + (option.rect.height() - swatch_rect.height()) // 2)
        try:
            qc = QColor(self._color_hex)
        except Exception:
            qc = QColor(0, 0, 0)
        painter.fillRect(swatch_rect, QBrush(qc))
        painter.setPen(QPen(QColor(theme.colors().get("outline", "#999"))))
        painter.drawRect(swatch_rect)
        text_rect = option.rect.adjusted(sw + 2 * mg, 0, 0, 0)
        painter.setPen(QPen(QColor(theme.colors().get("text", "#eee"))))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._color_hex)
        painter.restore()


class EditableItem(QTableWidgetItem):
    def __init__(self, text):
        super().__init__(text)
        self.setFlags(self.flags() | Qt.ItemFlag.ItemIsEditable)


# ------------------------------------------------------------------ #
#  BuffEditor — Material Design 3 Dialog
# ------------------------------------------------------------------ #
class BuffEditor(QDialog):
    def showEvent(self, event):
        super().showEvent(event)
        from modules.gui.window_helpers import apply_rounded_corners
        apply_rounded_corners(self)

    def __init__(self, parent=None, existing=None, idx=0):
        super().__init__(None)  # no parent — prevents silent crashes
        self._existing = existing
        self._idx = idx
        self._temp_watch = []
        self._temp_pixels = []
        self._capture_res = None
        self._drag_pos = None
        self._owner = parent     # stored for callbacks, NOT set as Qt parent
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setMinimumSize(620, 640)
        self._init_ui()
        self.resize(660, 680)
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

        title_txt = "Add Buff Timer" if not self._idx else "Edit Buff Timer"
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

        # Content
        content = QFrame()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 10, 16, 12)
        content_layout.setSpacing(6)

        # Row 1: Name / Trigger type
        top_grid = QGridLayout()
        top_grid.setSpacing(6)
        lbl = QLabel("Name:")
        lbl.setStyleSheet(f"color: {t['textSecondary']}; background: transparent; border: none;")
        top_grid.addWidget(lbl, 0, 0)
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Buff name…")
        top_grid.addWidget(self._name_edit, 0, 1, 1, 2)

        lbl2 = QLabel("Trigger:")
        lbl2.setStyleSheet(f"color: {t['textSecondary']}; background: transparent; border: none;")
        top_grid.addWidget(lbl2, 0, 3)
        self._trigger_ddl = QComboBox()
        self._trigger_ddl.addItems(["Watch Keys", "Pixel"])
        self._trigger_ddl.currentTextChanged.connect(self._update_trigger_mode)
        top_grid.addWidget(self._trigger_ddl, 0, 4, 1, 2)
        top_grid.setColumnStretch(1, 1)
        top_grid.setColumnStretch(4, 1)
        content_layout.addLayout(top_grid)

        # Row 2: Action key
        action_row = QHBoxLayout()
        lbl3 = QLabel("Action (key on expiry):")
        lbl3.setStyleSheet(f"color: {t['textSecondary']}; background: transparent; border: none;")
        action_row.addWidget(lbl3)
        self._action_ddl = QComboBox()
        self._action_ddl.setEditable(True)
        self._action_ddl.addItems(KEY_OPTIONS)
        action_row.addWidget(self._action_ddl, 1)
        action_row.addStretch()
        content_layout.addLayout(action_row)

        # Watch keys section
        self._watch_label = QLabel("Watch Keys")
        self._watch_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self._watch_label.setStyleSheet(f"color: {t['textSecondary']}; background: transparent; border: none; text-transform: uppercase; letter-spacing: 0.5px;")
        content_layout.addWidget(self._watch_label)

        watch_layout = QHBoxLayout()
        watch_layout.setSpacing(8)
        self._watch_table = QTableWidget(0, 2)
        self._watch_table.setHorizontalHeaderLabels(["#", "Key"])
        self._watch_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._watch_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._watch_table.verticalHeader().setVisible(False)
        self._watch_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._watch_table.setColumnWidth(0, 32)
        self._watch_table.horizontalHeader().setStretchLastSection(True)
        self._watch_table.setMinimumHeight(110)
        watch_layout.addWidget(self._watch_table, 1)

        watch_btn = QVBoxLayout()
        watch_btn.setSpacing(10)
        self._watch_ddl = QComboBox()
        self._watch_ddl.setEditable(True)
        self._watch_ddl.addItems(HOTKEY_OPTIONS)
        self._watch_ddl.setPlaceholderText("Select key…")
        watch_btn.addWidget(self._watch_ddl)
        add_w = QPushButton("Add")
        add_w.setProperty("class", "btn-filled")
        add_w.clicked.connect(self._add_watch)
        watch_btn.addWidget(add_w)
        rem_w = QPushButton("Remove")
        rem_w.setProperty("class", "btn-outlined")
        rem_w.clicked.connect(self._remove_watch)
        watch_btn.addWidget(rem_w)
        clear_w = QPushButton("Clear All")
        clear_w.setProperty("class", "btn-outlined")
        clear_w.clicked.connect(self._clear_watch)
        watch_btn.addWidget(clear_w)
        watch_btn.addStretch()
        watch_layout.addLayout(watch_btn)
        self._watch_container = QWidget()
        wc = QVBoxLayout(self._watch_container)
        wc.setContentsMargins(0, 0, 0, 0)
        wc.addLayout(watch_layout)
        content_layout.addWidget(self._watch_container)

        # Pixel section
        self._px_label = QLabel("Pixels")
        self._px_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self._px_label.setStyleSheet(f"color: {t['textSecondary']}; background: transparent; border: none; text-transform: uppercase; letter-spacing: 0.5px;")
        content_layout.addWidget(self._px_label)

        px_match_row = QHBoxLayout()
        lbl_mm = QLabel("Match:")
        lbl_mm.setStyleSheet(f"color: {t['textSecondary']}; background: transparent; border: none;")
        px_match_row.addWidget(lbl_mm)
        self._px_match_ddl = QComboBox()
        self._px_match_ddl.addItems(["All Match", "Any Match"])
        px_match_row.addWidget(self._px_match_ddl)
        px_match_row.addStretch()
        content_layout.addLayout(px_match_row)

        px_layout = QHBoxLayout()
        px_layout.setSpacing(8)
        self._px_table = QTableWidget(0, 4)
        self._px_table.setHorizontalHeaderLabels(["X", "Y", "Color", "Var"])
        self._px_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._px_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._px_table.verticalHeader().setVisible(False)
        self._px_table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed)
        for i, w in enumerate([50, 50, 110, 44]):
            self._px_table.setColumnWidth(i, w)
        self._px_table.horizontalHeader().setStretchLastSection(True)
        self._px_table.setMinimumHeight(110)
        self._px_table.cellChanged.connect(self._on_px_cell_changed)
        px_layout.addWidget(self._px_table, 1)

        px_btn = QVBoxLayout()
        px_btn.setSpacing(10)
        pick_btn = QPushButton("Pick")
        pick_btn.setProperty("class", "btn-filled")
        pick_btn.clicked.connect(self._pick)
        px_btn.addWidget(pick_btn)
        edit_px_btn = QPushButton("Edit")
        edit_px_btn.setProperty("class", "btn-tonal")
        edit_px_btn.clicked.connect(self._edit_pixel)
        px_btn.addWidget(edit_px_btn)
        rem_px_btn = QPushButton("Remove")
        rem_px_btn.setProperty("class", "btn-outlined")
        rem_px_btn.clicked.connect(self._remove_pixel)
        px_btn.addWidget(rem_px_btn)
        clear_px_btn = QPushButton("Clear All")
        clear_px_btn.setProperty("class", "btn-outlined")
        clear_px_btn.clicked.connect(self._clear_pixels)
        px_btn.addWidget(clear_px_btn)
        px_btn.addStretch()
        px_layout.addLayout(px_btn)
        self._px_container = QWidget()
        pc = QVBoxLayout(self._px_container)
        pc.setContentsMargins(0, 0, 0, 0)
        pc.addLayout(px_layout)
        content_layout.addWidget(self._px_container)

        # Bottom grid: Duration / Refresh
        bottom_grid = QGridLayout()
        bottom_grid.setSpacing(6)
        lbl5 = QLabel("Duration (ms):")
        lbl5.setStyleSheet(f"color: {t['textSecondary']}; background: transparent; border: none;")
        bottom_grid.addWidget(lbl5, 0, 0)
        self._duration_edit = QLineEdit("5000")
        self._duration_edit.setFixedWidth(80)
        bottom_grid.addWidget(self._duration_edit, 0, 1)

        lbl7 = QLabel("On Refresh:")
        lbl7.setStyleSheet(f"color: {t['textSecondary']}; background: transparent; border: none;")
        bottom_grid.addWidget(lbl7, 0, 2)
        self._refresh_ddl = QComboBox()
        self._refresh_ddl.addItems(["Reset", "Extend"])
        self._refresh_ddl.currentTextChanged.connect(self._update_extend)
        bottom_grid.addWidget(self._refresh_ddl, 0, 3)

        lbl8 = QLabel("Extend (ms):")
        lbl8.setStyleSheet(f"color: {t['textSecondary']}; background: transparent; border: none;")
        bottom_grid.addWidget(lbl8, 1, 0)
        self._extend_edit = QLineEdit("0")
        self._extend_edit.setFixedWidth(80)
        self._extend_edit.setEnabled(False)
        bottom_grid.addWidget(self._extend_edit, 1, 1)

        self._enabled_chk = QCheckBox("Enabled")
        self._enabled_chk.setChecked(True)
        bottom_grid.addWidget(self._enabled_chk, 1, 2, 1, 2)
        bottom_grid.setColumnStretch(1, 1)
        bottom_grid.setColumnStretch(3, 1)
        content_layout.addLayout(bottom_grid)

        # Resolution label
        self._res_label = QLabel("")
        self._res_label.setStyleSheet(f"color: {t['textSecondary']}; background: transparent; border: none; font-size: 9pt;")
        content_layout.addWidget(self._res_label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("class", "btn-text")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        save_btn = QPushButton("Save")
        save_btn.setProperty("class", "btn-filled")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)
        content_layout.addLayout(btn_layout)

        card_layout.addWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.addWidget(card)
        self._update_trigger_mode()

    # ------------------------------------------------------------------ #
    #  Data / logic
    # ------------------------------------------------------------------ #
    def _load(self, ex):
        self._name_edit.setText(ex.get("name", ""))
        if ex.get("actionKey"):
            self._action_ddl.setCurrentText(ex["actionKey"])
        self._duration_edit.setText(str(ex.get("duration", 5000)))
        on_refresh = ex.get("onRefresh", "reset")
        self._refresh_ddl.setCurrentIndex(1 if on_refresh == "extend" else 0)
        self._extend_edit.setText(str(ex.get("extendMs", 0)))
        self._update_extend()
        self._enabled_chk.setChecked(ex.get("enabled", True))
        trigger_type = ex.get("triggerType", "keys")
        self._trigger_ddl.setCurrentIndex(1 if trigger_type == "pixel" else 0)
        if trigger_type == "pixel":
            for px in ex.get("triggerPixels", []):
                self._temp_pixels.append({"x": px.get("x", 0), "y": px.get("y", 0),
                                          "color": px.get("color", "0x000000"),
                                          "variation": px.get("variation", 10)})
            match_mode = ex.get("triggerMatchMode", "all")
            self._px_match_ddl.setCurrentIndex(1 if match_mode == "any" else 0)
        else:
            self._temp_watch = list(ex.get("watchKeys", []))
        self._capture_res = ex.get("captureRes")
        if self._capture_res:
            self._res_label.setText(f"Captured at {self._capture_res.get('w','?')}x{self._capture_res.get('h','?')}")
        self._refresh_watch_table()
        self._refresh_px_table()

    def _update_trigger_mode(self):
        is_pixel = self._trigger_ddl.currentText() == "Pixel"
        self._watch_label.setVisible(not is_pixel)
        self._watch_container.setVisible(not is_pixel)
        self._px_label.setVisible(is_pixel)
        self._px_container.setVisible(is_pixel)

    def _refresh_watch_table(self):
        self._watch_table.setRowCount(0)
        for i, k in enumerate(self._temp_watch):
            row = self._watch_table.rowCount()
            self._watch_table.insertRow(row)
            self._watch_table.setItem(row, 0, QTableWidgetItem(str(i + 1)))
            self._watch_table.setItem(row, 1, QTableWidgetItem(k))
        self._watch_table.setColumnWidth(0, 32)
        self._watch_table.resizeColumnsToContents()

    def _refresh_px_table(self):
        self._px_table.blockSignals(True)
        self._px_table.setRowCount(0)
        for px in self._temp_pixels:
            row = self._px_table.rowCount()
            self._px_table.insertRow(row)
            self._px_table.setItem(row, 0, QTableWidgetItem(str(px["x"])))
            self._px_table.setItem(row, 1, QTableWidgetItem(str(px["y"])))
            self._px_table.setItem(row, 2, ColorSwatchItem(px["color"]))
            self._px_table.setItem(row, 3, EditableItem(str(px["variation"])))
        self._px_table.blockSignals(False)
        self._px_table.resizeColumnsToContents()

    def _on_px_cell_changed(self, row, col):
        if row < 0 or row >= len(self._temp_pixels):
            return
        item = self._px_table.item(row, col)
        if not item:
            return
        if col == 2:
            self._temp_pixels[row]["color"] = item.text().strip()
        elif col == 3:
            try:
                self._temp_pixels[row]["variation"] = max(0, int(item.text().strip()))
            except ValueError:
                pass

    def _add_watch(self):
        sel = self._watch_ddl.currentText().strip()
        if not sel:
            return
        self._temp_watch.append(sel)
        self._refresh_watch_table()

    def _remove_watch(self):
        row = self._watch_table.currentRow()
        if row < 0 or row >= len(self._temp_watch):
            return
        self._temp_watch.pop(row)
        self._refresh_watch_table()

    def _clear_watch(self):
        self._temp_watch.clear()
        self._refresh_watch_table()

    def _pick(self):
        self._pick_mode = "add"
        from modules import pixel_picker
        pixel_picker.start(self._on_picked)

    def _edit_pixel(self):
        row = self._px_table.currentRow()
        if row < 0 or row >= len(self._temp_pixels):
            return
        self._pick_mode = "edit"
        self._pick_edit_idx = row
        from modules import pixel_picker
        pixel_picker.start(self._on_picked)

    def _on_picked(self, result):
        if result and isinstance(result, dict):
            px = {"x": result["x"], "y": result["y"],
                  "color": result["color"], "variation": 10}
            if self._pick_mode == "edit" and 0 <= self._pick_edit_idx < len(self._temp_pixels):
                self._temp_pixels[self._pick_edit_idx] = px
            else:
                self._temp_pixels.append(px)
            if result.get("screenRes") and not self._capture_res:
                self._capture_res = result["screenRes"]
                self._res_label.setText(f"Captured at {self._capture_res['w']}x{self._capture_res['h']}")
            self._refresh_px_table()
        self.raise_()
        self.activateWindow()

    def _remove_pixel(self):
        row = self._px_table.currentRow()
        if row < 0 or row >= len(self._temp_pixels):
            return
        self._temp_pixels.pop(row)
        self._refresh_px_table()

    def _clear_pixels(self):
        self._temp_pixels.clear()
        self._refresh_px_table()

    def _update_extend(self):
        self._extend_edit.setEnabled(self._refresh_ddl.currentText() == "Extend")

    def _save(self):
        n = self._name_edit.text().strip()
        action_key = self._action_ddl.currentText().strip()
        if not n or not action_key:
            ThemedMessageBox.information(self, "Validation", "Name and Action key are required.")
            return
        if config._get_spec() is None:
            ThemedMessageBox.information(self, "Validation", "Select a Game > Class > Spec first.")
            return

        is_pixel = self._trigger_ddl.currentText() == "Pixel"
        if is_pixel:
            if not self._temp_pixels:
                ThemedMessageBox.information(self, "Validation", "Add at least one pixel.")
                return
        else:
            if not self._temp_watch:
                ThemedMessageBox.information(self, "Validation", "Add at least one watch key.")
                return

        duration = utils.safe_int(self._duration_edit.text(), 5000)
        duration = max(100, duration)
        extend_ms = utils.safe_int(self._extend_edit.text(), 0)
        extend_ms = max(0, extend_ms)
        on_refresh = "extend" if self._refresh_ddl.currentText() == "Extend" else "reset"
        if on_refresh == "reset":
            extend_ms = 0

        buff = {
            "name": n,
            "duration": duration,
            "actionKey": action_key,
            "onRefresh": on_refresh,
            "extendMs": extend_ms,
            "enabled": self._enabled_chk.isChecked(),
            "triggerType": "pixel" if is_pixel else "keys",
            "captureRes": self._capture_res if is_pixel else None,
        }

        if is_pixel:
            buff["triggerPixels"] = [dict(px) for px in self._temp_pixels]
            buff["triggerMatchMode"] = "any" if self._px_match_ddl.currentText() == "Any Match" else "all"
            buff["watchKeys"] = []
        else:
            buff["watchKeys"] = list(self._temp_watch)
            buff["triggerPixels"] = []

        buffs = config.get_buffs()
        if 0 < self._idx <= len(buffs):
            buffs[self._idx - 1] = buff
        else:
            buffs.append(buff)
        config.save()
        if self._owner and hasattr(self._owner, '_refresh_buff_list'):
            self._owner._refresh_buff_list()
        if self._owner and hasattr(self._owner, 'refresh_overlay'):
            self._owner.refresh_overlay()
        self.accept()
