import ctypes
import ctypes.wintypes
import os
import struct
import time

try:
    import _native
    HAS_NATIVE = True
except ImportError:
    HAS_NATIVE = False

_kernel32 = ctypes.windll.kernel32
_qpc_frequency = 0


def init():
    global _qpc_frequency
    if HAS_NATIVE:
        _native.init()
        return
    ctypes.windll.user32.SetProcessDPIAware()
    freq = ctypes.c_int64()
    _kernel32.QueryPerformanceFrequency(ctypes.byref(freq))
    _qpc_frequency = freq.value


def precise_sleep(ms):
    if HAS_NATIVE:
        _native.precise_sleep(ms)
        return
    if ms <= 0:
        return
    if ms < 2:
        _busy_wait(ms)
        return
    if ms > 5:
        _kernel32.Sleep(int(ms - 2))
        _busy_wait(2)
    else:
        _busy_wait(ms)


def _busy_wait(ms):
    if ms <= 0 or _qpc_frequency == 0:
        return
    counter = ctypes.c_int64()
    _kernel32.QueryPerformanceCounter(ctypes.byref(counter))
    start = counter.value
    target = start + int(_qpc_frequency * ms / 1000)
    while True:
        _kernel32.QueryPerformanceCounter(ctypes.byref(counter))
        if counter.value >= target:
            break


def get_precise_time():
    if HAS_NATIVE:
        return _native.get_time()
    counter = ctypes.c_int64()
    _kernel32.QueryPerformanceCounter(ctypes.byref(counter))
    return counter.value * 1000.0 / _qpc_frequency


def color_match(c1, c2, v):
    if HAS_NATIVE:
        a = _color_int(c1)
        b = _color_int(c2)
        return _native.color_match(a, b, v)
    a = int(c1, 16) if isinstance(c1, str) else c1
    b = int(c2, 16) if isinstance(c2, str) else c2
    return (abs(((a >> 16) & 0xFF) - ((b >> 16) & 0xFF)) <= v
            and abs(((a >> 8) & 0xFF) - ((b >> 8) & 0xFF)) <= v
            and abs((a & 0xFF) - (b & 0xFF)) <= v)


def _color_int(c):
    if isinstance(c, str):
        return int(c, 16)
    return int(c)


def get_pixel_color(x, y):
    if HAS_NATIVE:
        c = _native.get_pixel_color(x, y)
        return f"0x{c:06X}"
    hdc = ctypes.windll.user32.GetDC(0)
    if not hdc:
        return "0x000000"
    try:
        color = ctypes.windll.gdi32.GetPixel(hdc, x, y)
        if color == -1:
            return "0x000000"
        r = color & 0xFF
        g = (color >> 8) & 0xFF
        b_val = (color >> 16) & 0xFF
        return f"0x{r:02X}{g:02X}{b_val:02X}"
    finally:
        ctypes.windll.user32.ReleaseDC(0, hdc)


def check_pixels_packed(packed_bytes, match_mode):
    if HAS_NATIVE:
        return _native.capture_and_check(packed_bytes, match_mode)
    return None


def pack_pixels(pixels):
    data = bytearray()
    for px in pixels:
        x = px.get("x", 0)
        y = px.get("y", 0)
        c = px.get("color", "0x000000")
        color_int = int(c, 16) if isinstance(c, str) else int(c)
        var = px.get("variation", 10)
        data += struct.pack("iiii", x, y, color_int, var)
    return bytes(data)


def color_to_bgr(color):
    cv = int(color, 16) if isinstance(color, str) else color
    return ((cv & 0xFF) << 16) | (cv & 0xFF00) | ((cv >> 16) & 0xFF)


def hex_to_rgbref(hex_str):
    hex_str = hex_str.lstrip('#')
    r = int(hex_str[0:2], 16)
    g = int(hex_str[2:4], 16)
    b = int(hex_str[4:6], 16)
    return (b << 16) | (g << 8) | r


def has_val(arr, v):
    return v in arr


def safe_int(val, default=0):
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def get_screen_resolution():
    w = ctypes.windll.user32.GetSystemMetrics(0)
    h = ctypes.windll.user32.GetSystemMetrics(1)
    return {"w": w, "h": h}


def scale_pixels(pixels, capture_res, current_res=None):
    if not pixels or not capture_res:
        return pixels
    if current_res is None:
        current_res = get_screen_resolution()
    cw = capture_res.get("w", 0)
    ch = capture_res.get("h", 0)
    nw = current_res.get("w", 0)
    nh = current_res.get("h", 0)
    if cw <= 0 or ch <= 0 or nw <= 0 or nh <= 0:
        return pixels
    if cw == nw and ch == nh:
        return pixels
    rx = nw / cw
    ry = nh / ch
    return [
        {"x": round(px["x"] * rx), "y": round(px["y"] * ry),
         "color": px["color"], "variation": px["variation"]}
        for px in pixels
    ]


_kernel32 = ctypes.windll.kernel32

def set_macro_thread_affinity():
    count = os.cpu_count() or 4
    start = count * 3 // 4
    mask = 0
    for i in range(start, count):
        mask |= (1 << i)
    if mask == 0:
        mask = 1
    _kernel32.SetThreadAffinityMask(_kernel32.GetCurrentThread(), mask)
