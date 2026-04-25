import ctypes
import ctypes.wintypes
import threading
import time

from modules import config_manager as config
from modules import game_detection
from modules import input_handler
from modules import buff_engine as buff_mod
from modules import utils
from modules import perf_stats
from modules import timer_res

import keyboard

try:
    import _native
    HAS_NATIVE = True
except ImportError:
    HAS_NATIVE = False

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

user32.SetWindowsHookExW.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.wintypes.HMODULE, ctypes.wintypes.DWORD]
user32.SetWindowsHookExW.restype = ctypes.wintypes.HHOOK
user32.CallNextHookEx.argtypes = [ctypes.wintypes.HHOOK, ctypes.c_int, ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM]
user32.CallNextHookEx.restype = ctypes.c_int
user32.UnhookWindowsHookEx.argtypes = [ctypes.wintypes.HHOOK]
user32.UnhookWindowsHookEx.restype = ctypes.c_bool
user32.GetMessageW.argtypes = [ctypes.POINTER(ctypes.wintypes.MSG), ctypes.wintypes.HWND, ctypes.c_uint, ctypes.c_uint]
user32.GetMessageW.restype = ctypes.c_bool
user32.PeekMessageW.argtypes = [ctypes.POINTER(ctypes.wintypes.MSG), ctypes.wintypes.HWND, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint]
user32.PeekMessageW.restype = ctypes.c_bool
user32.TranslateMessage.argtypes = [ctypes.POINTER(ctypes.wintypes.MSG)]
user32.TranslateMessage.restype = ctypes.c_bool
user32.DispatchMessageW.argtypes = [ctypes.POINTER(ctypes.wintypes.MSG)]
user32.DispatchMessageW.restype = ctypes.c_long
user32.PostThreadMessageW.argtypes = [ctypes.wintypes.DWORD, ctypes.c_uint, ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM]
user32.PostThreadMessageW.restype = ctypes.c_bool
user32.WindowFromPoint.argtypes = [ctypes.wintypes.POINT]
user32.WindowFromPoint.restype = ctypes.wintypes.HWND
user32.GetWindowThreadProcessId.argtypes = [ctypes.wintypes.HWND, ctypes.POINTER(ctypes.wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = ctypes.wintypes.DWORD
kernel32.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
kernel32.GetModuleHandleW.restype = ctypes.wintypes.HMODULE
kernel32.GetCurrentThreadId.argtypes = []
kernel32.GetCurrentThreadId.restype = ctypes.wintypes.DWORD
kernel32.GetCurrentProcessId.argtypes = []
kernel32.GetCurrentProcessId.restype = ctypes.wintypes.DWORD

macros_paused = False

WH_MOUSE_LL = 14
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_MBUTTONDOWN = 0x0208
WM_MBUTTONUP = 0x0209
WM_XBUTTONDOWN = 0x020B
WM_XBUTTONUP = 0x020C
WM_QUIT = 0x0012

MOUSE_KEYS = {"LButton", "RButton", "MButton", "XButton1", "XButton2"}

MOUSE_VK_MAP = {
    "LButton": 0x01,
    "RButton": 0x02,
    "MButton": 0x04,
    "XButton1": 0x05,
    "XButton2": 0x06,
}

_WM_TO_HK = {
    WM_LBUTTONDOWN: "LButton",
    WM_LBUTTONUP: "LButton",
    WM_RBUTTONDOWN: "RButton",
    WM_RBUTTONUP: "RButton",
    WM_MBUTTONDOWN: "MButton",
    WM_MBUTTONUP: "MButton",
}

XBUTTON1 = 1
XBUTTON2 = 2


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", ctypes.wintypes.POINT),
        ("mouseData", ctypes.wintypes.DWORD),
        ("flags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


HOOKPROC = ctypes.CFUNCTYPE(
    ctypes.c_int,
    ctypes.c_int,
    ctypes.wintypes.WPARAM,
    ctypes.wintypes.LPARAM,
)


class MacroEngine:
    def __init__(self):
        self.profile = {}
        self.running = {}
        self._hotkey_handles = []
        self._release_handles = []
        self._hold_threads = {}
        self._lock = threading.Lock()
        self._sending = threading.Event()  # thread-safe flag (external check interface)
        self._sending_lock = threading.Lock()
        self._sending_count = 0

        self._mouse_hotkeys = {}
        self._mouse_hook = None
        self._mouse_hook_proc = None
        self._mouse_thread = None
        self._mouse_tid = None
        self._mouse_stop = threading.Event()
        self._mouse_lock = threading.Lock()

        self._stop_flags = {}
        self._game_flag = ctypes.c_int(1)
        self._state_callbacks = []
        self._buff_map = {}

    def register_callback(self, cb):
        self._state_callbacks.append(cb)

    def _acquire_sending(self):
        with self._sending_lock:
            self._sending_count += 1
            self._sending.set()

    def _release_sending(self):
        with self._sending_lock:
            self._sending_count -= 1
            if self._sending_count <= 0:
                self._sending_count = 0
                self._sending.clear()

    def _notify(self):
        for cb in list(self._state_callbacks):
            try:
                cb()
            except Exception as e:
                print(f"[macro_engine] callback error: {e}")

    def setup(self):
        self.cleanup()

        seen = {}
        conflicts = []

        self._game_flag.value = 1 if game_detection.is_active() else 0

        for m in config.get_macros():
            hk = m.get("hotkey", "")
            if not hk:
                continue
            if hk in seen:
                conflicts.append(f"'{m['name']}' and '{seen[hk]}' both use {hk}")
                continue
            seen[hk] = m["name"]
            self.profile[hk] = m
            self.running[hk] = False
            self._stop_flags[hk] = ctypes.c_int(0)

            try:
                if hk in MOUSE_VK_MAP:
                    self._mouse_hotkeys[hk] = True
                else:
                    kb_key = self._ahk_to_kb_key(hk)
                    if m.get("holdMode", False):
                        h = keyboard.add_hotkey(kb_key, lambda h=hk: self._on_down(h), suppress=True, trigger_on_release=False)
                        self._hotkey_handles.append(h)
                        release_key = self._kb_key_to_release(kb_key)
                        rh = keyboard.on_release_key(release_key, lambda e, h=hk: self._on_up(h))
                        self._release_handles.append(rh)
                    else:
                        h = keyboard.add_hotkey(kb_key, lambda h=hk: self._on_press(h), suppress=True)
                        self._hotkey_handles.append(h)
            except Exception as e:
                print(f"[macro_engine] Failed to register hotkey '{hk}': {e}")

        self.setup_buff_map()

        if self._mouse_hotkeys:
            self._start_mouse_hook()

        if conflicts:
            print(f"Hotkey conflicts: {conflicts}")

    def _start_mouse_hook(self):
        self._mouse_stop.clear()
        with self._mouse_lock:
            self._mouse_hook = None
            self._mouse_tid = None

        def _hook_proc(nCode, wParam, lParam):
            suppress = False
            try:
                if nCode >= 0 and wParam != WM_MOUSEMOVE:
                    hk = None
                    is_down = False

                    if wParam in _WM_TO_HK:
                        hk = _WM_TO_HK[wParam]
                        is_down = wParam in (WM_LBUTTONDOWN, WM_RBUTTONDOWN, WM_MBUTTONDOWN)
                    elif wParam == WM_XBUTTONDOWN:
                        info = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                        xbtn = info.mouseData >> 16
                        if xbtn == XBUTTON1:
                            hk = "XButton1"
                        elif xbtn == XBUTTON2:
                            hk = "XButton2"
                        is_down = True
                    elif wParam == WM_XBUTTONUP:
                        info = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                        xbtn = info.mouseData >> 16
                        if xbtn == XBUTTON1:
                            hk = "XButton1"
                        elif xbtn == XBUTTON2:
                            hk = "XButton2"
                        is_down = False

                    if hk and hk in self._mouse_hotkeys:
                        info = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                        if self._click_is_on_own_gui(info.pt.x, info.pt.y):
                            return user32.CallNextHookEx(0, nCode, wParam, lParam)
                        suppress = self._dispatch_mouse(hk, is_down)
            except Exception as e:
                print(f"[macro_engine] Mouse hook proc error: {e}")

            if suppress:
                return 1
            # hhk is ignored for low-level hooks; pass 0 to avoid reading self._mouse_hook under callback
            return user32.CallNextHookEx(0, nCode, wParam, lParam)

        self._mouse_hook_proc = HOOKPROC(_hook_proc)

        def _hook_thread():
            tid = kernel32.GetCurrentThreadId()
            hook = None

            msg = ctypes.wintypes.MSG()
            user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)

            cb_ptr = ctypes.cast(self._mouse_hook_proc, ctypes.c_void_p)
            hook = user32.SetWindowsHookExW(
                WH_MOUSE_LL,
                cb_ptr.value,
                kernel32.GetModuleHandleW(None),
                0,
            )
            if not hook:
                err = kernel32.GetLastError()
                print(f"[macro_engine] SetWindowsHookExW(WH_MOUSE_LL) failed: error {err}")
                with self._mouse_lock:
                    self._mouse_tid = None
                return

            with self._mouse_lock:
                self._mouse_hook = hook
                self._mouse_tid = tid

            try:
                if HAS_NATIVE and hasattr(_native, 'message_pump'):
                    _native.message_pump()
                else:
                    while not self._mouse_stop.is_set():
                        r = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                        if r <= 0 or msg.message == WM_QUIT:
                            break
                        user32.TranslateMessage(ctypes.byref(msg))
                        user32.DispatchMessageW(ctypes.byref(msg))
            except Exception as e:
                print(f"[macro_engine] Mouse hook thread error: {e}")
            finally:
                if hook:
                    user32.UnhookWindowsHookEx(hook)
                with self._mouse_lock:
                    self._mouse_hook = None
                    self._mouse_tid = None

        self._mouse_thread = threading.Thread(target=_hook_thread, daemon=True)
        self._mouse_thread.start()

    def _click_is_on_own_gui(self, x, y):
        pt = ctypes.wintypes.POINT()
        pt.x = x
        pt.y = y
        hwnd = user32.WindowFromPoint(pt)
        if not hwnd:
            return False
        pid = ctypes.wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return pid.value == kernel32.GetCurrentProcessId()

    def _dispatch_mouse(self, hk, is_down):
        m = self.profile.get(hk, {})
        if not m:
            return False
        if not game_detection.is_active():
            return False
        if macros_paused or not m.get("enabled", True):
            return False
        if m.get("holdMode", False):
            if is_down and not self._sending.is_set():
                self._on_down(hk)
                return True
            elif not is_down:
                self._on_up(hk)
                return True
        else:
            if is_down and not self._sending.is_set():
                self._on_press(hk)
                return True
        return False

    def cleanup(self):
        for hk in self._stop_flags:
            self._stop_flags[hk].value = 1

        # Signal mouse hook thread to stop and unhook itself
        self._mouse_stop.set()
        with self._mouse_lock:
            tid = self._mouse_tid

        if tid:
            user32.PostThreadMessageW(tid, WM_QUIT, 0, 0)

        # Wait for hook thread to finish (it will unhook itself)
        if self._mouse_thread:
            self._mouse_thread.join(timeout=5.0)
            if self._mouse_thread.is_alive():
                print("[macro_engine] Warning: mouse hook thread did not exit cleanly")
            self._mouse_thread = None

        with self._mouse_lock:
            self._mouse_hook = None
            self._mouse_tid = None
        self._mouse_hook_proc = None
        self._mouse_hotkeys.clear()

        for h in self._hotkey_handles:
            try:
                keyboard.remove_hotkey(h)
            except Exception as e:
                print(f"[macro_engine] remove_hotkey error: {e}")
        self._hotkey_handles.clear()

        for h in self._release_handles:
            try:
                keyboard.unhook(h)
            except Exception as e:
                print(f"[macro_engine] unhook error: {e}")
        self._release_handles.clear()

        with self._lock:
            for hk in list(self.running.keys()):
                self.running[hk] = False

        for t in list(self._hold_threads.values()):
            t.join(timeout=1.0)
        self._hold_threads.clear()

        self.profile.clear()
        self.running.clear()
        self._stop_flags.clear()

    def _ahk_to_kb_key(self, hk):
        mods = ""
        i = 0
        while i < len(hk) and hk[i] in "^!+#":
            if hk[i] == "^":
                mods += "ctrl+"
            elif hk[i] == "!":
                mods += "alt+"
            elif hk[i] == "+":
                mods += "shift+"
            elif hk[i] == "#":
                mods += "windows+"
            i += 1
        return mods + hk[i:].lower()

    def _kb_key_to_release(self, kb_key):
        parts = kb_key.split("+")
        return parts[-1]

    def _on_down(self, hk):
        if hk not in self.profile:
            return
        if self._sending.is_set():
            return
        if macros_paused or not self.profile[hk].get("enabled", True):
            if hk in input_handler.VK_MAP and hk not in MOUSE_KEYS:
                input_handler.send_key_down(hk)
            return
        if not game_detection.is_active():
            if hk in input_handler.VK_MAP and hk not in MOUSE_KEYS:
                input_handler.send_key_down(hk)
            return
        with self._lock:
            if self.running.get(hk, False):
                return
            self.running[hk] = True

        flag = self._stop_flags.get(hk)
        if flag is not None:
            flag.value = 0

        t = threading.Thread(target=self._hold_loop, args=(hk,), daemon=True)
        with self._lock:
            self._hold_threads[hk] = t
        t.start()

        self._notify()

    def _on_up(self, hk):
        if hk not in self.profile:
            return
        if macros_paused or not self.profile[hk].get("enabled", True):
            if hk in input_handler.VK_MAP and hk not in MOUSE_KEYS:
                input_handler.send_key_up(hk)
            return
        if not game_detection.is_active():
            if hk in input_handler.VK_MAP and hk not in MOUSE_KEYS:
                input_handler.send_key_up(hk)
            return
        flag = self._stop_flags.get(hk)
        if flag is not None:
            flag.value = 1
        with self._lock:
            if hk in self.running:
                self.running[hk] = False
        self._notify()

    def _on_press(self, hk):
        if hk not in self.profile:
            return
        if self._sending.is_set():
            return
        if macros_paused or not self.profile[hk].get("enabled", True):
            if hk in input_handler.VK_MAP and hk not in MOUSE_KEYS:
                input_handler.send_key(hk)
            return
        if not game_detection.is_active():
            if hk in input_handler.VK_MAP and hk not in MOUSE_KEYS:
                input_handler.send_key(hk)
            return
        threading.Thread(target=self._send_keys_once, args=(hk,), daemon=True).start()

    def _hold_loop(self, hk):
        utils.set_macro_thread_affinity()

        m = self.profile.get(hk)
        if not m:
            return

        keys = m.get("keys", [])
        if not keys:
            return

        interval = max(m.get("delay", 1), 1)
        ikd = m.get("interKeyDelay", 0)

        flag = self._stop_flags.get(hk)
        if flag is None:
            return

        flag.value = 0
        self._game_flag.value = 1 if game_detection.is_active() else 0

        needs_timer = interval > 5
        if needs_timer:
            timer_res.set_high_resolution()

        if HAS_NATIVE and hasattr(_native, 'hold_loop') and ikd == 0:
            _native.hold_loop(
                keys,
                float(interval),
                float(ikd),
                ctypes.addressof(flag),
                ctypes.addressof(self._game_flag),
            )
        elif HAS_NATIVE and hasattr(_native, 'send_wait'):
            self._hold_loop_sendwait(hk, m, flag)
        else:
            self._hold_loop_python(hk, m, flag)

        with self._lock:
            self.running[hk] = False
        if needs_timer:
            timer_res.restore_default()
        self._notify()

    def _hold_loop_sendwait(self, hk, m, flag):
        keys = m.get("keys", [])
        ikd = m.get("interKeyDelay", 0)
        interval = max(m.get("delay", 1), 1)

        while not flag.value and game_detection.is_active():
            _native.send_wait(
                keys, float(interval), float(ikd), ctypes.addressof(flag)
            )
            if flag.value:
                break
            for k in keys:
                self._check_buffs(k)
            if not game_detection.is_active():
                flag.value = 1
                break

    def _hold_loop_python(self, hk, m, flag):
        keys = m.get("keys", [])
        ikd = m.get("interKeyDelay", 0)
        interval = max(m.get("delay", 1), 1) / 1000.0

        while not flag.value:
            self._send_key_sequence(hk, m, keys, ikd, flag)
            if flag.value:
                break
            if not game_detection.is_active():
                flag.value = 1
                break
            if HAS_NATIVE:
                _native.precise_sleep(interval * 1000)
            else:
                time.sleep(interval)

    def _send_key_sequence(self, hk, m, keys, ikd, flag):
        self._acquire_sending()
        try:
            if ikd <= 0:
                input_handler.send_key_batch(keys)
                for k in keys:
                    self._check_buffs(k)
            else:
                first = True
                for k in keys:
                    if flag.value:
                        break
                    if not first and ikd > 0:
                        utils.precise_sleep(ikd)
                    first = False
                    input_handler.send_key(k)
                    self._check_buffs(k)
        finally:
            self._release_sending()

    def _send_keys_once(self, hk):
        try:
            utils.set_macro_thread_affinity()
            m = self.profile.get(hk)
            if not m:
                return
            keys = m.get("keys", [])
            ikd = m.get("interKeyDelay", 0)
            if not keys:
                return
            interval = max(m.get("delay", 1), 1)
            needs_timer = interval > 5
            if needs_timer:
                timer_res.set_high_resolution()
            if HAS_NATIVE and hasattr(_native, 'send_keys_once'):
                _native.send_keys_once(keys, float(ikd))
                for k in keys:
                    self._check_buffs(k)
            else:
                self._acquire_sending()
                try:
                    if ikd <= 0:
                        input_handler.send_key_batch(keys)
                        for k in keys:
                            self._check_buffs(k)
                    else:
                        first = True
                        for k in keys:
                            if not first and ikd > 0:
                                utils.precise_sleep(ikd)
                            first = False
                            input_handler.send_key(k)
                            self._check_buffs(k)
                finally:
                    self._release_sending()
            if needs_timer:
                timer_res.restore_default()
        finally:
            pass

    def _check_buffs(self, key):
        buffs_for_key = self._buff_map.get(key, [])
        if buffs_for_key:
            print(f"[macro_engine] _check_buffs key='{key}' found {len(buffs_for_key)} buff(s)")
        for b in buffs_for_key:
            buff_mod.buff_engine.activate(b)

    def setup_buff_map(self):
        self._buff_map = {}
        for b in config.get_buffs():
            if not b.get("enabled", True):
                continue
            if b.get("triggerType", "keys") == "pixel":
                continue
            for wk in b.get("watchKeys", []):
                self._buff_map.setdefault(wk, []).append(b)
        print(f"[macro_engine] Buff map built: {len(self._buff_map)} watch keys -> {[(k, [b['name'] for b in v]) for k, v in self._buff_map.items()]}")

    def update_game_flag(self, active):
        was = self._game_flag.value
        self._game_flag.value = 1 if active else 0
        if was != self._game_flag.value:
            if not active:
                self._stop_all_running()
            self._notify()

    def _stop_all_running(self):
        for hk in list(self._stop_flags.keys()):
            self._stop_flags[hk].value = 1
        with self._lock:
            for hk in list(self.running.keys()):
                self.running[hk] = False

    def release_hotkey(self, hk):
        flag = self._stop_flags.get(hk)
        if flag is not None:
            flag.value = 1
        was_running = False
        with self._lock:
            was_running = self.running.get(hk, False)
            if hk in self.running:
                self.running[hk] = False
        if was_running:
            self._notify()


macro_engine = MacroEngine()
