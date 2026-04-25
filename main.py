import sys
import os
import ctypes
import shutil
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_base = os.path.dirname(os.path.abspath(__file__))
_new_native = os.path.join(_base, '_native_new.pyd')
_native = os.path.join(_base, '_native.pyd')
if os.path.exists(_new_native):
    try:
        if os.path.exists(_native):
            os.remove(_native)
        shutil.copy2(_new_native, _native)
        os.remove(_new_native)
    except Exception:
        pass


def _is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _elevate():
    exe_dir = os.path.dirname(sys.executable)
    pythonw = os.path.join(exe_dir, "pythonw.exe")
    exe = pythonw if os.path.isfile(pythonw) else sys.executable
    script = os.path.abspath(__file__)
    ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, f'"{script}"', None, 1)


_SINGLE_INSTANCE_MUTEX = None


def _ensure_single_instance():
    global _SINGLE_INSTANCE_MUTEX
    _kernel32 = ctypes.windll.kernel32
    _ERROR_ALREADY_EXISTS = 183
    _SINGLE_INSTANCE_MUTEX = _kernel32.CreateMutexW(None, False, "JaidesMacroTool_SingleInstance")
    if ctypes.get_last_error() == _ERROR_ALREADY_EXISTS:
        try:
            _kernel32.CloseHandle(_SINGLE_INSTANCE_MUTEX)
        except Exception:
            pass
        print("[main] Another instance already running. Exiting.")
        sys.exit(0)


