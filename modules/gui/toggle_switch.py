"""Material Design 3 toggle switch for PyQt6."""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen

from modules.theme import theme


class ToggleSwitch(QWidget):
    """Material Design 3 switch widget.

    Click to toggle. Emits `toggled(bool)` on state change.
    Animates thumb position smoothly.
    """

    toggled = pyqtSignal(bool)

    def __init__(self, parent=None, checked=False, size=26):
        super().__init__(parent)
        self._checked = checked
        self._track_h = size
        self._thumb_d = int(size * 0.77)
        self._pad = max(2, int(size * 0.08))
        self._anim_value = 1.0 if checked else 0.0
        self._anim = None

        w = int(self._track_h * 1.85)
        h = self._track_h
        self.setFixedSize(w, h)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def get_anim_value(self):
        return self._anim_value

    def set_anim_value(self, value):
        self._anim_value = value
        self.update()

    _anim_prop = pyqtProperty(float, get_anim_value, set_anim_value)

    def isChecked(self):
        return self._checked

    def setChecked(self, checked):
        if self._checked == checked:
            return
        self._checked = checked
        self._run_anim()
        self.toggled.emit(checked)

    def _run_anim(self):
        if self._anim is None:
            self._anim = QPropertyAnimation(self, b"_anim_prop")
            self._anim.setDuration(150)
            self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._anim.stop()
        start = self._anim_value
        end = 1.0 if self._checked else 0.0
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.start()

    def _thumb_x(self):
        left = self._pad
        right = self.width() - self._thumb_d - self._pad
        return left + (right - left) * self._anim_value

    def sizeHint(self):
        return self.size()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        t = theme.colors()
        primary = QColor(t.get("primary", "#D0BCFF"))
        on_primary = QColor(t.get("onPrimary", "#381E72"))
        outline = QColor(t.get("outline", "#938F99"))
        sc_low = QColor(t.get("surfaceContainerLow", "#1F191C"))

        # Track
        track_r = self._track_h // 2
        if self._checked:
            track_color = QColor(primary)
            track_color.setAlpha(200)
        else:
            track_color = QColor(outline)
            track_color.setAlpha(100)

        track_rect = QRect(0, 0, self.width(), self._track_h)
        p.setBrush(QBrush(track_color))
        # Draw subtle outline so track is visible on any background
        p.setPen(QPen(outline, 1))
        p.drawRoundedRect(track_rect, track_r, track_r)

        # Thumb
        thumb_x = int(self._thumb_x())
        thumb_y = (self._track_h - self._thumb_d) // 2
        thumb_rect = QRect(thumb_x, thumb_y, self._thumb_d, self._thumb_d)

        if self._checked:
            thumb_color = on_primary
            thumb_pen = Qt.PenStyle.NoPen
        else:
            thumb_color = sc_low
            thumb_pen = QPen(outline, 1)

        p.setBrush(QBrush(thumb_color))
        p.setPen(thumb_pen)
        p.drawEllipse(thumb_rect)

        p.end()
