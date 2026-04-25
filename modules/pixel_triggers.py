import ctypes
import ctypes.wintypes
import threading
import time
import struct

from modules import config_manager as config
from modules import input_handler
from modules import utils
from modules import game_detection
from modules import buff_engine as buff_mod
from modules.macro_engine import macro_engine
from modules import perf_stats

try:
    import _native
    HAS_NATIVE = True
except ImportError:
    HAS_NATIVE = False

try:
    from modules import numba_utils as nu
    HAS_NUMBA = nu.HAS_NUMBA
except ImportError:
    HAS_NUMBA = False
    nu = None

_triggers = []
_px_buffs = []
_stop_event = threading.Event()
_thread = None
_check_interval = 0.004
_last_check_time = 0.0
# Shared capture state for batched pixel checking (reduces BitBlt calls)
_capture = {"screen_hdc": None, "mem_hdc": None, "bmp": None, "bmp_old": None,
            "minx": 0, "miny": 0, "w": 0, "h": 0, "valid": False}

_last_cur = None
_last_cur_time = 0.0

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32


def _get_check_interval():
    rate = config.data.get("settings", {}).get("pixelCheckRate", 250)
    rate = max(10, min(1000, int(rate)))
    return 1.0 / rate


def setup():
    global _triggers, _px_buffs, _stop_event, _thread, _check_interval

    _stop_event.set()
    if _thread and _thread.is_alive():
        _thread.join(timeout=3.0)

    _check_interval = _get_check_interval()
    print(f"[pixel_triggers] Check rate: {1.0 / _check_interval:.0f}/s, "
          f"interval: {_check_interval * 1000:.1f}ms")

    _triggers = config.get_pixels()
    for t in _triggers:
        t.setdefault("lastFired", 0)
        t["actionKey"] = t.get("actionKey", t.get("key", ""))
        t["_scaled"] = None
        t["_scaledRes"] = None
        anchor = t.get("anchor")
        if anchor and anchor.get("pixels"):
            anchor["_scaled"] = None
            anchor["_scaledRes"] = None
        blocker = t.get("blocker")
        if blocker and blocker.get("pixels"):
            blocker["_scaled"] = None
            blocker["_scaledRes"] = None

    _px_buffs = []
    for b in config.get_buffs():
        if b.get("triggerType") == "pixel" and b.get("enabled", True):
            b["actionKey"] = b.get("actionKey", b.get("key", ""))
            b["_scaled"] = None
            b["_scaledRes"] = None
            b["pxMatched"] = False
            _px_buffs.append(b)
    print(f"[pixel_triggers] Setup: {len(_triggers)} triggers, {len(_px_buffs)} pixel buffs "
          f"(names: {[b.get('name', '?') for b in _px_buffs]})")

    _stop_event = threading.Event()
    _thread = None

    if _triggers or _px_buffs:
        _thread = threading.Thread(target=_poll_loop, daemon=True)
        _thread.start()


def _poll_loop():
    if HAS_NATIVE and hasattr(_native, 'set_thread_priority'):
        _native.set_thread_priority(2)
    else:
        try:
            ctypes.windll.kernel32.SetThreadPriority(
                ctypes.windll.kernel32.GetCurrentThread(), 2
            )
        except Exception:
            pass
    try:
        ctypes.windll.winmm.timeBeginPeriod(1)
    except Exception:
        pass
    ls = perf_stats.loop_stat("pixel_poll", _check_interval)
    next_tick = time.perf_counter()
    while not _stop_event.is_set():
        t0 = perf_stats._perf()
        try:
            _check()
        except Exception as e:
            print(f"[pixel_triggers] Poll loop check error: {e}")
        if ls is not None:
            elapsed_ns = int((perf_stats._perf() - t0) * 1e9)
            ls.record(elapsed_ns)
            perf_stats.record("pixel_check", elapsed_ns)
        # Stable timing: compute next tick based on ideal interval, not elapsed
        next_tick += _check_interval
        now = time.perf_counter()
        sleep_time = next_tick - now
        if sleep_time > 0:
            time.sleep(sleep_time)
        else:
            # If we're behind, reset to avoid catching-up burst
            next_tick = now + _check_interval
    try:
        ctypes.windll.winmm.timeEndPeriod(1)
    except Exception:
        pass


