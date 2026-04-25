"""
Test suite for macro app startup and overlay functionality.
Run with: python tests/test_app.py
"""
import sys
import os
import time
import threading
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestImports(unittest.TestCase):
    """Test that all modules can be imported."""

    def test_pyqt6(self):
        from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QSizePolicy
        from PyQt6.QtCore import Qt, QTimer
        from PyQt6.QtGui import QPainter, QColor, QFont

    def test_config_manager(self):
        from modules import config_manager as config

    def test_theme(self):
        from modules.theme import theme

    def test_overlay(self):
        from modules.overlay import OverlayWindow, _TOGGLE_VK_MAP

    def test_macro_engine(self):
        from modules.macro_engine import macro_engine, macros_paused

    def test_game_detection(self):
        from modules import game_detection

    def test_pixel_triggers(self):
        from modules import pixel_triggers

    def test_utils(self):
        from modules import utils

    def test_input_handler(self):
        from modules import input_handler

    def test_buff_engine(self):
        from modules.buff_engine import buff_engine

    def test_debug_server(self):
        from modules import debug_server

    def test_main_window(self):
        from modules.gui.main_window import MainWindow


class TestConfigManager(unittest.TestCase):
    """Test config loading and data access."""

    @classmethod
    def setUpClass(cls):
        from modules import config_manager as config
        config.load()
        cls.config = config

    def test_config_loaded(self):
        self.assertIn("settings", self.config.data)

    def test_toggle_key(self):
        key = self.config.data["settings"].get("toggleKey", "ScrollLock")
        self.assertIsInstance(key, str)
        self.assertTrue(len(key) > 0)

    def test_get_macros(self):
        macros = self.config.get_macros()
        self.assertIsInstance(macros, list)

    def test_get_pixels(self):
        pixels = self.config.get_pixels()
        self.assertIsInstance(pixels, list)

    def test_get_buffs(self):
        buffs = self.config.get_buffs()
        self.assertIsInstance(buffs, list)


