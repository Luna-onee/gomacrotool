from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QComboBox, QPushButton, QCheckBox, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
     QFrame,
)
from PyQt6.QtGui import QPainter, QColor, QBrush, QFont, QPen
from PyQt6.QtCore import Qt

from modules import config_manager as config
from modules import utils
from modules.theme import theme
from modules.macro_engine import macro_engine
from modules import pixel_triggers
from modules.gui.main_window import HOTKEY_OPTIONS
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
#  PixelEditor — Material Design 3 Dialog
# ------------------------------------------------------------------ #
class PixelEditor(QDialog):
    def showEvent(self, event):
        super().showEvent(event)
        from modules.gui.window_helpers import apply_rounded_corners
        apply_rounded_corners(self)

    def __init__(self, parent=None, existing=None, idx=0):
        super().__init__(None)  # no parent — prevents silent crashes
        self._existing = existing
        self._idx = idx
        self._temp_pixels = []
        self._capture_res = None
        self._temp_anchor = []
        self._temp_blocker = []
        self._drag_pos = None
        self._owner = parent     # stored for callbacks, NOT set as Qt parent
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setMinimumSize(640, 680)
        self._init_ui()
        self.resize(680, 720)
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

        title_txt = "Add Pixel Trigger" if not self._idx else "Edit Pixel Trigger"
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

        # Row 1: Name / Action / Match
        top_grid = QGridLayout()
        top_grid.setSpacing(6)
        lbl = QLabel("Name:")
        lbl.setStyleSheet(f"color: {t['textSecondary']}; background: transparent; border: none;")
        top_grid.addWidget(lbl, 0, 0)
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Proc name…")
        top_grid.addWidget(self._name_edit, 0, 1)

        lbl2 = QLabel("Action:")
        lbl2.setStyleSheet(f"color: {t['textSecondary']}; background: transparent; border: none;")
        top_grid.addWidget(lbl2, 0, 2)
        self._action_ddl = QComboBox()
        self._action_ddl.setEditable(True)
        self._action_ddl.addItems(HOTKEY_OPTIONS)
        top_grid.addWidget(self._action_ddl, 0, 3)

        lbl3 = QLabel("Match:")
        lbl3.setStyleSheet(f"color: {t['textSecondary']}; background: transparent; border: none;")
        top_grid.addWidget(lbl3, 0, 4)
        self._match_ddl = QComboBox()
        self._match_ddl.addItems(["All Match", "Any Match"])
        top_grid.addWidget(self._match_ddl, 0, 5)
        top_grid.setColumnStretch(1, 1)
        top_grid.setColumnStretch(3, 1)
        content_layout.addLayout(top_grid)

        # Resolution
        res_row = QHBoxLayout()
        self._res_label = QLabel("--")
        self._res_label.setStyleSheet(f"color: {t['primary']}; background: transparent; border: none; font-size: 9pt;")
        res_row.addWidget(QLabel("Resolution:"))
        res_row.addWidget(self._res_label)
        res_row.addStretch()
        content_layout.addLayout(res_row)

        # Pixels section
        px_header = QLabel("Pixels")
        px_header.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        px_header.setStyleSheet(f"color: {t['textSecondary']}; background: transparent; border: none; text-transform: uppercase; letter-spacing: 0.5px;")
        content_layout.addWidget(px_header)

        px_layout = QHBoxLayout()
        px_layout.setSpacing(8)
        self._px_table = QTableWidget(0, 4)
        self._px_table.setHorizontalHeaderLabels(["X", "Y", "Color", "Var"])
        self._px_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._px_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._px_table.verticalHeader().setVisible(False)
        self._px_table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed)
        for i, w in enumerate([44, 44, 110, 44]):
            self._px_table.setColumnWidth(i, w)
        self._px_table.horizontalHeader().setStretchLastSection(True)
        self._px_table.setMinimumHeight(90)
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
        clear_px_btn = QPushButton("Clear")
        clear_px_btn.setProperty("class", "btn-outlined")
        clear_px_btn.clicked.connect(self._clear_pixels)
        px_btn.addWidget(clear_px_btn)
        px_btn.addStretch()
        px_layout.addLayout(px_btn)
        content_layout.addLayout(px_layout)

        # Mode grid
        mode_grid = QGridLayout()
        mode_grid.setSpacing(6)
        lbl5 = QLabel("Mode:")
        lbl5.setStyleSheet(f"color: {t['textSecondary']}; background: transparent; border: none;")
        mode_grid.addWidget(lbl5, 0, 0)
        self._mode_ddl = QComboBox()
        self._mode_ddl.addItems(["With Macro", "Always"])
        self._mode_ddl.currentTextChanged.connect(self._update_macro_ddl)
        mode_grid.addWidget(self._mode_ddl, 0, 1)
        lbl6 = QLabel("Macro:")
        lbl6.setStyleSheet(f"color: {t['textSecondary']}; background: transparent; border: none;")
        mode_grid.addWidget(lbl6, 0, 2)
        self._macro_ddl = QComboBox()
        self._macro_ddl.setEditable(True)
        macro_names = [m["hotkey"] for m in config.get_macros() if m.get("hotkey")]
        self._macro_ddl.addItems(macro_names)
        mode_grid.addWidget(self._macro_ddl, 0, 3)
        self._inv_chk = QCheckBox("Inverse")
        mode_grid.addWidget(self._inv_chk, 1, 0)
        self._on_chk = QCheckBox("Enabled")
        self._on_chk.setChecked(True)
        mode_grid.addWidget(self._on_chk, 1, 1, 1, 2)
        lbl_var = QLabel("Var (±):")
        lbl_var.setStyleSheet(f"color: {t['textSecondary']}; background: transparent; border: none;")
        mode_grid.addWidget(lbl_var, 1, 3)
        self._var_edit = QLineEdit("10")
        self._var_edit.setFixedWidth(50)
        mode_grid.addWidget(self._var_edit, 1, 4)
        mode_grid.setColumnStretch(3, 1)
        mode_grid.setColumnStretch(4, 1)
        content_layout.addLayout(mode_grid)

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
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)
        content_layout.addLayout(btn_layout)

        card_layout.addWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.addWidget(card)
        self._update_macro_ddl()

    # ------------------------------------------------------------------ #
    #  Data / logic
    # ------------------------------------------------------------------ #
    def _load(self, ex):
        self._name_edit.setText(ex.get("name", ""))
        ak = ex.get("actionKey", ex.get("key", ""))
        idx = self._action_ddl.findText(ak)
        if idx >= 0:
            self._action_ddl.setCurrentIndex(idx)
        else:
            self._action_ddl.setCurrentText(ak)
        self._inv_chk.setChecked(ex.get("inverse", False))
        self._on_chk.setChecked(ex.get("enabled", True))
        match_mode = ex.get("matchMode", "all")
        self._match_ddl.setCurrentIndex(1 if match_mode == "any" else 0)
        first_var = None
        for px in ex.get("pixels", []):
            v = px.get("variation", 10)
            if first_var is None:
                first_var = v
            self._temp_pixels.append({"x": px.get("x", 0), "y": px.get("y", 0),
                                       "color": px.get("color", "0x000000"), "variation": v})
        if first_var is not None:
            self._var_edit.setText(str(first_var))
        self._capture_res = ex.get("captureRes")
        if self._capture_res:
            self._res_label.setText(f"{self._capture_res.get('w','?')}x{self._capture_res.get('h','?')} (captured)")
        else:
            from modules.utils import get_screen_resolution
            cur = get_screen_resolution()
            self._res_label.setText(f"{cur['w']}x{cur['h']} (current)")
        mode = ex.get("triggerMode", "macro")
        self._mode_ddl.setCurrentIndex(1 if mode == "always" else 0)
        self._update_macro_ddl()
        if mode == "macro" and ex.get("macroHotkey"):
            self._macro_ddl.setCurrentText(ex["macroHotkey"])
        self._refresh_px_table()

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

    def _update_macro_ddl(self):
        is_with_macro = self._mode_ddl.currentText() == "With Macro"
        self._macro_ddl.setEnabled(is_with_macro)

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
                self._res_label.setText(f"{self._capture_res['w']}x{self._capture_res['h']} (captured)")
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

    def _save(self):
        n = self._name_edit.text().strip()
        action = self._action_ddl.currentText().strip()
        if not n or not action:
            ThemedMessageBox.information(self, "Validation", "Name and Action are required.")
            return
        if not self._temp_pixels:
            ThemedMessageBox.information(self, "Validation", "Add at least one pixel.")
            return
        if config._get_spec() is None:
            ThemedMessageBox.information(self, "Validation", "Select a Game > Class > Spec first.")
            return

        var = utils.safe_int(self._var_edit.text(), 10)
        var = max(0, var)
        cd = utils.safe_int(1000)
        mode = "always" if self._mode_ddl.currentText() == "Always" else "macro"
        match_mode = "any" if self._match_ddl.currentText() == "Any Match" else "all"

        proc = {
            "name": n,
            "actionKey": action,
            "pixels": [{"x": px["x"], "y": px["y"], "color": px["color"],
                        "variation": var} for px in self._temp_pixels],
            "matchMode": match_mode,
            "triggerMode": mode,
            "macroHotkey": self._macro_ddl.currentText().strip() if mode == "macro" else "",
            "inverse": self._inv_chk.isChecked(),
            "enabled": self._on_chk.isChecked(),
            "cooldown": cd,
            "captureRes": self._capture_res,
        }

        pixels = config.get_pixels()
        if 0 < self._idx <= len(pixels):
            pixels[self._idx - 1] = proc
        else:
            pixels.append(proc)
        config.save()
        if self._owner and hasattr(self._owner, '_refresh_pixel_list'):
            self._owner._refresh_pixel_list()
        if self._owner and hasattr(self._owner, 'refresh_overlay'):
            self._owner.refresh_overlay()
        pixel_triggers.setup()
        self.accept()
