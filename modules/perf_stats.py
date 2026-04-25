import threading
import time


class _Stat:
    __slots__ = ("count", "total_ns", "max_ns", "_last_report")

    def __init__(self):
        self.count = 0
        self.total_ns = 0
        self.max_ns = 0
        self._last_report = 0.0

    def record(self, ns):
        self.count += 1
        self.total_ns += ns
        if ns > self.max_ns:
            self.max_ns = ns

    def snapshot(self):
        if self.count == 0:
            return {"calls": 0, "avg_us": 0, "max_us": 0}
        return {
            "calls": self.count,
            "avg_us": round(self.total_ns / self.count / 1000, 2),
            "max_us": round(self.max_ns / 1000, 2),
        }

    def reset(self):
        self.count = 0
        self.total_ns = 0
        self.max_ns = 0


class _LoopStat:
    __slots__ = ("interval_ns", "count", "total_ns", "max_ns", "wake_rate")

    def __init__(self):
        self.interval_ns = 0
        self.count = 0
        self.total_ns = 0
        self.max_ns = 0
        self.wake_rate = 0.0

    def set_interval(self, seconds):
        self.interval_ns = int(seconds * 1e9)

    def record(self, ns):
        self.count += 1
        self.total_ns += ns
        if ns > self.max_ns:
            self.max_ns = ns

    def snapshot(self):
        if self.count == 0:
            return {"wake_rate": 0, "avg_us": 0, "max_us": 0, "target_interval_ms": 0}
        return {
            "wake_rate": round(self.wake_rate, 1),
            "avg_us": round(self.total_ns / self.count / 1000, 2),
            "max_us": round(self.max_ns / 1000, 2),
            "target_interval_ms": round(self.interval_ns / 1e6, 1),
        }

    def reset(self):
        self.count = 0
        self.total_ns = 0
        self.max_ns = 0
        self.wake_rate = 0.0


_stats = {}
_loops = {}
_lock = threading.Lock()
_warnings = []
_watchdog_running = False
_enabled = False


def enable():
    global _enabled
    _enabled = True


def stat(name):
    if not _enabled:
        return None
    with _lock:
        if name not in _stats:
            _stats[name] = _Stat()
        return _stats[name]


def loop_stat(name, interval_sec=0):
    if not _enabled:
        return None
    with _lock:
        if name not in _loops:
            _loops[name] = _LoopStat()
        s = _loops[name]
        if interval_sec > 0:
            s.set_interval(interval_sec)
        return s


def record(name, ns):
    if not _enabled:
        return
    with _lock:
        if name not in _stats:
            _stats[name] = _Stat()
        _stats[name].record(ns)


def record_loop(name, ns):
    if not _enabled:
        return
    with _lock:
        if name not in _loops:
            _loops[name] = _LoopStat()
        _loops[name].record(ns)


_perf = time.perf_counter


def measure(name):
    if not _enabled:
        return lambda: None
    t0 = _perf()
    return lambda: record(name, int((_perf() - t0) * 1e9))


def measure_loop(name):
    if not _enabled:
        return lambda: None
    t0 = _perf()
    return lambda: record_loop(name, int((_perf() - t0) * 1e9))


_THRESHOLDS = {
    "loop_wake_rate": 100,
    "loop_avg_us": 5000,
    "loop_max_us": 50000,
    "stat_avg_us": 1000,
    "stat_max_us": 10000,
    "process_cpu_pct": 3.0,
}


def set_threshold(key, value):
    _THRESHOLDS[key] = value


def _check():
    now = time.time()
    warnings = []

    for name, s in _loops.items():
        if s.count == 0:
            continue
        avg_us = s.total_ns / s.count / 1000
        max_us = s.max_ns / 1000

        if s.wake_rate > _THRESHOLDS["loop_wake_rate"]:
            warnings.append(
                f"[perf] {name}: wake rate {s.wake_rate:.0f}/s "
                f"(threshold: {_THRESHOLDS['loop_wake_rate']}/s) — "
                f"consider event-driven instead of polling"
            )
        if avg_us > _THRESHOLDS["loop_avg_us"]:
            warnings.append(
                f"[perf] {name}: avg iteration {avg_us:.0f}us "
                f"(threshold: {_THRESHOLDS['loop_avg_us']}us)"
            )
        if max_us > _THRESHOLDS["loop_max_us"]:
            warnings.append(
                f"[perf] {name}: max iteration {max_us:.0f}us "
                f"(threshold: {_THRESHOLDS['loop_max_us']}us)"
            )

    for name, s in _stats.items():
        if s.count == 0:
            continue
        avg_us = s.total_ns / s.count / 1000
        if avg_us > _THRESHOLDS["stat_avg_us"]:
            warnings.append(
                f"[perf] {name}: avg {avg_us:.0f}us "
                f"(threshold: {_THRESHOLDS['stat_avg_us']}us)"
            )

    try:
        import psutil
        cpu = psutil.Process().cpu_percent(interval=0)
        if cpu > _THRESHOLDS["process_cpu_pct"]:
            warnings.append(
                f"[perf] process CPU: {cpu:.1f}% "
                f"(threshold: {_THRESHOLDS['process_cpu_pct']}%)"
            )
    except Exception:
        pass

    if warnings:
        for w in warnings:
            print(w)

    _warnings.clear()
    _warnings.extend(warnings)

    with _lock:
        for s in _stats.values():
            s.reset()
        for s in _loops.values():
            s.reset()

    return warnings


def start_watchdog(interval_sec=5):
    global _watchdog_running
    if _watchdog_running:
        return
    _watchdog_running = True

    def _loop():
        while _watchdog_running:
            time.sleep(interval_sec)
            _update_wake_rates()
            _check()

    t = threading.Thread(target=_loop, daemon=True)
    t.start()


def stop_watchdog():
    global _watchdog_running
    _watchdog_running = False


def _update_wake_rates():
    with _lock:
        for name, s in _loops.items():
            if s.count > 0 and s.interval_ns > 0:
                expected_count = 5e9 / s.interval_ns
                s.wake_rate = s.count / max(expected_count / expected_count, 1)
                actual_interval = 5.0 / s.count if s.count else 0
                s.wake_rate = round(1.0 / actual_interval, 1) if actual_interval > 0 else 0


def snapshot():
    with _lock:
        result = {
            "stats": {name: s.snapshot() for name, s in _stats.items()},
            "loops": {name: s.snapshot() for name, s in _loops.items()},
            "warnings": list(_warnings),
        }
    return result