class TestOverlayWidget(unittest.TestCase):
    """Test overlay creation, rebuild, and sizing."""

    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        if not QApplication.instance():
            cls._app = QApplication(sys.argv)
        else:
            cls._app = QApplication.instance()

        from modules import config_manager as config
        config.load()
        from modules.overlay import OverlayWindow
        cls.overlay = OverlayWindow()

    def test_overlay_created(self):
        self.assertEqual(self.overlay.width(), 220)
        self.assertGreater(self.overlay.height(), 0)

    def test_overlay_has_header(self):
        layout = self.overlay.layout()
        self.assertGreaterEqual(layout.count(), 2,
                                "Should have at least header_row and separator")

    def test_overlay_dynamic_widgets_populated(self):
        self.assertGreater(len(self.overlay._dynamic_widgets), 0,
                           "Should have dynamic widgets from config")

    def test_overlay_toggle_vk_map(self):
        from modules.overlay import _TOGGLE_VK_MAP
        self.assertIn("ScrollLock", _TOGGLE_VK_MAP)
        self.assertIn("F1", _TOGGLE_VK_MAP)
        self.assertIn("NumLock", _TOGGLE_VK_MAP)

    def test_rebuild_preserves_layout_count(self):
        layout = self.overlay.layout()
        count_before = layout.count()
        dynamic_before = len(self.overlay._dynamic_widgets)

        self.overlay._rebuild_lines()

        count_after = layout.count()
        dynamic_after = len(self.overlay._dynamic_widgets)

        self.assertEqual(count_before, count_after,
                         f"Layout count changed: {count_before} -> {count_after}")
        self.assertEqual(dynamic_before, dynamic_after,
                         f"Dynamic widget count changed: {dynamic_before} -> {dynamic_after}")

    def test_rebuild_widget_names_match(self):
        from modules import config_manager as config

        self.overlay._rebuild_lines()

        macro_names = [m.get("name", "") for m, _ in self.overlay._macro_lines]
        expected_macros = [m.get("name", "") for m in config.get_macros()]
        self.assertEqual(macro_names, expected_macros)

        buff_names = [b.get("name", "") for b, _ in self.overlay._buff_lines]
        expected_buffs = [b.get("name", "") for b in config.get_buffs()]
        self.assertEqual(buff_names, expected_buffs)

    def test_rebuild_does_not_duplicate(self):
        self.overlay._rebuild_lines()
        count1 = self.overlay.layout().count()
        dyn1 = len(self.overlay._dynamic_widgets)

        self.overlay._rebuild_lines()
        count2 = self.overlay.layout().count()
        dyn2 = len(self.overlay._dynamic_widgets)

        self.overlay._rebuild_lines()
        count3 = self.overlay.layout().count()
        dyn3 = len(self.overlay._dynamic_widgets)

        self.assertEqual(count1, count2, "Second rebuild changed layout count")
        self.assertEqual(count2, count3, "Third rebuild changed layout count")
        self.assertEqual(dyn1, dyn2, "Second rebuild changed dynamic count")
        self.assertEqual(dyn2, dyn3, "Third rebuild changed dynamic count")

    def test_refresh_macros_preserves_size(self):
        h_before = self.overlay.height()
        self.overlay.refresh_macros()
        h_after = self.overlay.height()
        self.assertEqual(h_before, h_after,
                         f"Height changed after refresh_macros: {h_before} -> {h_after}")

    def test_notify_does_not_crash(self):
        self.overlay.notify()

    def test_do_update_does_not_crash(self):
        self.overlay._do_update()

    def test_widget_sizes_reasonable(self):
        for item, lbl in self.overlay._macro_lines:
            sh = lbl.sizeHint()
            self.assertGreater(sh.height(), 5,
                               f"Label '{item.get('name')}' sizeHint height too small: {sh.height()}")
            self.assertGreater(sh.width(), 5,
                               f"Label '{item.get('name')}' sizeHint width too small: {sh.width()}")

    def test_no_orphan_widgets_in_layout(self):
        layout = self.overlay.layout()
        all_widgets = []
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget():
                all_widgets.append(item.widget())
            elif item and item.layout():
                sub = item.layout()
                for j in range(sub.count()):
                    si = sub.itemAt(j)
                    if si and si.widget():
                        all_widgets.append(si.widget())

        dynamic_set = set(id(w) for w in self.overlay._dynamic_widgets)
        static_widgets = [
            self.overlay._status_dot, self.overlay._title,
            self.overlay._game_dot, self.overlay._profile_label,
            self.overlay._sep,
        ]
        static_set = set(id(w) for w in static_widgets)

        for w in all_widgets:
            wid = id(w)
            in_dynamic = wid in dynamic_set
            in_static = wid in static_set
            self.assertTrue(in_dynamic or in_static,
                            f"Widget {type(w).__name__} in layout but not tracked (dynamic or static)")


class TestToggleLogic(unittest.TestCase):
    """Test toggle key mapping and state logic."""

    def test_toggle_kb_map_coverage(self):
        from modules.overlay import _TOGGLE_VK_MAP
        expected_keys = ["ScrollLock", "CapsLock", "NumLock", "Pause", "PrintScreen",
                         "Insert", "Delete"] + [f"F{i}" for i in range(1, 13)]
        for key in expected_keys:
            self.assertIn(key, _TOGGLE_VK_MAP,
                          f"Missing VK mapping for {key}")

    def test_lock_keys_set(self):
        LOCK_KEYS = {"ScrollLock", "CapsLock", "NumLock"}
        self.assertEqual(len(LOCK_KEYS), 3)

    def test_toggle_kb_map_values(self):
        _TOGGLE_KB_MAP = {
            "ScrollLock": "scroll lock", "CapsLock": "caps lock", "NumLock": "num lock",
            "Pause": "pause", "PrintScreen": "print screen",
            "Insert": "insert", "Delete": "delete",
            "F1": "f1", "F2": "f2", "F3": "f3", "F4": "f4",
            "F5": "f5", "F6": "f6", "F7": "f7", "F8": "f8",
            "F9": "f9", "F10": "f10", "F11": "f11", "F12": "f12",
        }
        for key, kb_name in _TOGGLE_KB_MAP.items():
            self.assertIsInstance(kb_name, str)
            self.assertTrue(len(kb_name) > 0, f"Empty kb_name for {key}")


