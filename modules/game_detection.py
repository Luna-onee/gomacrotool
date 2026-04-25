import ctypes
import ctypes.wintypes
import os
import threading
import time
from collections import OrderedDict

from PyQt6.QtCore import QTimer

from modules import config_manager as config

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
psapi = ctypes.windll.psapi

window_active = False
_check_timer = None
_detect_timer = None
_last_error = ""
_game_exe = None
_game_pid = None
_macro_hwnd = None
_prev_active = False
_active_callbacks = []
_last_fg_hwnd = None
_last_fg_active = False
_last_path = None
_CHECK_INTERVAL_MS = 150
# PID -> (path, timestamp) cache to reduce handle churn
_PROC_PATH_CACHE = OrderedDict()
_PROC_CACHE_LOCK = threading.Lock()
_PROC_CACHE_TTL = 2.0
_PROC_CACHE_MAX_SIZE = 128


def _cached_process_path(pid):
    """Return process path, caching by PID for a short TTL to avoid handle churn."""
    if not pid:
        return None
    now = time.time()
    with _PROC_CACHE_LOCK:
        entry = _PROC_PATH_CACHE.get(pid)
        if entry and (now - entry[1]) < _PROC_CACHE_TTL:
            _PROC_PATH_CACHE.move_to_end(pid)
            return entry[0]
    path = _get_process_path(pid)
    if path:
        with _PROC_CACHE_LOCK:
            _PROC_PATH_CACHE[pid] = (path, now)
            _PROC_PATH_CACHE.move_to_end(pid)
            while len(_PROC_PATH_CACHE) > _PROC_CACHE_MAX_SIZE:
                _PROC_PATH_CACHE.popitem(last=False)
    return path


def clear_proc_cache():
    """Clear stale PID path cache."""
    with _PROC_CACHE_LOCK:
        _PROC_PATH_CACHE.clear()


def is_active():
    only = config.data.get("settings", {}).get("onlyInGame", True)
    if not only:
        return True
    return window_active


def is_active_now():
    only = config.data.get("settings", {}).get("onlyInGame", True)
    if not only:
        return True
    return _check_foreground()


def get_status():
    return _last_error


def get_game_pid():
    return _game_pid


def get_game_hwnd():
    """Find the game window HWND by enumerating windows and matching PID."""
    pid = _game_pid
    if not pid:
        return None
    result = ctypes.c_void_p(None)

    def _enum_proc(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        wpid = ctypes.wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
        if wpid.value == pid:
            result.value = hwnd
            return False
        return True

    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    user32.EnumWindows(EnumWindowsProc(_enum_proc), 0)
    return result.value


def register_active_callback(cb):
    _active_callbacks.append(cb)


def _notify_active_change():
    for cb in list(_active_callbacks):
        try:
            cb(window_active)
        except Exception as e:
            print(f"[game_detection] callback error: {e}")


def stop_window_check(app=None):
    global _check_timer
    if app and hasattr(app, '_gd_check_timer'):
        app._gd_check_timer.stop()
    _check_timer = None


def stop_auto_detect(app=None):
    global _detect_timer
    if app and hasattr(app, '_gd_detect_timer'):
        app._gd_detect_timer.stop()
    _detect_timer = None


def start_window_check(app=None):
    global _check_timer
    if app:
        if not hasattr(app, '_gd_check_timer'):
            app._gd_check_timer = QTimer()
            app._gd_check_timer.timeout.connect(check_window)
        _check_timer = app._gd_check_timer
        _check_timer.start(_CHECK_INTERVAL_MS)


def start_auto_detect(app=None):
    global _detect_timer
    if app:
        if not hasattr(app, '_gd_detect_timer'):
            app._gd_detect_timer = QTimer()
            app._gd_detect_timer.timeout.connect(auto_detect)
        _detect_timer = app._gd_detect_timer
        _detect_timer.start(2000)


def set_macro_hwnd(hwnd):
    global _macro_hwnd
    _macro_hwnd = hwnd


def _check_foreground():
    g = config.data.get("activeGame", "")
    if not g or g not in config.data.get("games", {}):
        return False
    gd = config.data["games"][g]
    path = gd.get("path", "")
    if not path:
        return True
    game_exe = os.path.basename(path).lower()
    fg = user32.GetForegroundWindow()
    if fg == _macro_hwnd:
        return True
    pid = ctypes.wintypes.DWORD()
    user32.GetWindowThreadProcessId(fg, ctypes.byref(pid))
    proc_path = _cached_process_path(pid.value)
    if not proc_path:
        return False
    return os.path.basename(proc_path).lower() == game_exe


def check_window():
    global window_active, _last_error, _game_exe, _game_pid, _prev_active
    global _last_fg_hwnd, _last_fg_active
    old = window_active

    g = config.data.get("activeGame", "")
    if not g or g not in config.data.get("games", {}):
        window_active = False
        _game_pid = None
        _last_error = "No game selected"
    else:
        gd = config.data["games"][g]
        path = gd.get("path", "")
        if not path:
            window_active = True
            _last_error = ""
        else:
            _game_exe = os.path.basename(path).lower()
            fg = user32.GetForegroundWindow()
            if fg == _macro_hwnd:
                window_active = True
                _last_error = ""
                _last_fg_hwnd = fg
            elif fg == _last_fg_hwnd:
                window_active = _last_fg_active
            else:
                pid = ctypes.wintypes.DWORD()
                user32.GetWindowThreadProcessId(fg, ctypes.byref(pid))
                proc_path = _cached_process_path(pid.value)
                if proc_path:
                    active_exe = os.path.basename(proc_path).lower()
                    if active_exe == _game_exe:
                        window_active = True
                        _last_error = ""
                        _game_pid = pid.value
                    else:
                        _last_error = f"FG:{active_exe}"
                        window_active = False
                        _game_pid = None
                else:
                    _last_error = "No FG window"
                    window_active = False
                    _game_pid = None
                _last_fg_hwnd = fg
                _last_fg_active = window_active

    if window_active != old:
        _notify_active_change()


def auto_detect():
    if not config.data.get("settings", {}).get("autoDetectGame", False):
        return
    try:
        hwnd = user32.GetForegroundWindow()
        pid = ctypes.wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        proc_path = _cached_process_path(pid.value)
        if not proc_path:
            return
        active_exe = os.path.basename(proc_path).lower()
        for name, game_data in config.data.get("games", {}).items():
            gp = game_data.get("path", "")
            if gp:
                game_exe = os.path.basename(gp).lower()
                if game_exe == active_exe and config.data.get("activeGame", "") != name:
                    config.data["activeGame"] = name
                    return ("game_detected", name)
    except Exception as e:
        print(f"[game_detection] auto_detect error: {e}")
    return None


def _get_process_path(pid):
    if not pid:
        return None
    try:
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return None
        try:
            buf = ctypes.create_unicode_buffer(512)
            psapi.GetModuleFileNameExW(handle, None, buf, 512)
            return buf.value if buf.value else None
        finally:
            kernel32.CloseHandle(handle)
    except Exception:
        return None