def _get_cached_resolution():
    global _last_cur, _last_cur_time
    now = time.time()
    if _last_cur is None or now - _last_cur_time > 2.0:
        _last_cur = utils.get_screen_resolution()
        _last_cur_time = now
    return _last_cur


def _get_scaled(t, cur):
    cache_key = (cur.get("w", 0), cur.get("h", 0))
    if t.get("_scaledRes") == cache_key and t.get("_scaled") is not None:
        return t["_scaled"]

    capture_res = t.get("captureRes")
    raw = t.get("pixels", [])
    scaled = utils.scale_pixels(raw, capture_res, cur)
    t["_scaled"] = scaled
    t["_scaledRes"] = cache_key
    return scaled


def _get_anchor_scaled(anchor, capture_res, cur):
    cache_key = (cur.get("w", 0), cur.get("h", 0))
    if anchor.get("_scaledRes") == cache_key and anchor.get("_scaled") is not None:
        return anchor["_scaled"]

    scaled = utils.scale_pixels(anchor.get("pixels", []), capture_res, cur)
    anchor["_scaled"] = scaled
    anchor["_scaledRes"] = cache_key
    return scaled


def _get_blocker_scaled(blocker, capture_res, cur):
    cache_key = (cur.get("w", 0), cur.get("h", 0))
    if blocker.get("_scaledRes") == cache_key and blocker.get("_scaled") is not None:
        return blocker["_scaled"]

    scaled = utils.scale_pixels(blocker.get("pixels", []), capture_res, cur)
    blocker["_scaled"] = scaled
    blocker["_scaledRes"] = cache_key
    return scaled


def _get_buff_scaled(b, cur):
    cache_key = (cur.get("w", 0), cur.get("h", 0))
    if b.get("_scaledRes") == cache_key and b.get("_scaled") is not None:
        return b["_scaled"]

    capture_res = b.get("captureRes")
    pixels = b.get("triggerPixels", [])
    scaled = utils.scale_pixels(pixels, capture_res, cur)
    b["_scaled"] = scaled
    b["_scaledRes"] = cache_key
    return scaled