def main():
    verbose = "-v" in sys.argv or "--verbose" in sys.argv

    _ensure_single_instance()

    if not _is_admin():
        _elevate()
        sys.exit(0)

    from modules import timer_res
    from modules import perf_stats
    if verbose:
        perf_stats.enable()

    from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
    from PyQt6.QtGui import QAction, QIcon, QPixmap, QPainter, QColor, QFont, QBrush
    from PyQt6.QtCore import QTimer, Qt, QAbstractNativeEventFilter

    from modules import utils
    from modules import config_manager as config
    from modules.theme import theme
    from modules.gui import material_style
    from modules.gui.main_window import MainWindow
    from modules.macro_engine import macro_engine, macros_paused
    from modules import pixel_triggers
    from modules import game_detection
    from modules.buff_engine import buff_engine
    from modules.overlay import OverlayWindow

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Jaide's Macro Tool")
    app.setApplicationDisplayName("Jaide's Macro Tool")
    ctypes.windll.kernel32.SetConsoleTitleW("Jaide's Macro Tool")

    utils.init()
    config.load()
    material_style.apply_theme(app)

    window = MainWindow()
    icon_path = os.path.join(_base, "icon.ico")
    if os.path.exists(icon_path):
        from PyQt6.QtGui import QIcon
        window.setWindowIcon(QIcon(icon_path))
        app.setWindowIcon(QIcon(icon_path))

    game_detection.set_macro_hwnd(int(window.winId()))

    game_detection.start_window_check(app)
    game_detection.start_auto_detect(app)
    game_detection.check_window()

    macro_engine.setup()
    pixel_triggers.setup()

    overlay = OverlayWindow()
    overlay.show()
    app._overlay = overlay

    if verbose:
        from modules import debug_server
        debug_server.init(overlay, window)
        debug_server.start()
        perf_stats.start_watchdog(5)

    from modules.overlay import _TOGGLE_VK_MAP

    _user32 = ctypes.windll.user32
    _LOCK_KEYS = {"ScrollLock", "CapsLock", "NumLock"}
    _WM_HOTKEY = 0x0312
    _MOD_NOREPEAT = 0x4000
    _TOGGLE_HOTKEY_ID = 1

    _TOGGLE_KB_MAP = {
        "ScrollLock": "scroll lock", "CapsLock": "caps lock", "NumLock": "num lock",
        "Pause": "pause", "PrintScreen": "print screen",
        "Insert": "insert", "Delete": "delete",
        "F1": "f1", "F2": "f2", "F3": "f3", "F4": "f4",
        "F5": "f5", "F6": "f6", "F7": "f7", "F8": "f8",
        "F9": "f9", "F10": "f10", "F11": "f11", "F12": "f12",
    }

    # --- Shared state (atomic reads/writes, no lock needed for single booleans) ---
    _macro_enabled = [True]
    _toggle_hook = [None]  # None, "register_hotkey", or keyboard hook handle
    _use_register_hotkey = [False]

    # --- Mouse toggle hook state ---
    _MOUSE_TOGGLE_KEYS = {"XButton1", "XButton2", "LButton", "RButton", "MButton"}
    _WH_MOUSE_LL = 14
    _WM_LBUTTONDOWN = 0x0201
    _WM_RBUTTONDOWN = 0x0204
    _WM_MBUTTONDOWN = 0x0208
    _WM_XBUTTONDOWN = 0x020B
    _WM_XBUTTONUP = 0x020C
    _XBUTTON1 = 1
    _XBUTTON2 = 2
    _WM_QUIT = 0x0012

    class _MSLLHOOKSTRUCT(ctypes.Structure):
        _fields_ = [
            ("pt", ctypes.wintypes.POINT),
            ("mouseData", ctypes.wintypes.DWORD),
            ("flags", ctypes.wintypes.DWORD),
            ("time", ctypes.wintypes.DWORD),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    _MOUSE_TOGGLE_HOOK = [None]
    _MOUSE_TOGGLE_PROC = [None]
    _MOUSE_TOGGLE_THREAD = [None]
    _MOUSE_TOGGLE_TID = [None]
    _MOUSE_TOGGLE_STOP = threading.Event()

    def _cleanup_mouse_toggle():
        _MOUSE_TOGGLE_STOP.set()
        tid = _MOUSE_TOGGLE_TID[0]
        hook = _MOUSE_TOGGLE_HOOK[0]
        if tid:
            try:
                _user32.PostThreadMessageW(tid, _WM_QUIT, 0, 0)
            except Exception:
                pass
        if hook:
            try:
                _user32.UnhookWindowsHookEx(hook)
            except Exception:
                pass
            _MOUSE_TOGGLE_HOOK[0] = None
        if _MOUSE_TOGGLE_THREAD[0]:
            _MOUSE_TOGGLE_THREAD[0].join(timeout=1.0)
            _MOUSE_TOGGLE_THREAD[0] = None
        _MOUSE_TOGGLE_TID[0] = None
        _MOUSE_TOGGLE_PROC[0] = None

    def _start_mouse_toggle_hook(key_name):
        _MOUSE_TOGGLE_STOP.clear()

        _DOWN_MAP = {
            "LButton": _WM_LBUTTONDOWN,
            "RButton": _WM_RBUTTONDOWN,
            "MButton": _WM_MBUTTONDOWN,
            "XButton1": _WM_XBUTTONDOWN,
            "XButton2": _WM_XBUTTONDOWN,
        }
        expected_down = _DOWN_MAP.get(key_name)

        _HOOKPROC = ctypes.CFUNCTYPE(
            ctypes.c_int,
            ctypes.c_int,
            ctypes.wintypes.WPARAM,
            ctypes.wintypes.LPARAM,
        )

        def _hook_proc(nCode, wParam, lParam):
            try:
                if nCode >= 0 and wParam == expected_down:
                    hk = None
                    if wParam == _WM_XBUTTONDOWN:
                        info = ctypes.cast(lParam, ctypes.POINTER(_MSLLHOOKSTRUCT)).contents
                        xbtn = info.mouseData >> 16
                        if xbtn == _XBUTTON1:
                            hk = "XButton1"
                        elif xbtn == _XBUTTON2:
                            hk = "XButton2"
                    else:
                        _WM_MAP = {
                            _WM_LBUTTONDOWN: "LButton",
                            _WM_RBUTTONDOWN: "RButton",
                            _WM_MBUTTONDOWN: "MButton",
                        }
                        hk = _WM_MAP.get(wParam)

                    if hk == key_name:
                        _on_toggle_key()
                        return 1  # suppress so game doesn't see it
            except Exception as e:
                print(f"[main] Mouse toggle hook error: {e}")
            return _user32.CallNextHookEx(0, nCode, wParam, lParam)

        _proc = _HOOKPROC(_hook_proc)
        _MOUSE_TOGGLE_PROC[0] = _proc

        def _hook_thread():
            tid = ctypes.windll.kernel32.GetCurrentThreadId()
            _MOUSE_TOGGLE_TID[0] = tid

            msg = ctypes.wintypes.MSG()
            _user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)

            cb_ptr = ctypes.cast(_proc, ctypes.c_void_p)
            hook = _user32.SetWindowsHookExW(
                _WH_MOUSE_LL,
                cb_ptr.value,
                ctypes.windll.kernel32.GetModuleHandleW(None),
                0,
            )
            if not hook:
                err = ctypes.windll.kernel32.GetLastError()
                print(f"[main] Mouse toggle hook failed: error {err}")
                _MOUSE_TOGGLE_TID[0] = None
                return

            _MOUSE_TOGGLE_HOOK[0] = hook

            try:
                while not _MOUSE_TOGGLE_STOP.is_set():
                    r = _user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                    if r <= 0 or msg.message == _WM_QUIT:
                        break
                    _user32.TranslateMessage(ctypes.byref(msg))
                    _user32.DispatchMessageW(ctypes.byref(msg))
            except Exception as e:
                print(f"[main] Mouse toggle thread error: {e}")
            finally:
                if hook:
                    _user32.UnhookWindowsHookEx(hook)
                _MOUSE_TOGGLE_HOOK[0] = None
                _MOUSE_TOGGLE_TID[0] = None

        t = threading.Thread(target=_hook_thread, daemon=True)
        _MOUSE_TOGGLE_THREAD[0] = t
        t.start()

    def _update_ui():
        import modules.macro_engine as me
        game_active = game_detection.window_active
        only_in_game = config.data.get("settings", {}).get("onlyInGame", True)
        effective_active = game_active or not only_in_game

        on = _macro_enabled[0] if effective_active else False

        overlay._toggle_on = on
        overlay._toggle_key = config.data.get("settings", {}).get("toggleKey", "ScrollLock")

        me.macros_paused = not on
        me.macro_engine.update_game_flag(effective_active)

        overlay.notify()
        window._update_status()

    def _on_toggle_key(e=None):
        key_name = config.data.get("settings", {}).get("toggleKey", "ScrollLock")

        if key_name in _LOCK_KEYS:
            vk = _TOGGLE_VK_MAP.get(key_name, 0x91)
            lock = bool(_user32.GetKeyState(vk) & 0x0001)
            _macro_enabled[0] = lock
        else:
            _macro_enabled[0] = not _macro_enabled[0]

        import modules.macro_engine as me
        me.macros_paused = not _macro_enabled[0]

        try:
            overlay._toggle_on = _macro_enabled[0]
            overlay._toggle_key = key_name
            overlay.notify()
        except RuntimeError:
            pass

    class _ToggleHotkeyFilter(QAbstractNativeEventFilter):
        def nativeEventFilter(self, eventType, message):
            if eventType == b"windows_generic_MSG":
                try:
                    msg = ctypes.wintypes.MSG.from_address(int(message))
                    if msg.message == _WM_HOTKEY and msg.wParam == _TOGGLE_HOTKEY_ID:
                        _on_toggle_key()
                        return True, 0
                except Exception:
                    pass
            return False, 0

    _hotkey_filter = _ToggleHotkeyFilter()
    app.installNativeEventFilter(_hotkey_filter)

    def _cleanup_toggle_hook():
        _cleanup_mouse_toggle()
        if _use_register_hotkey[0]:
            _user32.UnregisterHotKey(None, _TOGGLE_HOTKEY_ID)
            _use_register_hotkey[0] = False
        if _toggle_hook[0] and _toggle_hook[0] != "register_hotkey":
            try:
                import keyboard
                keyboard.unhook(_toggle_hook[0])
            except Exception:
                pass
        _toggle_hook[0] = None

    def setup_toggle_hook():
        _cleanup_toggle_hook()

        key_name = config.data.get("settings", {}).get("toggleKey", "ScrollLock")

        if key_name in _MOUSE_TOGGLE_KEYS:
            _start_mouse_toggle_hook(key_name)
            return

        if key_name not in _LOCK_KEYS:
            vk = _TOGGLE_VK_MAP.get(key_name, 0)
            if vk and _user32.RegisterHotKey(None, _TOGGLE_HOTKEY_ID, _MOD_NOREPEAT, vk):
                _toggle_hook[0] = "register_hotkey"
                _use_register_hotkey[0] = True
                return

        import keyboard
        kb_name = _TOGGLE_KB_MAP.get(key_name, key_name.lower())
        _toggle_hook[0] = keyboard.on_press_key(kb_name, _on_toggle_key, suppress=False)

    app._setup_toggle_hook = setup_toggle_hook
    setup_toggle_hook()

    def _on_macro_state():
        try:
            overlay.notify()
        except RuntimeError:
            pass

    macro_engine.register_callback(_on_macro_state)

    def _on_game_active(active):
        _update_ui()

    game_detection.register_active_callback(_on_game_active)

    _update_ui()

    window.show()

    def cleanup():
        _cleanup_toggle_hook()
        macro_engine.cleanup()
        pixel_triggers.stop()
        buff_engine.stop()
        overlay.close()
        tray.hide()
        from modules import timer_res
        timer_res.restore_default()

    app.aboutToQuit.connect(cleanup)

    tray = QSystemTrayIcon()
    tray_pixmap = QPixmap(32, 32)
    tray_pixmap.fill(Qt.GlobalColor.transparent)
    tp = QPainter(tray_pixmap)
    tp.setRenderHint(QPainter.RenderHint.Antialiasing)
    tp.setBrush(QBrush(QColor(theme.get("primary"))))
    tp.setPen(Qt.PenStyle.NoPen)
    tp.drawRoundedRect(4, 4, 24, 24, 6, 6)
    tp.setBrush(QBrush(QColor(theme.get("onPrimary"))))
    tp.drawRoundedRect(10, 10, 12, 12, 3, 3)
    tp.end()
    tray.setIcon(QIcon(tray_pixmap))
    tray.setToolTip("Jaide's Macro Tool")

    from modules.gui.nerd_font import ICONS

    tray_menu = QMenu()
    show_action = tray_menu.addAction("Show / Hide")
    reload_action = tray_menu.addAction(ICONS.RELOAD + "  Reload")
    tray_menu.addSeparator()
    quit_action = tray_menu.addAction("Quit")

    def _tray_toggle():
        if window.isVisible():
            window.hide()
        else:
            window.show()
            window.activateWindow()
            window.raise_()

    def _reload():
        cleanup()
        import subprocess
        subprocess.Popen([sys.executable] + sys.argv)
        sys.exit(0)

    show_action.triggered.connect(_tray_toggle)
    reload_action.triggered.connect(_reload)
    quit_action.triggered.connect(app.quit)
    tray.setContextMenu(tray_menu)
    tray.activated.connect(lambda reason: _tray_toggle() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
    tray.show()

    code = app.exec()
    cleanup()
    sys.exit(code)


if __name__ == "__main__":
    main()
