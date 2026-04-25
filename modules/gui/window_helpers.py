"""Window helper utilities for frameless windows on Windows."""
import ctypes
from ctypes import wintypes


def apply_rounded_corners(widget):
    """
    Apply rounded corners to a top-level window using the Windows DWM API.
    Works on Windows 11+. Falls back gracefully on older versions or errors.
    """
    try:
        hwnd = int(widget.winId())
    except Exception:
        return

    # DWMWA_WINDOW_CORNER_PREFERENCE = 33
    # DWMWCP_DEFAULT = 0, DWMWCP_DONOTROUND = 1, DWMWCP_ROUND = 2, DWMWCP_ROUNDSMALL = 3
    try:
        DWMWA_WINDOW_CORNER_PREFERENCE = 33
        DWMWCP_ROUND = 2
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(ctypes.c_int(DWMWCP_ROUND)),
            ctypes.sizeof(ctypes.c_int)
        )
    except Exception:
        pass

    # Frameless windows sometimes need a border style for DWM rounding to apply.
    # Add WS_BORDER without making it visually visible.
    try:
        GWL_STYLE = -16
        WS_BORDER = 0x00800000
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
        if not (style & WS_BORDER):
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style | WS_BORDER)
            SWP_FRAMECHANGED = 0x0020
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOZORDER = 0x0004
            SWP_NOACTIVATE = 0x0010
            ctypes.windll.user32.SetWindowPos(
                hwnd, 0, 0, 0, 0, 0,
                SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE
            )
    except Exception:
        pass
