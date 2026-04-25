import heapq
import threading
import time

from modules import config_manager as config
from modules import input_handler


def _log(action, detail=None):
    try:
        from modules.debug_server import log
        log("buff_engine", action, detail)
    except Exception:
        pass


def _now_ms():
    """Monotonic high-resolution time in milliseconds."""
    return time.perf_counter() * 1000.0


class BuffEngine:
    def __init__(self):
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._entries = {}  # name -> {gen, expire_time_ms, start_time_ms, duration_ms, buff, cancelled}
        self._heap = []     # [(expire_time_ms, gen, name, buff), ...]
        self._callbacks = []
        self._thread = None
        self._stop_event = threading.Event()
        self._gen_counter = 0

    def register_callback(self, cb):
        self._callbacks.append(cb)

    def unregister_callback(self, cb):
        try:
            self._callbacks.remove(cb)
        except ValueError:
            pass

    def _notify(self, event_type, buff_name, detail=None):
        for cb in list(self._callbacks):
            try:
                cb(event_type, buff_name, detail)
            except Exception as e:
                print(f"[buff_engine] callback error: {e}")

    def _ensure_thread(self):
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._worker, daemon=True)
            self._thread.start()

    def _worker(self):
        while not self._stop_event.is_set():
            buff_to_fire = None
            with self._lock:
                now = _now_ms()
                while self._heap:
                    expire_time, gen, name, buff = self._heap[0]
                    if expire_time > now:
                        break
                    heapq.heappop(self._heap)
                    entry = self._entries.get(name)
                    if entry and entry["gen"] == gen and not entry.get("cancelled"):
                        self._entries.pop(name, None)
                        buff_to_fire = buff
                        break

                if buff_to_fire is None:
                    if self._heap:
                        wait_time = (self._heap[0][0] - _now_ms()) / 1000.0
                        if wait_time > 0:
                            self._condition.wait(timeout=wait_time)
                    else:
                        self._condition.wait(timeout=1.0)

            if buff_to_fire is not None:
                self._fire(buff_to_fire)

    def _fire(self, buff):
        name = buff.get("name", "Unnamed")
        action_key = buff.get("actionKey", "")
        _log("expired", {"name": name, "actionKey": action_key})
        self._notify("expired", name, {"actionKey": action_key})
        if action_key:
            try:
                # If game is not active, try to send directly to the game window
                from modules import game_detection
                if not game_detection.is_active():
                    hwnd = game_detection.get_game_hwnd()
                    if hwnd:
                        input_handler.send_key_to_window(hwnd, action_key)
                    else:
                        input_handler.send_key(action_key)
                else:
                    input_handler.send_key(action_key)
            except Exception as e:
                print(f"[buff_engine] Error sending actionKey '{action_key}' for buff '{name}': {e}")

    def activate(self, buff):
        name = buff.get("name", "Unnamed")
        new_duration = buff.get("duration", 5000)

        with self._lock:
            existing = self._entries.get(name)
            if existing:
                on_refresh = buff.get("onRefresh", "reset")

                if on_refresh == "ignore":
                    _log("activate_ignored", {"name": name, "reason": "onRefresh=ignore"})
                    return

                existing["cancelled"] = True

                if on_refresh == "extend":
                    elapsed = _now_ms() - existing["start_time_ms"]
                    remaining = existing["duration_ms"] - elapsed
                    if remaining < 0:
                        remaining = 0
                    extend_ms = buff.get("extendMs", 0)
                    new_duration = remaining + extend_ms
                    _log("activate_extend", {"name": name, "remaining_ms": round(remaining, 1),
                                             "extend_ms": extend_ms, "new_duration": round(new_duration, 1)})
                    self._notify("extend", name, {"remaining": remaining, "new_duration": new_duration})
                else:
                    _log("activate_reset", {"name": name, "old_remaining_ms": round(existing["duration_ms"] - (_now_ms() - existing["start_time_ms"]), 1),
                                            "new_duration_ms": new_duration})
                    self._notify("reset", name, {"new_duration": new_duration})
            else:
                _log("activate_new", {"name": name, "duration_ms": new_duration})
                self._notify("activated", name, {"duration": new_duration})

            self._gen_counter += 1
            gen = self._gen_counter
            now_ms = _now_ms()
            expire_time = now_ms + new_duration

            self._entries[name] = {
                "gen": gen,
                "expire_time_ms": expire_time,
                "start_time_ms": now_ms,
                "duration_ms": new_duration,
                "buff": buff,
                "cancelled": False,
            }
            heapq.heappush(self._heap, (expire_time, gen, name, buff))
            self._condition.notify()

        self._ensure_thread()

    def _on_expired(self, buff, expected_gen):
        # Kept for compatibility; actual expiry is handled by _worker
        name = buff.get("name", "Unnamed")
        with self._lock:
            entry = self._entries.get(name)
            if entry is None or entry.get("cancelled") or entry.get("gen") != expected_gen:
                return
            self._entries.pop(name, None)
        self._fire(buff)

    def get_active_timers(self):
        now = _now_ms()
        with self._lock:
            result = {}
            for name, entry in list(self._entries.items()):
                if entry.get("cancelled"):
                    continue
                remaining = entry["expire_time_ms"] - now
                if remaining < 0:
                    remaining = 0
                result[name] = remaining
            return result

    def get_timer_info(self):
        now = _now_ms()
        with self._lock:
            result = {}
            for name, entry in list(self._entries.items()):
                if entry.get("cancelled"):
                    continue
                elapsed = now - entry["start_time_ms"]
                remaining = entry["expire_time_ms"] - now
                if remaining < 0:
                    remaining = 0
                result[name] = {
                    "remaining": remaining,
                    "duration": entry["duration_ms"],
                    "elapsed": elapsed,
                    "progress": elapsed / entry["duration_ms"] if entry["duration_ms"] > 0 else 1.0,
                }
            return result

    def clear_all(self):
        with self._lock:
            names = list(self._entries.keys())
            for entry in self._entries.values():
                entry["cancelled"] = True
            self._entries.clear()
            self._heap.clear()
            self._condition.notify()
        _log("clear_all", {"cleared": names})
        for name in names:
            self._notify("cleared", name, None)

    def stop(self):
        self._stop_event.set()
        with self._lock:
            self._condition.notify_all()
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None


buff_engine = BuffEngine()
