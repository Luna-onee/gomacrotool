from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QComboBox, QPushButton, QCheckBox, QLineEdit,
    QTableWidget, QTableWidgetItem, QFrame, QSystemTrayIcon,
     QFileDialog, QHeaderView, QAbstractItemView,
    QApplication, QSpinBox, QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QFont, QAction

from modules import config_manager as config
from modules import utils
from modules import input_handler
from modules.theme import theme
from modules import game_detection
from modules.macro_engine import macro_engine
from modules import pixel_triggers
from modules.gui import material_style
from modules.gui.settings_dialog import SettingsDialog
from modules.gui.nerd_font import ICONS, get_font
from modules.gui.message_box import ThemedMessageBox
from modules.gui.toggle_switch import ToggleSwitch

HOTKEY_OPTIONS = [
    "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12",
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "0",
    "q", "w", "e", "r", "t", "y", "u", "i", "o", "p",
    "a", "s", "d", "f", "g", "h", "j", "k", "l",
    "z", "x", "c", "v", "b", "n", "m",
    "Numpad0", "Numpad1", "Numpad2", "Numpad3", "Numpad4",
    "Numpad5", "Numpad6", "Numpad7", "Numpad8", "Numpad9",
    "NumpadAdd", "NumpadSub", "NumpadMult", "NumpadDiv",
    "Tab", "CapsLock", "Space", "Enter",
    "Insert", "Delete", "Home", "End", "PgUp", "PgDn",
    "Up", "Down", "Left", "Right",
    "^1", "^2", "^3", "^4", "^5",
    "!1", "!2", "!3", "!4", "!5",
    "+1", "+2", "+3", "+4", "+5",
    "^F1", "^F2", "^F3", "^F4", "^F5",
    "!F1", "!F2", "!F3", "!F4", "!F5",
    "XButton1", "XButton2",
]