def _check():
    global _last_check_time
    if not game_detection.is_active():
        return
    if not _triggers and not _px_buffs:
        return

    # Guard: don't interfere with input injection (prevents stutter during key sends)
    if macro_engine._sending.is_set():
        return

    now = time.time() * 1000
    _last_check_time = now
    cur = _get_cached_resolution()

    hdc = user32.GetDC(0)
    if not hdc:
        return
    try:
        for t in _triggers:
            if _stop_event.is_set():
                return
            if not t.get("enabled", True):
                continue
            if now - t.get("lastFired", 0) < t.get("cooldown", 1000):
                continue

            mode = t.get("triggerMode", "macro")
            if mode == "macro":
                mhk = t.get("macroHotkey", "")
                if not mhk:
                    any_running = any(macro_engine.running.values())
                    if not any_running:
                        if now - t.get("_dbgGate", 0) > 5000:
                            t["_dbgGate"] = now
                            print(f"[pixel_triggers] SKIP '{t.get('name', '?')}': no macroHotkey and no macros running")
                        continue
                elif not macro_engine.running.get(mhk, False):
                    if now - t.get("_dbgGate", 0) > 5000:
                        t["_dbgGate"] = now
                        print(f"[pixel_triggers] SKIP '{t.get('name', '?')}': macro '{mhk}' not running")
                    continue
            elif mode == "always":
                pass

            try:
                pixels = _get_scaled(t, cur)
                if not pixels:
                    print(f"[pixel_triggers] SKIP '{t.get('name', '?')}': no scaled pixels")
                    continue

                anchor = t.get("anchor")
                if anchor and anchor.get("pixels"):
                    capture_res = t.get("captureRes")
                    anchor_scaled = _get_anchor_scaled(anchor, capture_res, cur)
                    anchor_matched = _check_pixels_batched(anchor_scaled, anchor.get("matchMode", "all"), hdc=hdc)
                    if not anchor_matched:
                        if now - t.get("_dbgAnchor", 0) > 5000:
                            t["_dbgAnchor"] = now
                            ap = anchor_scaled[0] if anchor_scaled else {}
                            actual = _get_pixel_color(ap.get("x", 0), ap.get("y", 0)) if ap else "?"
                            print(f"[pixel_triggers] ANCHOR FAIL '{t.get('name', '?')}': "
                                  f"pixel({ap.get('x', 0)},{ap.get('y', 0)}) "
                                  f"expected={ap.get('color', '?')} actual={actual} var={ap.get('variation', 10)}")
                        continue

                blocker = t.get("blocker")
                if blocker and blocker.get("pixels"):
                    capture_res = t.get("captureRes")
                    blocker_scaled = _get_blocker_scaled(blocker, capture_res, cur)
                    blocker_matched = _check_pixels_batched(blocker_scaled, blocker.get("matchMode", "all"), hdc=hdc)
                    if blocker_matched:
                        continue

                matched = _check_pixels_batched(pixels, t.get("matchMode", "all"), hdc=hdc)

                if t.get("inverse", False):
                    matched = not matched

                if matched:
                    action_key = t.get("actionKey", "")
                    if action_key:
                        input_handler.send_key(action_key)
                        macro_engine._check_buffs(action_key)
                    t["lastFired"] = now
            except Exception as e:
                print(f"[pixel_triggers] ERROR checking trigger '{t.get('name', '?')}': {e}")

        if _px_buffs:
            if _stop_event.is_set():
                return
            _check_buffs(cur, hdc=hdc)
    finally:
        user32.ReleaseDC(0, hdc)


def _check_buffs(cur, hdc=None):
    for b in _px_buffs:
        if _stop_event.is_set():
            return
        if not b.get("enabled", True):
            continue

        pixels = b.get("triggerPixels", [])
        if not pixels:
            continue

        try:
            scaled = _get_buff_scaled(b, cur)
            matched = _check_pixels_batched(scaled, b.get("triggerMatchMode", "all"), hdc=hdc)

            was_matched = b.get("pxMatched", False)
            b["pxMatched"] = matched
            if matched and not was_matched:
                print(f"[pixel_triggers] Pixel buff '{b.get('name', '?')}' matched! Activating timer "
                      f"duration={b.get('duration', 5000)}ms actionKey={b.get('actionKey', '')}")
                buff_mod.buff_engine.activate(b)
            elif not matched and was_matched:
                print(f"[pixel_triggers] Pixel buff '{b.get('name', '?')}' no longer matched.")
        except Exception as e:
            print(f"[pixel_triggers] Error checking buff '{b.get('name', '?')}': {e}")


def _check_pixels_batched(pixels, match_mode, hdc=None):
    if HAS_NATIVE:
        packed = utils.pack_pixels(pixels)
        if packed and len(packed) >= 16:
            result = utils.check_pixels_packed(packed, match_mode)
            if result is not None:
                return result
    return _match_pixels_python(pixels, match_mode, shared_hdc=hdc)


