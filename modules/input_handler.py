import ctypes
import ctypes.wintypes

try:
    import _native
    HAS_NATIVE = True
except ImportError:
    HAS_NATIVE = False

user32 = ctypes.windll.user32

INPUT_KEYBOARD = 1
INPUT_MOUSE = 0
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_EXTENDEDKEY = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_XDOWN = 0x0080
MOUSEEVENTF_XUP = 0x0100
XBUTTON1 = 1
XBUTTON2 = 2
MAPVK_VK_TO_VSC = 0


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.wintypes.WORD),
        ("wScan", ctypes.wintypes.WORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.wintypes.DWORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("ki", KEYBDINPUT),
        ("mi", MOUSEINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.wintypes.DWORD),
        ("union", INPUT_UNION),
    ]


VK_MAP = {
    "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34, "5": 0x35,
    "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39, "0": 0x30,
    "a": 0x41, "b": 0x42, "c": 0x43, "d": 0x44, "e": 0x45,
    "f": 0x46, "g": 0x47, "h": 0x48, "i": 0x49, "j": 0x4A,
    "k": 0x4B, "l": 0x4C, "m": 0x4D, "n": 0x4E, "o": 0x4F,
    "p": 0x50, "q": 0x51, "r": 0x52, "s": 0x53, "t": 0x54,
    "u": 0x55, "v": 0x56, "w": 0x57, "x": 0x58, "y": 0x59,
    "z": 0x5A,
    "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73, "F5": 0x74,
    "F6": 0x75, "F7": 0x76, "F8": 0x77, "F9": 0x78, "F10": 0x79,
    "F11": 0x7A, "F12": 0x7B,
    "Tab": 0x09, "Enter": 0x0D, "Escape": 0x1B, "Backspace": 0x08,
    "Space": 0x20, "Delete": 0x2E, "Insert": 0x2D,
    "Home": 0x24, "End": 0x23, "PgUp": 0x21, "PgDn": 0x22,
    "Up": 0x26, "Down": 0x28, "Left": 0x25, "Right": 0x27,
    "CapsLock": 0x14, "ScrollLock": 0x91, "NumLock": 0x90,
    "PrintScreen": 0x2C, "Pause": 0x13,
    "Shift": 0x10, "Ctrl": 0x11, "Alt": 0x12,
    "LButton": 0x01, "RButton": 0x02, "MButton": 0x04,
    "Numpad0": 0x60, "Numpad1": 0x61, "Numpad2": 0x62, "Numpad3": 0x63,
    "Numpad4": 0x64, "Numpad5": 0x65, "Numpad6": 0x66, "Numpad7": 0x67,
    "Numpad8": 0x68, "Numpad9": 0x69,
    "NumpadEnter": 0x0D, "NumpadAdd": 0x6B, "NumpadSub": 0x6D,
    "NumpadMult": 0x6A, "NumpadDiv": 0x6F,
    "XButton1": 0x05, "XButton2": 0x06,
}

EXTENDED_KEYS = {
    "Insert", "Delete", "Home", "End", "PgUp", "PgDn",
    "Up", "Down", "Left", "Right",
    "NumpadEnter", "NumpadDiv",
}

MOUSE_KEYS = {"LButton", "RButton", "MButton", "XButton1", "XButton2"}

_vk_to_name = {v: k for k, v in VK_MAP.items()}


def _make_key_input(vk, up=False):
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    flags = 0
    if up:
        flags |= KEYEVENTF_KEYUP
    name = _vk_to_name.get(vk)
    if name and name in EXTENDED_KEYS:
        flags |= KEYEVENTF_EXTENDEDKEY
    scan = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)
    inp.union.ki.wVk = vk
    inp.union.ki.wScan = scan
    inp.union.ki.dwFlags = flags
    inp.union.ki.time = 0
    inp.union.ki.dwExtraInfo = ctypes.pointer(ctypes.c_ulong(0))
    return inp