KEY_OPTIONS = [
    "Down", "Up", "Left", "Right",
    "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12",
    "Home", "End", "PgUp", "PgDn", "Insert", "Delete",
    "Space", "Enter", "Tab", "Escape", "Backspace",
    "Numpad0", "Numpad1", "Numpad2", "Numpad3", "Numpad4",
    "Numpad5", "Numpad6", "Numpad7", "Numpad8", "Numpad9",
    "NumpadEnter", "NumpadAdd", "NumpadSub", "NumpadMult", "NumpadDiv",
    "LButton", "RButton", "MButton", "XButton1", "XButton2",
    "Shift", "Ctrl", "Alt",
    "CapsLock", "ScrollLock", "NumLock",
    "PrintScreen", "Pause",
]



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setMinimumSize(620, 580)
        self.resize(720, 660)
        self._active_tab = 0
        self._ready = False
        self._drag_pos = None
        self._resize_edge = None
        self._resize_margin = 6
        self._init_ui()
        self._refresh_game_list()

    def showEvent(self, event):
        super().showEvent(event)
        from modules.gui.window_helpers import apply_rounded_corners
        apply_rounded_corners(self)

    def _init_ui(self):
        central = QWidget()
        central.setProperty("class", "mainwindow")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title_bar = QFrame()
        title_bar.setProperty("class", "titlebar")
        title_bar.setFixedHeight(38)
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(12, 0, 4, 0)
        tb_layout.setSpacing(4)

        icon_lbl = QLabel(ICONS.POWER)
        icon_lbl.setFont(get_font(12))
        icon_lbl.setProperty("class", "titlebar-icon")
        tb_layout.addWidget(icon_lbl)

        title_lbl = QLabel("Macro Manager")
        title_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title_lbl.setProperty("class", "titlebar-title")
        tb_layout.addWidget(title_lbl)
        tb_layout.addStretch()

        theme_btn = QPushButton(ICONS.SUN if theme.dark_mode else ICONS.MOON)
        theme_btn.setProperty("class", "titlebar-btn")
        theme_btn.setFixedSize(32, 28)
        theme_btn.setToolTip("Toggle Theme")
        theme_btn.clicked.connect(self._toggle_theme)
        tb_layout.addWidget(theme_btn)
        self._theme_btn = theme_btn

        min_btn = QPushButton(ICONS.MINUS)
        min_btn.setProperty("class", "titlebar-btn")
        min_btn.setFixedSize(32, 28)
        min_btn.setToolTip("Minimize")
        min_btn.clicked.connect(self.showMinimized)
        tb_layout.addWidget(min_btn)

        close_btn = QPushButton(ICONS.X)
        close_btn.setProperty("class", "titlebar-close")
        close_btn.setFixedSize(40, 28)
        close_btn.setToolTip("Close")
        close_btn.clicked.connect(self._on_close)
        tb_layout.addWidget(close_btn)

        layout.addWidget(title_bar)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(10, 6, 10, 10)
        body_layout.setSpacing(6)
        layout.addWidget(body)

        l = body_layout

        profile_card = QFrame()
        profile_card.setProperty("class", "card")
        profile_grid = QGridLayout(profile_card)
        profile_grid.setContentsMargins(10, 6, 10, 6)
        profile_grid.setSpacing(4)

        profile_grid.addWidget(self._sec_label("Game:"), 0, 0)
        self._game_ddl = QComboBox()
        self._game_ddl.setEditable(True)
        profile_grid.addWidget(self._game_ddl, 0, 1)
        add_game_btn = QPushButton("Add")
        add_game_btn.setProperty("class", "btn-tonal")
        add_game_btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        add_game_btn.clicked.connect(self._add_game)
        profile_grid.addWidget(add_game_btn, 0, 2)
        del_game_btn = QPushButton("Del")
        del_game_btn.setProperty("class", "btn-outlined")
        del_game_btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        del_game_btn.clicked.connect(self._delete_game)
        profile_grid.addWidget(del_game_btn, 0, 3)

        profile_grid.addWidget(self._sec_label("Class:"), 1, 0)
        self._class_ddl = QComboBox()
        self._class_ddl.setEditable(True)
        profile_grid.addWidget(self._class_ddl, 1, 1)
        add_class_btn = QPushButton("Add")
        add_class_btn.setProperty("class", "btn-tonal")
        add_class_btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        add_class_btn.clicked.connect(self._add_class)
        profile_grid.addWidget(add_class_btn, 1, 2)
        del_class_btn = QPushButton("Del")
        del_class_btn.setProperty("class", "btn-outlined")
        del_class_btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        del_class_btn.clicked.connect(self._delete_class)
        profile_grid.addWidget(del_class_btn, 1, 3)

        profile_grid.addWidget(self._sec_label("Spec:"), 2, 0)
        self._spec_ddl = QComboBox()
        self._spec_ddl.setEditable(True)
        profile_grid.addWidget(self._spec_ddl, 2, 1)
        add_spec_btn = QPushButton("Add")
        add_spec_btn.setProperty("class", "btn-tonal")
        add_spec_btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        add_spec_btn.clicked.connect(self._add_spec)
        profile_grid.addWidget(add_spec_btn, 2, 2)
        del_spec_btn = QPushButton("Del")
        del_spec_btn.setProperty("class", "btn-outlined")
        del_spec_btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        del_spec_btn.clicked.connect(self._delete_spec)
        profile_grid.addWidget(del_spec_btn, 2, 3)

        detect_spec_btn = QPushButton("Detect")
        detect_spec_btn.setProperty("class", "btn-tonal")
        detect_spec_btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        detect_spec_btn.setToolTip("Set detection pixels for auto-spec switching")
        detect_spec_btn.clicked.connect(self._edit_spec_detect)
        profile_grid.addWidget(detect_spec_btn, 2, 4)

        profile_grid.setColumnStretch(1, 1)

        l.addWidget(profile_card)

        self._game_ddl.currentTextChanged.connect(self._on_game_change)
        self._class_ddl.currentTextChanged.connect(self._on_class_change)
        self._spec_ddl.currentTextChanged.connect(self._on_spec_change)

        tab_layout = QHBoxLayout()
        tab_layout.setSpacing(6)
        self._tab_btns = []
        for i, name in enumerate(["Macros", "Procs", "Buffs"]):
            btn = QPushButton(name)
            btn.setProperty("class", "btn-filled" if i == 0 else "btn-tonal")
            btn.setCheckable(True)
            btn.setChecked(i == 0)
            btn.clicked.connect(lambda checked, idx=i: self._switch_tab(idx))
            tab_layout.addWidget(btn)
            self._tab_btns.append(btn)
        l.addLayout(tab_layout)

        self._macro_table = self._create_table(["Key", "Name", "Mode", "Delay", "InterKey", "On"], [70, 180, 80, 70, 80, 50])
        self._pixel_table = self._create_table(["Name", "Action", "Px", "Match", "Mode", "On"], [130, 80, 40, 70, 80, 50])
        self._buff_table = self._create_table(["Name", "Trigger", "Duration", "Action", "Refresh", "On"], [120, 120, 85, 75, 75, 50])

        self._tables = [self._macro_table, self._pixel_table, self._buff_table]
        for t in self._tables:
            l.addWidget(t)

        self._switch_tab(0)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton(ICONS.PLUS + "  Add")
        add_btn.setProperty("class", "btn-filled")
        add_btn.clicked.connect(self._on_add)
        edit_btn = QPushButton(ICONS.PENCIL + "  Edit")
        edit_btn.setProperty("class", "btn-tonal")
        edit_btn.clicked.connect(self._on_edit)
        toggle_btn = QPushButton(ICONS.TOGGLE + "  Toggle")
        toggle_btn.setProperty("class", "btn-tonal")
        toggle_btn.clicked.connect(self._on_toggle)
        del_btn = QPushButton(ICONS.TRASH + "  Delete")
        del_btn.setProperty("class", "btn-outlined")
        del_btn.clicked.connect(self._on_delete)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(toggle_btn)
        btn_layout.addWidget(del_btn)
        l.addLayout(btn_layout)
        self._editor_btns = [add_btn, edit_btn, del_btn]

        # ---- Settings bar (clean) ----
        settings_bar = QHBoxLayout()
        settings_bar.setSpacing(8)

        self._settings_info = QLabel()
        self._settings_info.setStyleSheet("color: #A8949C; background: transparent; border: none; font-size: 8pt;")
        settings_bar.addWidget(self._settings_info)
        settings_bar.addStretch()

        settings_btn = QPushButton(ICONS.COG + "  Settings")
        settings_btn.setProperty("class", "btn-tonal")
        settings_btn.setToolTip("Open settings (overlay position, toggle key, etc.)")
        settings_btn.clicked.connect(self._open_settings)
        settings_bar.addWidget(settings_btn)

        l.addLayout(settings_bar)
        self._refresh_settings_info()

        self._status_label = QLabel("Ready | High-Precision Timer Active")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet(f"color: {theme.get('primary')}; padding: 4px;")
        l.addWidget(self._status_label)

        self._ready = True

    def _on_close(self):
        self.hide()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            edge = self._edge_at(e.pos())
            if edge:
                self._resize_edge = edge
                self._resize_start_geo = self.geometry()
                self._resize_start_pos = e.globalPosition().toPoint()
            else:
                title_bar = self.centralWidget().layout().itemAt(0).widget()
                if title_bar and title_bar.geometry().contains(e.pos()):
                    self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos is not None:
            self.move(e.globalPosition().toPoint() - self._drag_pos)
        elif self._resize_edge is not None:
            self._do_resize(e.globalPosition().toPoint())
        else:
            edge = self._edge_at(e.pos())
            cursor = Qt.CursorShape.ArrowCursor
            if edge in ('top', 'bottom'): cursor = Qt.CursorShape.SizeVerCursor
            elif edge in ('left', 'right'): cursor = Qt.CursorShape.SizeHorCursor
            elif edge in ('top-left', 'bottom-right'): cursor = Qt.CursorShape.SizeFDiagCursor
            elif edge in ('top-right', 'bottom-left'): cursor = Qt.CursorShape.SizeBDiagCursor
            self.setCursor(cursor)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None
        self._resize_edge = None

    def mouseDoubleClickEvent(self, e):
        title_bar = self.centralWidget().layout().itemAt(0).widget()
        if title_bar and title_bar.geometry().contains(e.pos()):
            if self.isMaximized():
                self.showNormal()
            else:
                self.showMaximized()

    def _edge_at(self, pos):
        m = self._resize_margin
        r = self.rect()
        top = pos.y() < m
        bottom = pos.y() > r.height() - m
        left = pos.x() < m
        right = pos.x() > r.width() - m
        if top and left: return 'top-left'
        if top and right: return 'top-right'
        if bottom and left: return 'bottom-left'
        if bottom and right: return 'bottom-right'
        if top: return 'top'
        if bottom: return 'bottom'
        if left: return 'left'
        if right: return 'right'
        return None

    def _do_resize(self, pos):
        delta = pos - self._resize_start_pos
        geo = self._resize_start_geo.__class__(self._resize_start_geo)
        edge = self._resize_edge
        if 'left' in edge:
            geo.setLeft(geo.left() + delta.x())
        if 'right' in edge:
            geo.setRight(geo.right() + delta.x())
        if 'top' in edge:
            geo.setTop(geo.top() + delta.y())
        if 'bottom' in edge:
            geo.setBottom(geo.bottom() + delta.y())
        if geo.width() < self.minimumWidth():
            if 'left' in edge: geo.setLeft(geo.right() - self.minimumWidth())
            else: geo.setRight(geo.left() + self.minimumWidth())
        if geo.height() < self.minimumHeight():
            if 'top' in edge: geo.setTop(geo.bottom() - self.minimumHeight())
            else: geo.setBottom(geo.top() + self.minimumHeight())
        self.setGeometry(geo)

    def _sec_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {theme.get('textSecondary')}; background: transparent; border: none;")
        return lbl

    def _create_table(self, headers, widths):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(True)
        table.setMinimumHeight(200)
        for i, w in enumerate(widths):
            table.setColumnWidth(i, w)
        table.horizontalHeader().setStretchLastSection(True)
        return table

    def _switch_tab(self, idx):
        self._active_tab = idx
        for i, btn in enumerate(self._tab_btns):
            btn.setProperty("class", "btn-filled" if i == idx else "btn-tonal")
            btn.setChecked(i == idx)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        for i, t in enumerate(self._tables):
            t.setVisible(i == idx)

    def _current_table(self):
        return self._tables[self._active_tab]

    def _on_add(self):
        try:
            if self._active_tab == 0:
                from modules.gui.macro_editor import MacroEditor
                MacroEditor(self).exec()
            elif self._active_tab == 1:
                if config._get_spec() is None:
                    ThemedMessageBox.information(self, "Validation", "Select a Game > Class > Spec first.")
                    return
                from modules.gui.pixel_editor import PixelEditor
                PixelEditor(self).exec()
            elif self._active_tab == 2:
                if config._get_spec() is None:
                    ThemedMessageBox.information(self, "Validation", "Select a Game > Class > Spec first.")
                    return
                from modules.gui.buff_editor import BuffEditor
                BuffEditor(self).exec()
        except Exception as e:
            import traceback
            traceback.print_exc()
            ThemedMessageBox.critical(self, "Error", str(e))

    def _on_edit(self):
        table = self._current_table()
        row = table.currentRow()
        if row < 0:
            ThemedMessageBox.information(self, "No Selection", "Select an item in the list first.")
            return
        try:
            if self._active_tab == 0:
                from modules.gui.macro_editor import MacroEditor
                macros = config.get_macros()
                if row < len(macros):
                    MacroEditor(self, macros[row], row + 1).exec()
            elif self._active_tab == 1:
                from modules.gui.pixel_editor import PixelEditor
                pixels = config.get_pixels()
                if row < len(pixels):
                    PixelEditor(self, pixels[row], row + 1).exec()
            elif self._active_tab == 2:
                from modules.gui.buff_editor import BuffEditor
                buffs = config.get_buffs()
                if row < len(buffs):
                    BuffEditor(self, buffs[row], row + 1).exec()
        except Exception as e:
            import traceback
            traceback.print_exc()
            ThemedMessageBox.critical(self, "Error", str(e))

    def _on_delete(self):
        table = self._current_table()
        row = table.currentRow()
        if row < 0:
            return
        if ThemedMessageBox.question(self, "Confirm", "Delete?") != ThemedMessageBox.Yes:
            return

        try:
            if self._active_tab == 0:
                macros = config.get_macros()
                if row < len(macros):
                    macros.pop(row)
            elif self._active_tab == 1:
                pixels = config.get_pixels()
                if row < len(pixels):
                    pixels.pop(row)
            elif self._active_tab == 2:
                buffs = config.get_buffs()
                if row < len(buffs):
                    buffs.pop(row)
        except Exception as e:
            ThemedMessageBox.warning(self, "Error", f"Delete failed: {e}")
            return

        config.save()
        self._refresh_all_lists()
        macro_engine.setup()
        pixel_triggers.setup()

    def _on_toggle(self):
        if self._active_tab == 0:
            table = self._macro_table
            row = table.currentRow()
            if row < 0:
                return
            macros = config.get_macros()
            if row < len(macros):
                macros[row]["enabled"] = not macros[row].get("enabled", True)
                config.save()
                self._refresh_macro_list()
                macro_engine.setup()
        elif self._active_tab == 1:
            table = self._pixel_table
            row = table.currentRow()
            if row < 0:
                return
            pixels = config.get_pixels()
            if row < len(pixels):
                pixels[row]["enabled"] = not pixels[row].get("enabled", True)
                config.save()
                self._refresh_pixel_list()
                pixel_triggers.setup()
        elif self._active_tab == 2:
            table = self._buff_table
            row = table.currentRow()
            if row < 0:
                return
            buffs = config.get_buffs()
            if row < len(buffs):
                buffs[row]["enabled"] = not buffs[row].get("enabled", True)
                config.save()
                self._refresh_buff_list()

    def _refresh_all_lists(self):
        self._refresh_macro_list()
        self._refresh_pixel_list()
        self._refresh_buff_list()
        self._update_status()

    def refresh_overlay(self):
        app_inst = QApplication.instance()
        if app_inst and hasattr(app_inst, '_overlay'):
            app_inst._overlay.refresh_macros()

    def _refresh_game_list(self):
        if not self._ready:
            return
        self._game_ddl.blockSignals(True)
        self._game_ddl.clear()
        games = list(config.data.get("games", {}).keys())
        self._game_ddl.addItems(games)
        active = config.data.get("activeGame", "")
        if active and active in games:
            self._game_ddl.setCurrentText(active)
        self._game_ddl.blockSignals(False)
        self._on_game_change()

    def _on_game_change(self):
        if not self._ready:
            return
        config.data["activeGame"] = self._game_ddl.currentText()

        self._class_ddl.blockSignals(True)
        self._class_ddl.clear()
        g_name = config.data.get("activeGame", "")
        classes = []
        if g_name and g_name in config.data.get("games", {}):
            classes = list(config.data["games"][g_name].get("classes", {}).keys())
        self._class_ddl.addItems(classes)
        active = config.data.get("activeClass", "")
        if active and active in classes:
            self._class_ddl.setCurrentText(active)
        self._class_ddl.blockSignals(False)
        self._on_class_change()

    def _on_class_change(self):
        if not self._ready:
            return
        config.data["activeClass"] = self._class_ddl.currentText()

        self._spec_ddl.blockSignals(True)
        self._spec_ddl.clear()
        g_name = config.data.get("activeGame", "")
        c_name = config.data.get("activeClass", "")
        specs = []
        try:
            c = config.data["games"][g_name]["classes"][c_name]
            specs = list(c.get("specs", {}).keys())
        except (KeyError, TypeError):
            pass
        self._spec_ddl.addItems(specs)
        active = config.data.get("activeSpec", "")
        if active and active in specs:
            self._spec_ddl.setCurrentText(active)
        self._spec_ddl.blockSignals(False)
        self._on_spec_change()

    def _on_spec_change(self):
        if not self._ready:
            return
        config.data["activeSpec"] = self._spec_ddl.currentText()
        self._refresh_macro_list()
        self._refresh_pixel_list()
        self._refresh_buff_list()
        self._update_status()
        config.save()
        macro_engine.setup()
        pixel_triggers.setup()

    def _make_toggle_cell(self, checked, callback):
        """Create a centered toggle switch for a table cell."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        switch = ToggleSwitch(checked=checked, size=16)
        switch.toggled.connect(callback)
        layout.addWidget(switch)
        return container

    def _on_macro_toggle(self, row, checked):
        macros = config.get_macros()
        if row < len(macros):
            macros[row]["enabled"] = checked
            config.save()
            macro_engine.setup()
            self._update_status()

    def _on_pixel_toggle(self, row, checked):
        pixels = config.get_pixels()
        if row < len(pixels):
            pixels[row]["enabled"] = checked
            config.save()
            pixel_triggers.setup()
            self._update_status()

    def _on_buff_toggle(self, row, checked):
        buffs = config.get_buffs()
        if row < len(buffs):
            buffs[row]["enabled"] = checked
            config.save()
            self._update_status()

    def _refresh_macro_list(self):
        self._macro_table.setRowCount(0)
        macros = config.get_macros()
        for row, m in enumerate(macros):
            self._macro_table.insertRow(row)
            self._macro_table.setItem(row, 0, QTableWidgetItem(m.get("hotkey", "")))
            self._macro_table.setItem(row, 1, QTableWidgetItem(m.get("name", "")))
            mode = "Hold" if m.get("holdMode", False) else "Press"
            self._macro_table.setItem(row, 2, QTableWidgetItem(mode))
            self._macro_table.setItem(row, 3, QTableWidgetItem(str(m.get("delay", 0)) + "ms"))
            ikd = m.get("interKeyDelay", 0)
            self._macro_table.setItem(row, 4, QTableWidgetItem(str(ikd) + "ms"))
            enabled = m.get("enabled", True)
            toggle = self._make_toggle_cell(enabled, lambda c, r=row: self._on_macro_toggle(r, c))
            self._macro_table.setCellWidget(row, 5, toggle)
            self._macro_table.setRowHeight(row, 24)
        self._macro_table.resizeColumnsToContents()
        for i in range(self._macro_table.columnCount() - 1):
            self._macro_table.setColumnWidth(i, self._macro_table.columnWidth(i) + 8)
        self._macro_table.horizontalHeader().setStretchLastSection(True)

    def _refresh_pixel_list(self):
        self._pixel_table.setRowCount(0)
        pixels = config.get_pixels()
        for row, t in enumerate(pixels):
            self._pixel_table.insertRow(row)
            self._pixel_table.setItem(row, 0, QTableWidgetItem(t.get("name", "")))
            self._pixel_table.setItem(row, 1, QTableWidgetItem(t.get("actionKey", t.get("key", ""))))
            px_count = len(t.get("pixels", []))
            self._pixel_table.setItem(row, 2, QTableWidgetItem(str(px_count)))
            match = "Any" if t.get("matchMode") == "any" else "All"
            self._pixel_table.setItem(row, 3, QTableWidgetItem(match))
            mode = "Macro: " + t.get("macroHotkey", "") if t.get("triggerMode") == "macro" else "Always"
            self._pixel_table.setItem(row, 4, QTableWidgetItem(mode))
            enabled = t.get("enabled", True)
            toggle = self._make_toggle_cell(enabled, lambda c, r=row: self._on_pixel_toggle(r, c))
            self._pixel_table.setCellWidget(row, 5, toggle)
            self._pixel_table.setRowHeight(row, 24)
        self._pixel_table.resizeColumnsToContents()
        for i in range(self._pixel_table.columnCount() - 1):
            self._pixel_table.setColumnWidth(i, self._pixel_table.columnWidth(i) + 8)
        self._pixel_table.horizontalHeader().setStretchLastSection(True)

    def _refresh_buff_list(self):
        self._buff_table.setRowCount(0)
        buffs = config.get_buffs()
        for row, b in enumerate(buffs):
            self._buff_table.insertRow(row)
            self._buff_table.setItem(row, 0, QTableWidgetItem(b.get("name", "")))

            is_pixel = b.get("triggerType") == "pixel"
            if is_pixel:
                px_count = len(b.get("triggerPixels", []))
                match = b.get("triggerMatchMode", "all")
                trigger_str = f"Px:{px_count}({match[0]})"
            else:
                keys = b.get("watchKeys", [])
                trigger_str = ",".join(keys) if keys else "—"
            self._buff_table.setItem(row, 1, QTableWidgetItem(trigger_str))
            self._buff_table.setItem(row, 2, QTableWidgetItem(str(b.get("duration", 0)) + "ms"))
            self._buff_table.setItem(row, 3, QTableWidgetItem(b.get("actionKey", "")))
            self._buff_table.setItem(row, 4, QTableWidgetItem(b.get("onRefresh", "reset")))
            enabled = b.get("enabled", True)
            toggle = self._make_toggle_cell(enabled, lambda c, r=row: self._on_buff_toggle(r, c))
            self._buff_table.setCellWidget(row, 5, toggle)
            self._buff_table.setRowHeight(row, 24)
        self._buff_table.resizeColumnsToContents()
        for i in range(self._buff_table.columnCount() - 1):
            self._buff_table.setColumnWidth(i, self._buff_table.columnWidth(i) + 8)
        self._buff_table.horizontalHeader().setStretchLastSection(True)

    def _update_status(self):
        g = config.data.get("activeGame", "")
        c = config.data.get("activeClass", "")
        s = config.data.get("activeSpec", "")
        mc = len(config.get_macros())
        pc = len(config.get_pixels())
        bc = len(config.get_buffs())
        game_active = game_detection.window_active
        only = config.data["settings"].get("onlyInGame", True)
        dot = ICONS.CIRCLE if any(macro_engine.running.values()) else ICONS.CIRCLE_O
        st = ICONS.CHECK if (game_active or not only) else ICONS.X

        from modules.macro_engine import macros_paused
        toggle_key = config.data["settings"].get("toggleKey", "ScrollLock")
        is_on = not macros_paused
        toggle_icon = ICONS.TOGGLE_ON if is_on else ICONS.TOGGLE_OFF

        parts = []
        if g and c and s:
            parts.append(f"{dot} {g}>{c}>{s}")
        else:
            parts.append("Select profile")
        parts.append(toggle_icon)
        parts.append(f"{mc}M {pc}P {bc}B")
        if only:
            parts.append(f"Game{'OK' if game_active else 'NO'}{st}")
        else:
            parts.append("Always")
        m_on = sum(1 for m in config.get_macros() if m.get("enabled", True))
        p_on = sum(1 for p in config.get_pixels() if p.get("enabled", True))
        b_on = sum(1 for b in config.get_buffs() if b.get("enabled", True))
        parts.append(f"{m_on}/{mc} {p_on}/{pc} {b_on}/{bc}")
        parts.append(f"HK:{len(macro_engine.profile)}")
        err = game_detection.get_status()
        if err and only:
            parts.append(err)
        self._status_label.setText(" | ".join(parts))

    def _open_settings(self):
        dlg = SettingsDialog()
        if dlg.exec() == SettingsDialog.DialogCode.Accepted:
            self._refresh_settings_info()
            self._update_status()

    def _refresh_settings_info(self):
        s = config.data.get("settings", {})
        parts = []
        parts.append(f"Toggle: {s.get('toggleKey', 'ScrollLock')}")
        parts.append(f"Delay: {s.get('defaultDelay', 50)}ms")
        parts.append(f"Pixel/s: {s.get('pixelCheckRate', 250)}")
        if s.get('onlyInGame', True):
            parts.append("Game only")
        if s.get('autoDetectGame', True):
            parts.append("Auto-detect")
        self._settings_info.setText("  |  ".join(parts))

    def _add_game(self):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout
        dlg = QDialog(self)
        dlg.setWindowTitle("Add Game")
        dlg.setMinimumWidth(250)
        layout = QFormLayout(dlg)
        name_edit = QLineEdit()
        path_edit = QLineEdit()
        browse_btn = QPushButton("...")
        browse_btn.setFixedWidth(40)

        def browse():
            f, _ = QFileDialog.getOpenFileName(dlg, "Select Game Exe", "", "*.exe")
            if f:
                path_edit.setText(f)

        browse_btn.clicked.connect(browse)
        path_layout = QHBoxLayout()
        path_layout.addWidget(path_edit)
        path_layout.addWidget(browse_btn)

        layout.addRow("Name:", name_edit)
        layout.addRow("Exe:", path_layout)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Add")
        save_btn.setProperty("class", "btn-filled")
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("class", "btn-text")
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

        cancel_btn.clicked.connect(dlg.reject)

        def save():
            n = name_edit.text().strip()
            if not n:
                return
            p = path_edit.text().strip()
            if n not in config.data["games"]:
                config.data["games"][n] = {"path": p, "classes": {}}
            else:
                config.data["games"][n]["path"] = p
            config.save()
            self._refresh_game_list()
            self._game_ddl.setCurrentText(n)
            dlg.accept()

        save_btn.clicked.connect(save)
        dlg.exec()

    def _delete_game(self):
        n = self._game_ddl.currentText()
        if not n:
            return
        if ThemedMessageBox.question(self, "Confirm", f"Delete '{n}'?") == ThemedMessageBox.Yes:
            config.data["games"].pop(n, None)
            config.data["activeGame"] = ""
            config.data["activeClass"] = ""
            config.data["activeSpec"] = ""
            config.save()
            self._refresh_game_list()

    def _add_class(self):
        gn = self._game_ddl.currentText()
        if not gn:
            return
        from PyQt6.QtWidgets import QDialog, QFormLayout
        dlg = QDialog(self)
        dlg.setWindowTitle("Add Class")
        dlg.setMinimumWidth(200)
        layout = QFormLayout(dlg)
        name_edit = QLineEdit()
        layout.addRow("Name:", name_edit)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Add")
        save_btn.setProperty("class", "btn-filled")
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("class", "btn-text")
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

        cancel_btn.clicked.connect(dlg.reject)

        def save():
            n = name_edit.text().strip()
            if not n:
                return
            try:
                classes = config.data["games"][gn]["classes"]
            except KeyError:
                return
            if n not in classes:
                classes[n] = {"specs": {}}
            config.save()
            self._on_game_change()
            self._class_ddl.setCurrentText(n)
            dlg.accept()

        save_btn.clicked.connect(save)
        dlg.exec()

    def _delete_class(self):
        gn = self._game_ddl.currentText()
        cn = self._class_ddl.currentText()
        if not gn or not cn:
            return
        if ThemedMessageBox.question(self, "Confirm", f"Delete '{cn}'?") == ThemedMessageBox.Yes:
            try:
                config.data["games"][gn]["classes"].pop(cn, None)
            except KeyError:
                pass
            config.data["activeClass"] = ""
            config.data["activeSpec"] = ""
            config.save()
            self._on_game_change()

    def _add_spec(self):
        gn = self._game_ddl.currentText()
        cn = self._class_ddl.currentText()
        if not gn or not cn:
            return
        from PyQt6.QtWidgets import QDialog, QFormLayout
        dlg = QDialog(self)
        dlg.setWindowTitle("Add Spec")
        dlg.setMinimumWidth(200)
        layout = QFormLayout(dlg)
        name_edit = QLineEdit()
        layout.addRow("Name:", name_edit)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Add")
        save_btn.setProperty("class", "btn-filled")
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("class", "btn-text")
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

        cancel_btn.clicked.connect(dlg.reject)

        def save():
            n = name_edit.text().strip()
            if not n:
                return
            try:
                specs = config.data["games"][gn]["classes"][cn]["specs"]
            except KeyError:
                return
            if n not in specs:
                specs[n] = {"macros": [], "pixelTriggers": [], "buffTimers": []}
            config.save()
            self._on_class_change()
            self._spec_ddl.setCurrentText(n)
            dlg.accept()

        save_btn.clicked.connect(save)
        dlg.exec()

    def _edit_spec_detect(self):
        if config._get_spec() is None:
            ThemedMessageBox.information(self, "Validation", "Select a Game > Class > Spec first.")
            return
        from modules.gui.spec_detect_editor import SpecDetectEditor
        SpecDetectEditor(self).exec()

    def _delete_spec(self):
        gn = self._game_ddl.currentText()
        cn = self._class_ddl.currentText()
        sn = self._spec_ddl.currentText()
        if not gn or not cn or not sn:
            return
        if ThemedMessageBox.question(self, "Confirm", f"Delete '{sn}'?") == ThemedMessageBox.Yes:
            try:
                config.data["games"][gn]["classes"][cn]["specs"].pop(sn, None)
            except KeyError:
                pass
            config.data["activeSpec"] = ""
            config.save()
            self._on_class_change()

    def _toggle_theme(self):
        theme.set_dark_mode(not theme.dark_mode)
        config.save()
        material_style.apply_theme(QApplication.instance())
        self._theme_btn.setText(chr(9788) if theme.dark_mode else chr(9790))
        self._status_label.setStyleSheet(f"color: {theme.get('primary')}; padding: 4px;")
        self._update_status()

        app_inst = QApplication.instance()
        if app_inst and hasattr(app_inst, '_overlay'):
            app_inst._overlay.refresh_macros()

    def auto_detect_game(self):
        result = game_detection.auto_detect()
        if result and result[0] == "game_detected":
            name = result[1]
            self._game_ddl.blockSignals(True)
            self._game_ddl.setCurrentText(name)
            self._game_ddl.blockSignals(False)
            self._on_game_change()

        spec_name = pixel_triggers.check_spec_detect()
        if spec_name and spec_name != config.data.get("activeSpec", ""):
            self._spec_ddl.blockSignals(True)
            self._spec_ddl.setCurrentText(spec_name)
            self._spec_ddl.blockSignals(False)
            self._on_spec_change()

    def closeEvent(self, a0):
        a0.ignore()
        self.hide()