class TestMacroEngine(unittest.TestCase):
    """Test macro engine core logic — routing, hold/release, and game detection."""

    def setUp(self):
        from modules.macro_engine import MacroEngine, MOUSE_VK_MAP
        from modules import game_detection
        import ctypes
        import threading

        self.engine = MacroEngine()
        self.MOUSE_VK_MAP = MOUSE_VK_MAP
        self.game_detection = game_detection

        self.hold_macro = {
            "name": "HoldTest", "hotkey": "RButton", "delay": 10,
            "holdMode": True, "interKeyDelay": 0, "enabled": True,
            "keys": ["b", "r"],
        }
        self.hold_macro_ikd = {
            "name": "HoldIKDTest", "hotkey": "XButton1", "delay": 10,
            "holdMode": True, "interKeyDelay": 2, "enabled": True,
            "keys": ["v", "g", "t"],
        }
        self.press_macro = {
            "name": "PressTest", "hotkey": "RButton", "delay": 10,
            "holdMode": False, "interKeyDelay": 0, "enabled": True,
            "keys": ["b", "r", "t"],
        }

        self.sent_keys = []
        self._orig_send = None
        self._orig_send_down = None
        self._orig_send_up = None
        self._orig_send_batch = None
        self._orig_paused = None
        self._orig_active = None

    def _mock_input(self):
        from modules import input_handler
        self.sent_keys = []

        self._orig_send = getattr(input_handler, 'send_key', None)
        self._orig_send_down = getattr(input_handler, 'send_key_down', None)
        self._orig_send_up = getattr(input_handler, 'send_key_up', None)
        self._orig_send_batch = getattr(input_handler, 'send_key_batch', None)

        input_handler.send_key = lambda k: self.sent_keys.append(("key", k))
        input_handler.send_key_down = lambda k: self.sent_keys.append(("down", k))
        input_handler.send_key_up = lambda k: self.sent_keys.append(("up", k))
        input_handler.send_key_batch = lambda ks: self.sent_keys.append(("batch", ks))

    def _restore_input(self):
        from modules import input_handler
        if self._orig_send:
            input_handler.send_key = self._orig_send
        if self._orig_send_down:
            input_handler.send_key_down = self._orig_send_down
        if self._orig_send_up:
            input_handler.send_key_up = self._orig_send_up
        if self._orig_send_batch:
            input_handler.send_key_batch = self._orig_send_batch

    def _force_active(self, active=True):
        import modules.macro_engine as me
        import modules.game_detection as gd
        self._orig_paused = me.macros_paused
        self._orig_active = gd.window_active
        me.macros_paused = False
        gd.window_active = active

    def _restore_state(self):
        import modules.macro_engine as me
        import modules.game_detection as gd
        me.macros_paused = self._orig_paused
        gd.window_active = self._orig_active

    def tearDown(self):
        self._restore_input()
        if self._orig_paused is not None:
            self._restore_state()
        self.engine.cleanup()

    def test_mouse_poll_routes_hold_mode_to_on_down(self):
        """Hold-mode mouse macros should call _on_down on press."""
        import threading
        import ctypes

        hk = "RButton"
        self.engine.profile[hk] = self.hold_macro
        self.engine.running[hk] = False
        self.engine._stop_flags[hk] = ctypes.c_int(1)
        self.engine._game_flag = ctypes.c_int(1)

        self._force_active(True)
        self._mock_input()

        started = threading.Event()
        orig_on_down = self.engine._on_down
        def mock_on_down(h):
            started.set()
        self.engine._on_down = mock_on_down

        self.engine._mouse_hotkeys = {hk: True}
        self.engine._dispatch_mouse(hk, is_down=True)

        self.assertTrue(started.wait(timeout=1.0), "_on_down was not called for hold-mode macro")
        self.engine._on_down = orig_on_down

    def test_mouse_poll_routes_press_mode_to_on_press(self):
        """Non-hold-mode mouse macros should call _on_press, not _on_down."""
        import threading
        import ctypes

        hk = "RButton"
        self.engine.profile[hk] = self.press_macro
        self.engine.running[hk] = False
        self.engine._stop_flags[hk] = ctypes.c_int(1)

        self._force_active(True)

        press_called = threading.Event()
        orig_on_press = self.engine._on_press
        def mock_on_press(h):
            press_called.set()
        self.engine._on_press = mock_on_press

        self.engine._mouse_hotkeys = {hk: True}
        self.engine._dispatch_mouse(hk, is_down=True)

        self.assertTrue(press_called.wait(timeout=1.0), "_on_press was not called for non-hold macro")
        self.engine._on_press = orig_on_press

    def test_mouse_poll_detects_release_during_sending(self):
        """Release detection must work even when _sending is True."""
        import threading
        import ctypes

        hk = "RButton"
        self.engine.profile[hk] = self.hold_macro
        self.engine.running[hk] = False
        self.engine._stop_flags[hk] = ctypes.c_int(1)
        self.engine._game_flag = ctypes.c_int(1)

        self._force_active(True)

        up_called = threading.Event()
        orig_on_up = self.engine._on_up
        def mock_on_up(h):
            up_called.set()
        self.engine._on_up = mock_on_up

        self.engine._mouse_hotkeys = {hk: True}

        self.engine._sending = True

        self.engine._dispatch_mouse(hk, is_down=False)

        self.assertTrue(up_called.wait(timeout=1.0),
                        "_on_up not called when _sending=True — release blocked by sending guard")

        self.engine._sending = False
        self.engine._on_up = orig_on_up

    def test_on_down_starts_hold_loop(self):
        """_on_down should set running=True and clear the stop flag for hold macros."""
        import ctypes

        hk = "RButton"
        self.engine.profile[hk] = self.hold_macro
        self.engine._stop_flags[hk] = ctypes.c_int(1)
        self.engine._game_flag = ctypes.c_int(1)

        self._force_active(True)
        self._mock_input()

        orig_hold_loop = self.engine._hold_loop
        block = threading.Event()
        def mock_hold_loop(h):
            block.wait(timeout=2.0)
        self.engine._hold_loop = mock_hold_loop

        self.engine._on_down(hk)
        self.assertTrue(self.engine.running.get(hk, False), "running[hk] not set after _on_down")
        self.assertEqual(self.engine._stop_flags[hk].value, 0, "stop flag should be 0 after _on_down")

        block.set()
        self.engine._hold_loop = orig_hold_loop

    def test_on_up_stops_hold_loop(self):
        """_on_up should set stop flag and mark running as False."""
        import ctypes

        hk = "RButton"
        self.engine.profile[hk] = self.hold_macro
        self.engine.running[hk] = True
        self.engine._stop_flags[hk] = ctypes.c_int(0)

        self._force_active(True)

        self.engine._on_up(hk)
        self.assertEqual(self.engine._stop_flags[hk].value, 1, "stop flag should be 1 after _on_up")
        self.assertFalse(self.engine.running.get(hk, False), "running[hk] should be False after _on_up")

    def test_on_press_starts_fire_once_thread(self):
        """_on_press should spawn a thread for non-hold macros."""
        import ctypes

        hk = "RButton"
        self.engine.profile[hk] = self.press_macro

        self._force_active(True)

        thread_started = threading.Event()
        orig = self.engine._send_keys_once
        def mock_send(h):
            thread_started.set()
        self.engine._send_keys_once = mock_send

        self.engine._on_press(hk)

        self.assertTrue(thread_started.wait(timeout=1.0),
                        "_send_keys_once was not called for press macro")
        self.engine._send_keys_once = orig

    def test_on_down_blocked_when_paused(self):
        """_on_down should passthrough (not start loop) when macros_paused."""
        import modules.macro_engine as me

        hk = "RButton"
        self.engine.profile[hk] = self.hold_macro

        self._force_active(True)
        me.macros_paused = True
        self._mock_input()

        self.engine._on_down(hk)
        self.assertFalse(self.engine.running.get(hk, False), "Macro should not start when paused")

        me.macros_paused = False

    def test_on_press_blocked_when_paused(self):
        """_on_press should passthrough when macros_paused."""
        import modules.macro_engine as me

        hk = "RButton"
        self.engine.profile[hk] = self.press_macro

        self._force_active(True)
        me.macros_paused = True
        self._mock_input()

        self.engine._on_press(hk)
        time.sleep(0.2)
        for kind, k in self.sent_keys:
            self.assertNotEqual(kind, "batch",
                                "send_key_batch should not be called when paused")

        me.macros_paused = False

    def test_on_down_blocked_when_game_inactive(self):
        """_on_down should passthrough when game is not active and onlyInGame is on."""
        hk = "RButton"
        self.engine.profile[hk] = self.hold_macro

        self._force_active(False)

        self.engine._on_down(hk)
        self.assertFalse(self.engine.running.get(hk, False),
                         "Macro should not start when game inactive")

    def test_hold_loop_uses_sendwait_with_ikd(self):
        """Macros with interKeyDelay > 0 should use _hold_loop_sendwait when native available."""
        import ctypes

        hk = "XButton1"
        self.engine.profile[hk] = self.hold_macro_ikd
        self.engine._stop_flags[hk] = ctypes.c_int(0)
        self.engine._game_flag = ctypes.c_int(1)

        self._force_active(True)

        try:
            import _native
            has_send_wait = hasattr(_native, 'send_wait')
        except ImportError:
            has_send_wait = False

        sendwait_called = []
        orig_sendwait = getattr(self.engine, '_hold_loop_sendwait', None)
        def mock_sendwait(h, m, f):
            sendwait_called.append(True)
        self.engine._hold_loop_sendwait = mock_sendwait

        python_called = []
        orig_python = getattr(self.engine, '_hold_loop_python', None)
        def mock_python(h, m, f):
            python_called.append(True)
        self.engine._hold_loop_python = mock_python

        self.engine._hold_loop(hk)

        if has_send_wait:
            self.assertTrue(len(sendwait_called) > 0,
                            "Should use _hold_loop_sendwait for ikd>0 with native")
        else:
            self.assertTrue(len(python_called) > 0,
                            "Should use _hold_loop_python when native unavailable")

        self.engine._hold_loop_sendwait = orig_sendwait
        self.engine._hold_loop_python = orig_python

    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        if not QApplication.instance():
            cls._app = QApplication(sys.argv)
        else:
            cls._app = QApplication.instance()

    def test_game_detection_timers_created(self):
        """start_window_check / start_auto_detect should create timers if missing."""
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        self.assertIsNotNone(app, "QApplication must exist for timer tests")

        from modules import game_detection

        if hasattr(app, '_gd_check_timer'):
            delattr(app, '_gd_check_timer')
        if hasattr(app, '_gd_detect_timer'):
            delattr(app, '_gd_detect_timer')

        game_detection.start_window_check(app)
        game_detection.start_auto_detect(app)

        self.assertTrue(hasattr(app, '_gd_check_timer'),
                        "start_window_check did not create _gd_check_timer")
        self.assertTrue(hasattr(app, '_gd_detect_timer'),
                        "start_auto_detect did not create _gd_detect_timer")
        self.assertTrue(app._gd_check_timer.isActive(),
                        "Game check timer should be active")
        self.assertTrue(app._gd_detect_timer.isActive(),
                        "Auto-detect timer should be active")

    def test_game_detection_callback_fires_on_change(self):
        """Active callback should fire when window_active changes."""
        from modules import game_detection
        import threading

        calls = []
        def cb(active):
            calls.append(active)

        game_detection._active_callbacks.append(cb)
        old = game_detection.window_active

        game_detection.window_active = not old
        game_detection._notify_active_change()
        self.assertTrue(len(calls) > 0, "Callback should have been called")
        self.assertEqual(calls[-1], not old)

        game_detection.window_active = old
        game_detection._notify_active_change()
        game_detection._active_callbacks.remove(cb)


class TestSyntaxAllFiles(unittest.TestCase):
    """Compile-check all Python files."""

    def test_all_files_compile(self):
        import py_compile
        root = os.path.join(os.path.dirname(__file__), '..')
        files = [
            'main.py',
            'modules/config_manager.py',
            'modules/game_detection.py',
            'modules/overlay.py',
            'modules/macro_engine.py',
            'modules/pixel_triggers.py',
            'modules/input_handler.py',
            'modules/buff_engine.py',
            'modules/utils.py',
            'modules/theme.py',
            'modules/debug_server.py',
            'modules/gui/main_window.py',
            'modules/gui/material_style.py',
            'modules/gui/macro_editor.py',
            'modules/gui/pixel_editor.py',
            'modules/gui/buff_editor.py',
            'modules/gui/spec_detect_editor.py',
            'modules/pixel_picker.py',
            'modules/perf_stats.py',
        ]
        for f in files:
            path = os.path.join(root, f)
            if os.path.exists(path):
                with self.subTest(file=f):
                    py_compile.compile(path, doraise=True)
            else:
                self.fail(f"File not found: {f}")




if __name__ == "__main__":
    unittest.main(verbosity=2)
