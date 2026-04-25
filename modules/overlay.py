from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame, QSizePolicy
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QGuiApplication

from modules import config_manager as config
from modules.macro_engine import macro_engine
from modules.buff_engine import buff_engine
from modules.theme import theme
from modules.gui.toggle_switch import ToggleSwitch
from modules.gui.nerd_font import ICONS, get_font

# Windows virtual-key code map for toggle hotkeys
_TOGGLE_VK_MAP = {
    "ScrollLock": 0x91,
    "CapsLock": 0x14,
    "NumLock": 0x90,
    "Pause": 0x13,
    "PrintScreen": 0x2C,
    "Insert": 0x2D,
    "Delete": 0x2E,
    **{f"F{i}": 0x6F + i for i in range(1, 13)},  # F1=0x70 ... F12=0x7B
}


def _dbg(action, detail=None):
    try:
        from modules.debug_server import log
        log("overlay", action, detail)
    except Exception:
        pass


_instance = None


# ------------------------------------------------------------------ #
#  M3 Status Dot — filled circle indicator
# ------------------------------------------------------------------ #
class StatusDot(QWidget):
    def __init__(self, parent=None, color="#9DD5B8", size=8):
        super().__init__(parent)
        self._color = QColor(color)
        self._size = size
        self.setFixedSize(size + 2, size + 2)

    def set_color(self, color):
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._color.setAlpha(220)
        p.setBrush(QBrush(self._color))
        p.setPen(Qt.PenStyle.NoPen)
        cx = self.width() // 2
        cy = self.height() // 2
        p.drawEllipse(cx - self._size // 2, cy - self._size // 2, self._size, self._size)
        p.end()


# ------------------------------------------------------------------ #
#  M3 Linear Progress Bar for buff timers
# ------------------------------------------------------------------ #
class M3ProgressBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 0.0
        self._bar_color = QColor("#9DD5B8")
        self.setFixedHeight(3)
        self.setMinimumWidth(60)

    def set_progress(self, progress, bar_color=None):
        self._progress = max(0.0, min(1.0, progress))
        if bar_color:
            self._bar_color = QColor(bar_color)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = theme.colors()
        # Track / background
        bg = QColor(t.get("outlineVariant", "#4D434B"))
        bg.setAlpha(80)
        p.setBrush(QBrush(bg))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(self.rect(), 2, 2)
        # Active chunk
        if self._progress > 0:
            bar_w = int(self.width() * self._progress)
            bar_rect = self.rect().adjusted(0, 0, -(self.width() - bar_w), 0)
            self._bar_color.setAlpha(200)
            p.setBrush(QBrush(self._bar_color))
            p.drawRoundedRect(bar_rect, 2, 2)
        p.end()


# ------------------------------------------------------------------ #
#  Overlay Window — Material Design 3 surface-elevation card
# ------------------------------------------------------------------ #
class OverlayWindow(QWidget):
    def __init__(self):
        global _instance
        if _instance is not None:
            try:
                _instance._destroyed = True
                _instance._buff_update_timer.stop()
                buff_engine.unregister_callback(_instance._on_buff_event)
            except Exception as e:
                print(f"[overlay] cleanup old instance error: {e}")
            try:
                _instance.close()
                _instance.deleteLater()
            except Exception:
                pass
        _instance = self

        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)

        self._apply_settings()
        self._position_overlay()

        self._destroyed = False
        self._toggle_on = True
        self._toggle_key = config.data.get("settings", {}).get("toggleKey", "ScrollLock")
        self._drag_pos = None
        self._dragging = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)
        layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinAndMaxSize)

        # ── Drag handle (invisible top strip for repositioning) ───
        self._drag_handle = QFrame()
        self._drag_handle.setFixedHeight(6)
        self._drag_handle.setStyleSheet("background: transparent; border: none;")
        self._drag_handle.setCursor(Qt.CursorShape.OpenHandCursor)
        self._drag_handle.setToolTip("Drag to move overlay  |  Hold Shift and drag anywhere")
        layout.addWidget(self._drag_handle)

        # ── Header row ──────────────────────────────────────────
        header = QHBoxLayout()
        header.setSpacing(6)

        self._status_dot = StatusDot(color="#9DD5B8", size=7)
        header.addWidget(self._status_dot)

        self._toggle_switch = ToggleSwitch(checked=True, size=22)
        self._toggle_switch.toggled.connect(self._on_overlay_toggle)
        header.addWidget(self._toggle_switch)

        header.addStretch()

        self._game_indicator = QLabel()
        self._game_indicator.setFont(QFont("Segoe UI", 8))
        self._game_indicator.setStyleSheet("background: transparent; border: none;")
        header.addWidget(self._game_indicator)

        self._profile_label = QLabel("")
        self._profile_label.setFont(QFont("Segoe UI", 7))
        self._profile_label.setStyleSheet("background: transparent; border: none; color: #A8949C;")
        header.addWidget(self._profile_label)

        layout.addLayout(header)

        # ── Separator ───────────────────────────────────────────
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #4D434B; border: none; margin: 2px 0px;")
        layout.addWidget(sep)

        # ── Dynamic content ─────────────────────────────────────
        self._macro_lines = []
        self._proc_lines = []
        self._buff_lines = []
        self._buff_bars = {}
        self._dynamic_widgets = []
        self._last_buff_state = {}

        self._rebuild_lines()

        self._buff_update_timer = QTimer(self)
        self._buff_update_timer.timeout.connect(self._update_buff_timers)
        self._buff_update_timer.start(100)

        # Debounced update timer
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._flush_update)

        buff_engine.register_callback(self._on_buff_event)

        self._update_pending = False
        self._do_update()

        _dbg("init", {
            "macros": len(self._macro_lines),
            "procs": len(self._proc_lines),
            "buffs": len(self._buff_lines),
        })

    # ------------------------------------------------------------------ #
    #  Rebuild dynamic content sections
    # ------------------------------------------------------------------ #
    def _make_section_header(self, title):
        lbl = QLabel(title)
        lbl.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #A8949C; background: transparent; border: none; text-transform: uppercase; letter-spacing: 0.8px;")
        return lbl

    def _make_sep(self):
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #4D434B; border: none; margin: 3px 0px;")
        return sep

    def _make_section(self, title, items_data, target_list, with_bars=False):
        lbl = self._make_section_header(title)
        self.layout().addWidget(lbl)
        self._dynamic_widgets.append(lbl)
        target_list.clear()

        for item in items_data:
            name = item.get("name", "")
            row = QWidget()
            row.setStyleSheet("background: transparent; border: none;")
            row_layout = QVBoxLayout(row)
            row_layout.setSpacing(0)
            row_layout.setContentsMargins(0, 1, 0, 1)

            line = QLabel(name)
            line.setFont(QFont("Segoe UI", 8))
            line.setStyleSheet("color: #EDE0E4; background: transparent; border: none;")
            row_layout.addWidget(line)
            target_list.append((item, line))

            if with_bars:
                bar = M3ProgressBar(self)
                bar.setVisible(False)
                row_layout.addWidget(bar)
                self._buff_bars[name] = bar
                self._dynamic_widgets.append(bar)

            self._dynamic_widgets.append(line)
            self.layout().addWidget(row)
            self._dynamic_widgets.append(row)

    def _rebuild_lines(self):
        while self.layout().count() > 3:   # keep header + sep
            item = self.layout().takeAt(3)
            if item:
                w = item.widget()
                if w:
                    w.deleteLater()
                elif item.layout():
                    item.layout().setParent(None)
        self._dynamic_widgets.clear()
        self._macro_lines.clear()
        self._proc_lines.clear()
        self._buff_lines.clear()
        self._buff_bars.clear()
        self._last_buff_state.clear()

        macros = config.get_macros()
        procs = config.get_pixels()
        buffs = config.get_buffs()

        if macros:
            self._make_section("Macros", macros, self._macro_lines)
        if procs:
            sep = self._make_sep()
            self.layout().addWidget(sep)
            self._dynamic_widgets.append(sep)
            self._make_section("Procs", procs, self._proc_lines)
        if buffs:
            sep = self._make_sep()
            self.layout().addWidget(sep)
            self._dynamic_widgets.append(sep)
            self._make_section("Buffs", buffs, self._buff_lines, with_bars=True)

        _dbg("rebuild_lines", {
            "macros": len(self._macro_lines),
            "procs": len(self._proc_lines),
            "buffs": len(self._buff_lines),
        })

    # ------------------------------------------------------------------ #
    #  Refresh
    # ------------------------------------------------------------------ #
    def notify(self):
        if self._destroyed:
            return
        self._update_pending = True
        # Debounce: if timer is already running, it will fire once after 50ms
        if not self._update_timer.isActive():
            self._update_timer.start(50)

    def _flush_update(self):
        if self._destroyed:
            return
        if self._update_pending:
            self._update_pending = False
            self._do_update()

    def closeEvent(self, event):
        self._destroyed = True
        self._update_timer.stop()
        self._buff_update_timer.stop()
        try:
            buff_engine.unregister_callback(self._on_buff_event)
        except Exception:
            pass
        event.accept()

    # ------------------------------------------------------------------ #
    #  Paint — M3 surface card with tonal border
    # ------------------------------------------------------------------ #
    def paintEvent(self, a0):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        t = theme.colors()
        # Surface color from theme
        surf = QColor(t.get("surfaceContainerLow", "#1F191C"))
        surf.setAlpha(235)
        p.setBrush(QBrush(surf))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(self.rect(), 12, 12)

        # Subtle outline around the entire card
        outline = QColor(t.get("outline", "#938F99"))
        outline.setAlpha(60)
        p.setPen(QPen(outline, 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 11, 11)

        # Left accent strip — filled rounded rect, narrow
        if self._toggle_on:
            accent = QColor(t.get("success", "#9DD5B8"))
        else:
            accent = QColor(t.get("error", "#F2B8B5"))
        accent.setAlpha(180)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(accent))
        strip = self.rect().adjusted(2, 6, -self.width() + 6, -6)
        p.drawRoundedRect(strip, 3, 3)
        p.end()

    # ------------------------------------------------------------------ #
    #  Update display
    # ------------------------------------------------------------------ #
    def _do_update(self):
        t = theme.colors()
        text_c  = t.get("text", "#EDE0E4")
        text_sec = t.get("textSecondary", "#A8949C")
        success = t.get("success", "#9DD5B8")
        error   = t.get("error", "#F2B8B5")
        accent  = success if self._toggle_on else error

        from modules import game_detection
        game_active = game_detection.window_active
        only = config.data.get("settings", {}).get("onlyInGame", True)
        game_ok = game_active or not only

        # Header dot + toggle switch
        self._status_dot.set_color(accent)
        self._toggle_switch.setChecked(self._toggle_on)

        # Game indicator dot
        if game_ok:
            self._game_indicator.setText(ICONS.CIRCLE)
            self._game_indicator.setStyleSheet(f"color: {success}; background: transparent; border: none; font-size: 7pt;")
        else:
            self._game_indicator.setText(ICONS.CIRCLE)
            self._game_indicator.setStyleSheet(f"color: {error}; background: transparent; border: none; font-size: 7pt;")

        # Profile label
        g = config.data.get("activeGame", "")
        c = config.data.get("activeClass", "")
        s = config.data.get("activeSpec", "")
        if g and c and s:
            self._profile_label.setText(f"{c} · {s}")
        elif g:
            self._profile_label.setText(g)
        else:
            self._profile_label.setText("")

        # Item rows
        def update_items(items, check_running_fn):
            for item, lbl in items:
                enabled = item.get("enabled", True)
                running = check_running_fn(item)
                if not self._toggle_on or not enabled:
                    color = text_sec
                    prefix = ICONS.CIRCLE_O + " "
                elif running:
                    color = accent
                    prefix = ICONS.CIRCLE + " "
                else:
                    color = text_c
                    prefix = ICONS.CIRCLE_O + " "
                lbl.setText(prefix + item.get("name", ""))
                lbl.setStyleSheet(f"color: {color}; background: transparent; border: none; font-size: 8pt;")

        update_items(self._macro_lines,
                      lambda m: macro_engine.running.get(m.get("hotkey", ""), False))
        update_items(self._proc_lines, lambda p: False)
        self._update_buff_display()

        self.update()
        _dbg("do_update", {"toggle_on": self._toggle_on})

    def _update_buff_display(self):
        t = theme.colors()
        text_c   = t.get("text", "#EDE0E4")
        text_sec = t.get("textSecondary", "#A8949C")
        accent   = t.get("success", "#9DD5B8") if self._toggle_on else t.get("error", "#F2B8B5")

        timer_info = buff_engine.get_timer_info()
        for item, lbl in self._buff_lines:
            enabled = item.get("enabled", True)
            name = item.get("name", "")
            info = timer_info.get(name)
            bar = self._buff_bars.get(name)

            if not self._toggle_on or not enabled:
                color = text_sec
                prefix = ICONS.CIRCLE_O + " "
                suffix = ""
                if bar:
                    bar.setVisible(False)
            elif info is not None and info["remaining"] > 0:
                color = accent
                prefix = ICONS.CIRCLE + " "
                secs = info["remaining"] / 1000.0
                suffix = f" {secs:.0f}s" if secs >= 10 else f" {secs:.1f}s"
                if bar:
                    bar.setVisible(True)
                    bar.set_progress(info["progress"], accent)
            else:
                color = text_c
                prefix = ICONS.CIRCLE_O + " "
                suffix = ""
                if bar:
                    bar.setVisible(False)

            lbl.setText(prefix + name + suffix)
            lbl.setStyleSheet(f"color: {color}; background: transparent; border: none; font-size: 8pt;")

    def _update_buff_timers(self):
        if self._destroyed:
            return
        if self._buff_lines:
            try:
                self._update_buff_display()
                self.update()
            except RuntimeError as e:
                print(f"[overlay] buff timer update error: {e}")

    def _on_buff_event(self, event_type, buff_name, detail):
        if self._destroyed:
            return
        state_key = buff_name
        old_state = self._last_buff_state.get(state_key)
        new_state = f"{event_type}:{detail}" if detail else event_type
        if old_state != new_state:
            self._last_buff_state[state_key] = new_state
            _dbg("buff_event", {"name": buff_name, "event": event_type})
            self.notify()

    def is_toggle_on(self):
        return self._toggle_on

    def _on_overlay_toggle(self, checked):
        """Handle user clicking the overlay toggle switch."""
        import modules.macro_engine as me
        me.macros_paused = not checked
        self._toggle_on = checked
        # Notify main app to sync state
        app_inst = QGuiApplication.instance()
        if app_inst:
            # Find main window and update status
            for w in app_inst.topLevelWidgets():
                if hasattr(w, '_update_status'):
                    w._update_status()
                    break

    def refresh_macros(self):
        self._rebuild_lines()
        self._do_update()

    # ------------------------------------------------------------------ #
    #  Positioning & drag
    # ------------------------------------------------------------------ #
    def _apply_settings(self):
        s = config.data.get("settings", {})
        width = max(160, min(400, s.get("overlayWidth", 230)))
        self.setFixedWidth(width)
        opacity = max(0.3, min(1.0, s.get("overlayOpacity", 0.92)))
        self.setWindowOpacity(opacity)
        self._set_clickthrough(not s.get("overlayClickable", False))

    def _set_clickthrough(self, enabled):
        """Enable/disable click-through using Windows WS_EX_TRANSPARENT."""
        try:
            import ctypes
            from ctypes import wintypes

            GWL_EXSTYLE = -20
            WS_EX_TRANSPARENT = 0x00000020

            hwnd = int(self.winId())
            user32 = ctypes.windll.user32
            exstyle = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if enabled:
                exstyle |= WS_EX_TRANSPARENT
            else:
                exstyle &= ~WS_EX_TRANSPARENT
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, exstyle)
        except Exception:
            pass

    def _position_overlay(self):
        self.adjustSize()
        s = config.data.get("settings", {})
        pos_preset = s.get("overlayPosition", "top-left")
        screen = QGuiApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        margin = 10
        if pos_preset == "top-right":
            x = geo.right() - self.width() - margin
            y = geo.top() + margin
        elif pos_preset == "bottom-left":
            x = geo.left() + margin
            y = geo.bottom() - self.height() - margin
        elif pos_preset == "bottom-right":
            x = geo.right() - self.width() - margin
            y = geo.bottom() - self.height() - margin
        elif pos_preset == "custom":
            x = s.get("overlayX", 10)
            y = s.get("overlayY", 10)
        else:  # top-left
            x = geo.left() + margin
            y = geo.top() + margin
        self.move(x, y)

    def showEvent(self, event):
        super().showEvent(event)
        self._position_overlay()
        # Ensure click-through is applied now that HWND exists
        s = config.data.get("settings", {})
        self._set_clickthrough(not s.get("overlayClickable", False))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Allow dragging from the drag handle, or anywhere if Shift is held
            on_handle = self._drag_handle.geometry().contains(event.pos())
            shift_held = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            if on_handle or shift_held:
                self._dragging = True
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                self._drag_handle.setCursor(Qt.CursorShape.ClosedHandCursor)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging and self._drag_pos is not None:
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            self.move(new_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._dragging = False
            self._drag_handle.setCursor(Qt.CursorShape.OpenHandCursor)
            # Save custom position
            config.data["settings"]["overlayPosition"] = "custom"
            config.data["settings"]["overlayX"] = self.x()
            config.data["settings"]["overlayY"] = self.y()
            config.save()
            event.accept()
            return
        super().mouseReleaseEvent(event)
