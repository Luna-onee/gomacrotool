from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton,
    QTableWidget, QTableWidgetItem, QAbstractItemView,
     QFrame,
)
from PyQt6.QtGui import QPainter, QColor, QBrush, QFont
from PyQt6.QtCore import Qt

from modules import config_manager as config
from modules import utils
from modules.theme import theme
from modules.gui.nerd_font import ICONS
from modules.gui.message_box import ThemedMessageBox


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
            self._color_hex = str(value)

    def paint(self, painter, option, widget=None):
        painter.save()
        swatch_size = 14
        margin = 3
        swatch_rect = option.rect.adjusted(margin, margin, 0, 0)
        swatch_rect.setWidth(swatch_size)
        swatch_rect.setHeight(min(swatch_size, option.rect.height() - 2 * margin))
        swatch_rect.moveTop(option.rect.top() + (option.rect.height() - swatch_rect.height()) // 2)

        try:
            qc = QColor(self._color_hex)
        except Exception:
            qc = QColor(0, 0, 0)
        painter.fillRect(swatch_rect, QBrush(qc))
        painter.setPen(QColor(theme.get("outline")))
        painter.drawRect(swatch_rect)

        text_rect = option.rect.adjusted(swatch_size + 2 * margin, 0, 0, 0)
        painter.setPen(QColor(theme.get("text")))
        font = option.font
        painter.setFont(font)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._color_hex)
        painter.restore()


class SpecDetectEditor(QDialog):
    def showEvent(self, event):
        super().showEvent(event)
        from modules.gui.window_helpers import apply_rounded_corners
        apply_rounded_corners(self)

    def __init__(self, parent=None):
        super().__init__(None)  # no parent — prevents silent crashes
        self._temp_pixels = []
        self._drag_pos = None
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setMinimumSize(460, 340)
        self._init_ui()
        self.resize(520, 420)
        self._load()

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

        title_lbl = QLabel("Spec Detection")
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

        info = QLabel("Pixels that identify this spec. Auto-detect switches spec when these match.")
        info.setStyleSheet(f"color: {t['textSecondary']}; background: transparent; border: none;")
        info.setWordWrap(True)
        content_layout.addWidget(info)

        match_layout = QHBoxLayout()
        lbl = QLabel("Match:")
        lbl.setStyleSheet(f"color: {t['textSecondary']}; background: transparent; border: none;")
        match_layout.addWidget(lbl)
        self._match_ddl = QComboBox()
        self._match_ddl.addItems(["All Match", "Any Match"])
        match_layout.addWidget(self._match_ddl)
        match_layout.addStretch()
        content_layout.addLayout(match_layout)

        self._res_label = QLabel("")
        self._res_label.setStyleSheet(f"color: {t['primary']}; background: transparent; border: none; font-size: 9pt;")
        content_layout.addWidget(self._res_label)

        px_header = QLabel("Detection Pixels")
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
        self._px_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        for i, w in enumerate([50, 50, 100, 44]):
            self._px_table.setColumnWidth(i, w)
        self._px_table.horizontalHeader().setStretchLastSection(True)
        self._px_table.setMinimumHeight(160)
        px_layout.addWidget(self._px_table, 1)

        px_btn_layout = QVBoxLayout()
        px_btn_layout.setSpacing(6)
        pick_btn = QPushButton("Pick")
        pick_btn.setProperty("class", "btn-filled")
        pick_btn.clicked.connect(self._pick)
        px_btn_layout.addWidget(pick_btn)
        rem_btn = QPushButton("Remove")
        rem_btn.setProperty("class", "btn-outlined")
        rem_btn.clicked.connect(self._remove)
        px_btn_layout.addWidget(rem_btn)
        clear_btn = QPushButton("Clear All")
        clear_btn.setProperty("class", "btn-outlined")
        clear_btn.clicked.connect(self._clear)
        px_btn_layout.addWidget(clear_btn)
        px_btn_layout.addStretch()
        px_layout.addLayout(px_btn_layout)
        content_layout.addLayout(px_layout)

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

    def _load(self):
        spec = config._get_spec()
        if spec is None:
            return
        detect = spec.get("detect")
        if detect:
            for px in detect.get("pixels", []):
                self._temp_pixels.append({
                    "x": px.get("x", 0),
                    "y": px.get("y", 0),
                    "color": px.get("color", "0x000000"),
                    "variation": px.get("variation", 10),
                })
            match_mode = detect.get("matchMode", "all")
            self._match_ddl.setCurrentIndex(1 if match_mode == "any" else 0)
            cr = detect.get("captureRes")
            if cr:
                self._res_label.setText(f"Captured at {cr.get('w', '?')}x{cr.get('h', '?')}")
            else:
                cur = utils.get_screen_resolution()
                self._res_label.setText(f"Current: {cur['w']}x{cur['h']}")
        else:
            cur = utils.get_screen_resolution()
            self._res_label.setText(f"Current: {cur['w']}x{cur['h']}")
        self._refresh_table()

    def _refresh_table(self):
        self._px_table.setRowCount(0)
        for px in self._temp_pixels:
            row = self._px_table.rowCount()
            self._px_table.insertRow(row)
            self._px_table.setItem(row, 0, QTableWidgetItem(str(px["x"])))
            self._px_table.setItem(row, 1, QTableWidgetItem(str(px["y"])))
            self._px_table.setItem(row, 2, ColorSwatchItem(px["color"]))
            self._px_table.setItem(row, 3, QTableWidgetItem(str(px["variation"])))
        self._px_table.resizeColumnsToContents()

    def _pick(self):
        from modules import pixel_picker
        pixel_picker.start(self._on_picked)

    def _on_picked(self, result):
        if result and isinstance(result, dict):
            self._temp_pixels.append({
                "x": result["x"],
                "y": result["y"],
                "color": result["color"],
                "variation": 10,
            })
            if result.get("screenRes"):
                self._res_label.setText(f"Captured at {result['screenRes']['w']}x{result['screenRes']['h']}")
            self._refresh_table()
        self.raise_()
        self.activateWindow()

    def _remove(self):
        row = self._px_table.currentRow()
        if row < 0 or row >= len(self._temp_pixels):
            return
        self._temp_pixels.pop(row)
        self._refresh_table()

    def _clear(self):
        self._temp_pixels.clear()
        self._refresh_table()

    def _save(self):
        spec = config._get_spec()
        if spec is None:
            ThemedMessageBox.information(self, "Validation", "Select a Game > Class > Spec first.")
            return

        match_mode = "any" if self._match_ddl.currentText() == "Any Match" else "all"
        if self._temp_pixels:
            spec["detect"] = {
                "pixels": [dict(px) for px in self._temp_pixels],
                "matchMode": match_mode,
                "captureRes": utils.get_screen_resolution(),
            }
        else:
            spec["detect"] = None

        config.save()
        self.accept()
