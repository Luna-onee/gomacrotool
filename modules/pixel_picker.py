import ctypes
import ctypes.wintypes

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QPen, QGuiApplication, QPixmap, QCursor,
    QBitmap,
)

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
VK_MBUTTON = 0x04
VK_ESCAPE = 0x1B
VK_RETURN = 0x0D
VK_SPACE = 0x20
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28


def _key_down(vk):
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


class PixelPickerOverlay(QWidget):
    def __init__(self):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setFixedSize(240, 320)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        blank = QBitmap(1, 1)
        blank.clear()
        self.setCursor(QCursor(blank, blank, 0, 0))

        self._frozen = False
        self._frozen_pos = QPoint(0, 0)
        self._mx = 0
        self._my = 0
        self._color_hex = "0x000000"
        self._color_qt = QColor(0, 0, 0)
        self._active = False
        self._callback = None
        self._zoom_pixmap = QPixmap()
        self._prev_keys = {}
        self._ready = False

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def start(self, callback):
        self._callback = callback
        self._frozen = False
        self._active = True
        self._ready = False
        self._prev_keys = {}
        self._timer.start(16)
        self.show()

    def stop(self):
        self._active = False
        self._timer.stop()
        self.hide()
        self._callback = None

    def _just_pressed(self, vk):
        now = _key_down(vk)
        was = self._prev_keys.get(vk, False)
        self._prev_keys[vk] = now
        return now and not was

    def _tick(self):
        if not self._active:
            return

        # ===== Input polling =====
        # Skip first few ticks to let the opening click release
        if not self._ready:
            self._ready = not _key_down(VK_LBUTTON)
            if not self._ready:
                for vk in (VK_ESCAPE, VK_LBUTTON, VK_RETURN, VK_SPACE):
                    self._prev_keys[vk] = _key_down(vk)
                return

        if self._just_pressed(VK_ESCAPE):
            self._handle_cancel()
            return

        if self._just_pressed(VK_LBUTTON) or self._just_pressed(VK_RETURN):
            self._handle_select()
            return

        if self._just_pressed(VK_SPACE):
            self._handle_freeze()

        # Arrow keys: held = continuous movement (1px per tick)
        if _key_down(VK_UP):
            self._do_move(0, -1)
        if _key_down(VK_DOWN):
            self._do_move(0, 1)
        if _key_down(VK_LEFT):
            self._do_move(-1, 0)
        if _key_down(VK_RIGHT):
            self._do_move(1, 0)

        # Flush stale held state for one-shot keys
        for vk in (VK_ESCAPE, VK_LBUTTON, VK_RETURN, VK_SPACE):
            if _key_down(vk):
                self._prev_keys[vk] = True

        # ===== Position / capture / paint =====

        if self._frozen:
            mx = self._frozen_pos.x()
            my = self._frozen_pos.y()
        else:
            pos = QCursor.pos()
            mx = pos.x()
            my = pos.y()

        self._mx = mx
        self._my = my

        self._color_hex = _pixel_get_color(mx, my)
        c = int(self._color_hex, 16)
        self._color_qt = QColor(c >> 16, (c >> 8) & 0xFF, c & 0xFF)

        try:
            screen = QGuiApplication.primaryScreen()
            if screen:
                self._zoom_pixmap = screen.grabWindow(0, mx - 10, my - 10, 20, 20)
        except Exception:
            self._zoom_pixmap = QPixmap()

        wx = mx + 25
        wy = my + 25
        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)
        if wx + 250 > sw:
            wx = mx - 265
        if wy + 330 > sh:
            wy = my - 345
        if wy < 0:
            wy = 5
        self.move(wx, wy)

        self.update()

    def _do_move(self, dx, dy):
        if self._frozen:
            self._frozen_pos = QPoint(
                self._frozen_pos.x() + dx,
                self._frozen_pos.y() + dy,
            )
        else:
            pt = ctypes.wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            user32.SetCursorPos(pt.x + dx, pt.y + dy)

    def paintEvent(self, a0):
        from modules.theme import theme

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # Header
        sc = QColor(theme.get("surfaceContainerLow"))
        p.fillRect(0, 0, 240, 60, sc)

        # Zoom area constants
        PX, PY, PW, PH = 20, 60, 200, 200
        PIX = 10  # each source pixel = 10x10 display pixels

        # Zoomed screen capture
        if not self._zoom_pixmap.isNull():
            scaled = self._zoom_pixmap.scaled(
                PW, PH,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.FastTransformation,
            )
            p.drawPixmap(PX, PY, scaled)
        else:
            p.fillRect(PX, PY, PW, PH, QColor(0, 0, 0))

        # Center pixel top-left in widget space
        cx = PX + 10 * PIX  # 20 + 100 = 120
        cy = PY + 10 * PIX  # 60 + 100 = 160

        # Crosshair lines: stop short of the yellow box edges
        # Yellow box is 2px pen on rect (cx,cy,PIX,PIX) → covers cx-1..cx+PIX+1
        # So lines go from zoom edge to yellow box boundary
        gap = 2  # pixels of gap between line end and yellow box edge
        pen = QPen(QColor(theme.get("primary")), 1)
        p.setPen(pen)
        mid_y = cy + PIX // 2
        mid_x = cx + PIX // 2
        # Horizontal: left of center
        p.drawLine(PX, mid_y, cx - gap, mid_y)
        # Horizontal: right of center
        p.drawLine(cx + PIX + gap, mid_y, PX + PW, mid_y)
        # Vertical: above center
        p.drawLine(mid_x, PY, mid_x, cy - gap)
        # Vertical: below center
        p.drawLine(mid_x, cy + PIX + gap, mid_x, PY + PH)

        # Yellow highlight box exactly on the center pixel
        p.setPen(QPen(QColor(255, 255, 0), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(cx, cy, PIX, PIX)

        # Footer
        p.fillRect(0, 260, 240, 60, QColor(theme.get("surfaceHigh")))

        # Color swatch
        p.fillRect(150, 25, 80, 30, self._color_qt)
        p.setPen(QPen(QColor(theme.get("outline")), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(150, 25, 80, 30)

        # Header text
        p.setPen(QColor(theme.get("text")))
        p.setFont(QFont("Segoe UI", 9))
        frozen_str = " [F]" if self._frozen else ""
        p.drawText(10, 20, f"X:{self._mx} Y:{self._my}{frozen_str}")
        p.drawText(10, 44, f"Color: {self._color_hex}")

        # Footer text
        p.setPen(QColor(theme.get("textSecondary")))
        p.setFont(QFont("Segoe UI", 8))
        p.drawText(10, 280, "Click=Select Esc=Cancel")
        p.drawText(10, 296, "Arrows=Move Space=Freeze")

        p.end()

    # ===== Actions =====

    def _handle_select(self):
        if not self._active:
            return
        from modules.utils import get_screen_resolution
        result = {
            "x": self._mx,
            "y": self._my,
            "color": self._color_hex,
            "screenRes": get_screen_resolution(),
        }
        cb = self._callback
        self.stop()
        if cb:
            cb(result)

    def _handle_cancel(self):
        cb = self._callback
        self.stop()
        if cb:
            cb(None)

    def _handle_freeze(self):
        if not self._active:
            return
        if self._frozen:
            self._frozen = False
        else:
            pt = ctypes.wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            self._frozen_pos = QPoint(pt.x, pt.y)
            self._frozen = True


def _pixel_get_color(x, y):
    from modules.utils import get_pixel_color
    return get_pixel_color(x, y)


_overlay = None


def is_running():
    return _overlay is not None and _overlay._active


def start(callback):
    global _overlay
    close()
    _overlay = PixelPickerOverlay()
    _overlay.start(callback)


def close():
    global _overlay
    if _overlay:
        _overlay.stop()
        _overlay.deleteLater()
        _overlay = None