def _make_mouse_input(key, up=False):
    inp = INPUT()
    inp.type = INPUT_MOUSE
    flags = 0
    mouse_data = 0
    if key == "LButton":
        flags = MOUSEEVENTF_LEFTUP if up else MOUSEEVENTF_LEFTDOWN
    elif key == "RButton":
        flags = MOUSEEVENTF_RIGHTUP if up else MOUSEEVENTF_RIGHTDOWN
    elif key == "MButton":
        flags = MOUSEEVENTF_MIDDLEUP if up else MOUSEEVENTF_MIDDLEDOWN
    elif key == "XButton1":
        flags = MOUSEEVENTF_XUP if up else MOUSEEVENTF_XDOWN
        mouse_data = XBUTTON1
    elif key == "XButton2":
        flags = MOUSEEVENTF_XUP if up else MOUSEEVENTF_XDOWN
        mouse_data = XBUTTON2
    inp.union.mi.dx = 0
    inp.union.mi.dy = 0
    inp.union.mi.mouseData = mouse_data
    inp.union.mi.dwFlags = flags
    inp.union.mi.time = 0
    inp.union.mi.dwExtraInfo = ctypes.pointer(ctypes.c_ulong(0))
    return inp


def _send_input(inputs):
    n = len(inputs)
    arr = (INPUT * n)(*inputs)
    user32.SendInput(n, ctypes.byref(arr), ctypes.sizeof(INPUT))


def send_key_to_window(hwnd, key):
    """Send a keypress to a specific window using PostMessage.

    This works even when the target window is not focused.
    Useful for sending buff refresh keys to the game while tabbed out.
    """
    if not hwnd:
        return
    WM_KEYDOWN = 0x0100
    WM_KEYUP = 0x0101
    vk = VK_MAP.get(key)
    if vk is None:
        return
    scan = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)
    # lParam for KEYDOWN: repeat count 1, scan code, no extended, no previous, no transition
    lparam_down = 1 | (scan << 16)
    # lParam for KEYUP: repeat count 1, scan code, no extended, previous=1, transition=1
    lparam_up = 1 | (scan << 16) | (1 << 30) | (1 << 31)
    user32.PostMessageW(hwnd, WM_KEYDOWN, vk, lparam_down)
    user32.PostMessageW(hwnd, WM_KEYUP, vk, lparam_up)


def send_key(key):
    if HAS_NATIVE:
        _native.send_key(key)
        return
    if key in MOUSE_KEYS:
        _send_input([_make_mouse_input(key, False)])
        _send_input([_make_mouse_input(key, True)])
        return
    vk = VK_MAP.get(key)
    if vk is None:
        return
    _send_input([_make_key_input(vk, False), _make_key_input(vk, True)])


def send_key_down(key):
    if HAS_NATIVE:
        _native.send_key_down(key)
        return
    if key in MOUSE_KEYS:
        _send_input([_make_mouse_input(key, False)])
        return
    vk = VK_MAP.get(key)
    if vk is None:
        return
    _send_input([_make_key_input(vk, False)])


def send_key_up(key):
    if HAS_NATIVE:
        _native.send_key_up(key)
        return
    if key in MOUSE_KEYS:
        _send_input([_make_mouse_input(key, True)])
        return
    vk = VK_MAP.get(key)
    if vk is None:
        return
    _send_input([_make_key_input(vk, True)])


def send_key_batch(keys):
    if HAS_NATIVE:
        _native.send_key_batch(keys)
        return
    kb_inputs = []
    for key in keys:
        if key in MOUSE_KEYS:
            if kb_inputs:
                _send_input(kb_inputs)
                kb_inputs = []
            _send_input([_make_mouse_input(key, False)])
            _send_input([_make_mouse_input(key, True)])
        else:
            vk = VK_MAP.get(key)
            if vk is not None:
                kb_inputs.append(_make_key_input(vk, False))
                kb_inputs.append(_make_key_input(vk, True))
    if kb_inputs:
        _send_input(kb_inputs)


def key_to_vk(key):
    if HAS_NATIVE:
        vk = _native.name_to_vk(key)
        return vk if vk else VK_MAP.get(key, 0)
    return VK_MAP.get(key, 0)


def vk_to_key_name(vk):
    if HAS_NATIVE:
        name = _native.vk_to_name(vk)
        if name and name != str(vk):
            return name
    return _vk_to_name.get(vk, str(vk))