def check_spec_detect():
    if not game_detection.is_active():
        return None

    g = config.data.get("activeGame", "")
    c = config.data.get("activeClass", "")
    if not g or not c:
        return None

    try:
        class_data = config.data["games"][g]["classes"][c]
    except (KeyError, TypeError):
        return None

    cur = utils.get_screen_resolution()
    for s_name, s_data in class_data.get("specs", {}).items():
        detect = s_data.get("detect")
        if not detect or not detect.get("pixels"):
            continue
        capture_res = detect.get("captureRes")
        scaled = utils.scale_pixels(detect["pixels"], capture_res, cur)
        if _check_pixels_batched(scaled, detect.get("matchMode", "all")):
            return s_name

    return None


def _match_pixels_python(pixels, match_mode, shared_hdc=None):
    """Check pixels against screen using GetPixel. Uses numba for matching if available."""
    if not pixels:
        return False
    
    take_release = False
    if shared_hdc is None:
        hdc = ctypes.windll.user32.GetDC(0)
        if not hdc:
            return False
        take_release = True
    else:
        hdc = shared_hdc
    
    try:
        # Fast path: use numba to batch color matching
        if HAS_NUMBA and nu is not None:
            return _match_pixels_python_numba(pixels, match_mode, hdc)
        
        # Slow path: pure Python per-pixel
        if match_mode == "all":
            for px in pixels:
                found = _get_pixel_color_dc(hdc, px["x"], px["y"])
                if not utils.color_match(found, px.get("color", "0x000000"), px.get("variation", 10)):
                    return False
            return True
        else:
            for px in pixels:
                found = _get_pixel_color_dc(hdc, px["x"], px["y"])
                if utils.color_match(found, px.get("color", "0x000000"), px.get("variation", 10)):
                    return True
            return False
    finally:
        if take_release:
            ctypes.windll.user32.ReleaseDC(0, hdc)


def _match_pixels_python_numba(pixels, match_mode, hdc):
    """Numba-accelerated pixel matching using batch GetPixel."""
    import numpy as np
    
    n = len(pixels)
    x_coords = np.empty(n, dtype=np.int32)
    y_coords = np.empty(n, dtype=np.int32)
    colors_int = np.empty(n, dtype=np.int32)
    variations = np.empty(n, dtype=np.int32)
    
    # Extract pixel data into arrays
    for i, px in enumerate(pixels):
        x_coords[i] = px.get("x", 0)
        y_coords[i] = px.get("y", 0)
        c = px.get("color", 0)
        if isinstance(c, str):
            c = int(c, 16)
        colors_int[i] = c
        variations[i] = px.get("variation", 10)
    
    # Batch GetPixel using numpy for the found colors
    found_r = np.empty(n, dtype=np.int32)
    found_g = np.empty(n, dtype=np.int32)
    found_b = np.empty(n, dtype=np.int32)
    
    gdi32 = ctypes.windll.gdi32
    for i in range(n):
        color = gdi32.GetPixel(hdc, int(x_coords[i]), int(y_coords[i]))
        if color == -1:
            color = 0
        found_r[i] = color & 0xFF
        found_g[i] = (color >> 8) & 0xFF
        found_b[i] = (color >> 16) & 0xFF
    
    # Extract expected colors
    exp_r = (colors_int >> 16) & 0xFF
    exp_g = (colors_int >> 8) & 0xFF
    exp_b = colors_int & 0xFF
    
    # Stack for numba matching
    found_colors = np.stack([found_r, found_g, found_b], axis=1)
    expected_colors = np.stack([exp_r, exp_g, exp_b], axis=1)
    
    mode = 0 if match_mode == "all" else 1
    return nu._match_pixels_packed_inner(found_colors, expected_colors, variations, mode)


def _get_pixel_color_dc(hdc, x, y):
    color = ctypes.windll.gdi32.GetPixel(hdc, x, y)
    if color == -1:
        return "0x000000"
    r = color & 0xFF
    g = (color >> 8) & 0xFF
    b_val = (color >> 16) & 0xFF
    return f"0x{r:02X}{g:02X}{b_val:02X}"


def _get_pixel_color(x, y):
    return utils.get_pixel_color(x, y)
def stop():
    _stop_event.set()
