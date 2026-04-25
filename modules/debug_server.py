import json
import threading
import time
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler

_log = []
_log_lock = threading.Lock()
_overlay_ref = None
_window_ref = None
_max_entries = 500


def init(overlay, window):
    global _overlay_ref, _window_ref
    _overlay_ref = overlay
    _window_ref = window


def log(source, action, detail=None):
    entry = {
        "ts": time.time(),
        "time": time.strftime("%H:%M:%S", time.localtime()),
        "source": source,
        "action": action,
    }
    if detail:
        entry["detail"] = detail
    if traceback:
        import inspect
        frame = inspect.currentframe().f_back.f_back
        if frame:
            entry["caller"] = f"{frame.f_code.co_filename}:{frame.f_lineno} in {frame.f_code.co_name}"
    with _log_lock:
        _log.append(entry)
        if len(_log) > _max_entries:
            _log[:] = _log[-_max_entries:]


def get_log(last_n=100):
    with _log_lock:
        return _log[-last_n:]


def get_overlay_state():
    if not _overlay_ref:
        return {"error": "overlay not initialized"}
    o = _overlay_ref
    layout = o.layout()

    all_widgets = []
    for i in range(layout.count()):
        item = layout.itemAt(i)
        if item.widget():
            w = item.widget()
            all_widgets.append({
                "type": type(w).__name__,
                "text": w.text() if hasattr(w, "text") else "",
                "visible": w.isVisible(),
                "geometry": str(w.geometry().getRect()),
                "sizeHint": str(w.sizeHint().width()) + "x" + str(w.sizeHint().height()),
                "className": w.property("class") or "",
            })
        elif item.layout():
            sub = item.layout()
            for j in range(sub.count()):
                sw = sub.itemAt(j)
                if sw and sw.widget():
                    w = sw.widget()
                    all_widgets.append({
                        "type": type(w).__name__,
                        "text": w.text() if hasattr(w, "text") else "",
                        "visible": w.isVisible(),
                        "geometry": str(w.geometry().getRect()),
                        "sizeHint": str(w.sizeHint().width()) + "x" + str(w.sizeHint().height()),
                        "className": w.property("class") or "",
                    })

    macros_data = []
    for item, lbl in o._macro_lines:
        macros_data.append({"name": item.get("name", ""), "text": lbl.text(), "visible": lbl.isVisible(), "geo": str(lbl.geometry().getRect())})
    procs_data = []
    for item, lbl in o._proc_lines:
        procs_data.append({"name": item.get("name", ""), "text": lbl.text(), "visible": lbl.isVisible(), "geo": str(lbl.geometry().getRect())})
    buffs_data = []
    for item, lbl in o._buff_lines:
        buffs_data.append({"name": item.get("name", ""), "text": lbl.text(), "visible": lbl.isVisible(), "geo": str(lbl.geometry().getRect())})

    return {
        "window": {
            "size": f"{o.width()}x{o.height()}",
            "pos": f"{o.x()},{o.y()}",
            "fixedWidth": o.minimumWidth() if o.minimumWidth() == o.maximumWidth() else f"{o.minimumWidth()}-{o.maximumWidth()}",
            "fixedHeight": o.minimumHeight() if o.minimumHeight() == o.maximumHeight() else f"{o.minimumHeight()}-{o.maximumHeight()}",
            "visible": o.isVisible(),
        },
        "state": {
            "toggle_on": o._toggle_on,
            "toggle_key": o._toggle_key,
            "update_pending": o._update_pending,
        },
        "layout_count": layout.count(),
        "all_widgets": all_widgets,
        "tracked_lines": {
            "macros": macros_data,
            "procs": procs_data,
            "buffs": buffs_data,
            "dynamic_widget_count": len(o._dynamic_widgets),
        },
        "dynamic_widgets": [
            {"type": type(w).__name__, "text": w.text() if hasattr(w, "text") else "", "visible": w.isVisible(), "geo": str(w.geometry().getRect())}
            for w in o._dynamic_widgets
        ],
    }


_diag_state = {
    "keyboard_enabled": True,
    "overlay_visible": True,
    "mouse_poll_enabled": True,
    "timer_resolution_set": True,
}

_profile_data = {}


def profile_record(section, duration_ms):
    with _log_lock:
        lst = _profile_data.setdefault(section, [])
        lst.append(duration_ms)
        if len(lst) > 200:
            lst[:] = lst[-200:]


def _toggle_keyboard():
    try:
        import keyboard as kb
        if _diag_state["keyboard_enabled"]:
            kb.unhook_all()
            _diag_state["keyboard_enabled"] = False
            return {"action": "stopped", "keyboard_enabled": False}
        else:
            _diag_state["keyboard_enabled"] = True
            return {"action": "restarted", "keyboard_enabled": True, "note": "press ScrollLock to verify toggle works"}
    except Exception as e:
        return {"error": str(e)}


def _toggle_overlay():
    try:
        if _overlay_ref:
            if _diag_state["overlay_visible"]:
                _overlay_ref.hide()
                _diag_state["overlay_visible"] = False
                return {"action": "hidden", "overlay_visible": False}
            else:
                _overlay_ref.show()
                _diag_state["overlay_visible"] = True
                return {"action": "shown", "overlay_visible": True}
        return {"error": "no overlay ref"}
    except Exception as e:
        return {"error": str(e)}


def _toggle_mouse_poll():
    try:
        from modules.macro_engine import macro_engine, WM_QUIT
        import ctypes
        if _diag_state["mouse_poll_enabled"]:
            if macro_engine._mouse_tid:
                ctypes.windll.user32.PostThreadMessageW(macro_engine._mouse_tid, WM_QUIT, 0, 0)
            if macro_engine._mouse_thread:
                macro_engine._mouse_thread.join(timeout=1.0)
                macro_engine._mouse_thread = None
            if macro_engine._mouse_hook:
                ctypes.windll.user32.UnhookWindowsHookEx(macro_engine._mouse_hook)
                macro_engine._mouse_hook = None
            macro_engine._mouse_hook_proc = None
            macro_engine._mouse_tid = None
            _diag_state["mouse_poll_enabled"] = False
            return {"action": "stopped", "mouse_poll_enabled": False}
        else:
            macro_engine._start_mouse_hook()
            _diag_state["mouse_poll_enabled"] = True
            return {"action": "started", "mouse_poll_enabled": True}
    except Exception as e:
        return {"error": str(e)}


def _toggle_timer_resolution():
    try:
        import ctypes
        winmm = ctypes.windll.winmm
        if _diag_state["timer_resolution_set"]:
            winmm.timeEndPeriod(1)
            _diag_state["timer_resolution_set"] = False
            return {"action": "restored_default", "timer_resolution_set": False}
        else:
            winmm.timeBeginPeriod(1)
            _diag_state["timer_resolution_set"] = True
            return {"action": "set_1ms", "timer_resolution_set": True}
    except Exception as e:
        return {"error": str(e)}


def _profile_snapshot():
    import threading as _threading

    result = {
        "timestamp": time.time(),
        "python_threads": [],
        "thread_count": _threading.active_count(),
        "native_loaded": False,
    }

    for t in _threading.enumerate():
        result["python_threads"].append({
            "name": t.name,
            "daemon": t.daemon,
            "alive": t.is_alive(),
        })

    try:
        import psutil as _ps
        proc = _ps.Process()
        result["process"] = {
            "cpu_percent": proc.cpu_percent(interval=0),
            "num_threads": proc.num_threads(),
            "memory_mb": round(proc.memory_info().rss / 1024 / 1024, 1),
        }
        try:
            result["process"]["cpu_times"] = {k: round(v, 3) for k, v in proc.cpu_times()._asdict().items()}
        except Exception:
            pass
    except Exception as e:
        result["process_error"] = str(e)

    try:
        from modules.macro_engine import macro_engine, HAS_NATIVE as me_native
        result["native_loaded"] = me_native
        result["hotkey_count"] = len(macro_engine._hotkey_handles)
        result["release_handle_count"] = len(macro_engine._release_handles)
        result["mouse_hotkeys"] = list(macro_engine._mouse_hotkeys.keys())
        result["mouse_thread_alive"] = macro_engine._mouse_thread is not None and macro_engine._mouse_thread.is_alive()
        result["running_macros"] = {k: v for k, v in macro_engine.running.items() if v}
        result["profile_count"] = len(macro_engine.profile)
    except Exception as e:
        result["macro_engine_error"] = str(e)

    try:
        from modules import pixel_triggers as pt
        result["pixel_trigger_count"] = len(pt._triggers)
        result["pixel_buff_count"] = len(pt._px_buffs)
        result["pixel_thread_alive"] = pt._thread is not None and pt._thread.is_alive()
    except Exception as e:
        result["pixel_triggers_error"] = str(e)

    try:
        import keyboard as kb
        result["keyboard_hooks"] = len(kb._hotkeys) if hasattr(kb, '_hotkeys') else "unknown"
        result["keyboard_filtering"] = getattr(kb, '_filtering', "unknown")
        result["keyboard_all_hooks"] = len(kb._hooks) if hasattr(kb, '_hooks') else "unknown"
        result["keyboard_hooked"] = getattr(kb, '_hook', None) is not None
    except Exception:
        result["keyboard_hooks"] = "error"

    try:
        from modules import config_manager as config
        result["active_game"] = config.data.get("activeGame", "")
        result["active_class"] = config.data.get("activeClass", "")
        result["active_spec"] = config.data.get("activeSpec", "")
        macros = config.get_macros()
        result["configured_macros"] = len(macros)
        result["macro_hotkeys"] = [m.get("hotkey", "") for m in macros if m.get("hotkey")]
    except Exception as e:
        result["config_error"] = str(e)

    try:
        from modules import game_detection as gd
        result["game_window_active"] = gd.window_active
        result["game_is_active"] = gd.is_active()
        only = config.data.get("settings", {}).get("onlyInGame", True)
        result["onlyInGame"] = only
    except Exception:
        pass

    timing_data = {}
    with _log_lock:
        for key, vals in _profile_data.items():
            if isinstance(vals, list) and vals:
                recent = vals[-50:]
                timing_data[key] = {
                    "count": len(vals),
                    "last_avg_ms": round(sum(recent) / len(recent), 3),
                    "max_ms": round(max(recent), 3),
                    "min_ms": round(min(recent), 3),
                }
    result["timing"] = timing_data

    return result


_DIAG_HTML = b"""<!DOCTYPE html>
<html><head><title>FPS Diagnostic</title>
<meta charset="utf-8">
<style>
body{font-family:Consolas,monospace;background:#1e1e2e;color:#cdd6f4;margin:20px;max-width:800px}
h1{color:#89b4fa}h2{color:#a6e3a1}
.card{background:#181825;border:1px solid #45475a;border-radius:8px;padding:16px;margin:12px 0}
.card h3{margin:0 0 8px 0;color:#f9e2af;font-size:14px}
.card p{margin:4px 0;color:#a6adc8;font-size:13px}
button{background:#45475a;border:none;color:#cdd6f4;padding:10px 20px;border-radius:6px;cursor:pointer;margin:4px;font-size:13px}
button:hover{background:#585b70}
#status{background:#181825;padding:12px;border-radius:8px;font-size:13px;white-space:pre-wrap;margin-top:16px}
.note{background:#313244;padding:8px 12px;border-radius:4px;color:#f9e2af;font-size:12px;margin-top:8px}
</style></head><body>
<h1>FPS Diagnostic Tool</h1>
<p>Toggle each subsystem below and check if game FPS changes.</p>
<div class="note">Keep the game in windowed mode so you can see FPS while clicking. Test ONE at a time.</div>

<div class="card">
<h3>1. Keyboard Hook (global low-level hook via keyboard library)</h3>
<p>Intercepts ALL keyboard events system-wide. Can add input latency.</p>
<button onclick="toggle('keyboard')">Toggle Keyboard Hook</button>
<span id="keyboard-status">ON</span>
</div>

<div class="card">
<h3>2. Overlay Window (transparent always-on-top)</h3>
<p>Can force DWM composition changes that affect game rendering.</p>
<button onclick="toggle('overlay')">Toggle Overlay</button>
<span id="overlay-status">VISIBLE</span>
</div>

<div class="card">
<h3>3. Mouse Poll Thread (8ms polling)</h3>
<p>Polls mouse button state via GetAsyncKeyState.</p>
<button onclick="toggle('mouse_poll')">Toggle Mouse Poll</button>
<span id="mouse_poll-status">ON</span>
</div>

<div class="card">
<h3>4. Timer Resolution (timeBeginPeriod 1ms)</h3>
<p>Sets SYSTEM-WIDE timer to 1ms (from ~15ms). Increases context switches for ALL processes.</p>
<button onclick="toggle('timer')">Toggle Timer Resolution</button>
<span id="timer-status">1ms</span>
</div>

<div id="status">Ready. Click buttons above to test.</div>

<script>
async function toggle(name){
  const r=await fetch('/diag/toggle_'+name);
  const d=await r.json();
  document.getElementById(name+'-status').textContent=JSON.stringify(d);
  fetchStatus();
}
async function fetchStatus(){
  const r=await fetch('/profile');
  const d=await r.json();
  let s='Process CPU: '+JSON.stringify(d.process)+'\\n';
  s+='Threads: '+d.thread_count+' Python, '+(d.process?d.process.num_threads:'?')+' OS\\n';
  s+='Game active: '+d.game_is_active+'\\n';
  s+='Keyboard hooks: '+d.keyboard_all_hooks+'\\n';
  s+='Mouse thread: '+(d.mouse_thread_alive?'alive':'stopped')+'\\n';
  s+='Pixel thread: '+(d.pixel_thread_alive?'alive':'stopped');
  document.getElementById('status').textContent=s;
}
fetchStatus();
</script>
</body></html>"""


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            self._serve_dashboard()
        elif path == "/state":
            self._serve_json(get_overlay_state())
        elif path == "/log":
            self._serve_json(get_log(200))
        elif path == "/clear":
            with _log_lock:
                _log.clear()
            self._serve_json({"ok": True})
        elif path == "/profile":
            self._serve_json(_profile_snapshot())
        elif path == "/stats":
            try:
                from modules import perf_stats
                self._serve_json(perf_stats.snapshot())
            except Exception as e:
                self._serve_json({"error": str(e)})
        elif path == "/diag":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(_DIAG_HTML)))
            self.end_headers()
            self.wfile.write(_DIAG_HTML)
        elif path == "/diag/toggle_keyboard":
            self._serve_json(_toggle_keyboard())
        elif path == "/diag/toggle_overlay":
            self._serve_json(_toggle_overlay())
        elif path == "/diag/toggle_mouse_poll":
            self._serve_json(_toggle_mouse_poll())
        elif path == "/diag/toggle_timer":
            self._serve_json(_toggle_timer_resolution())
        else:
            self.send_error(404)

    def _serve_json(self, data):
        body = json.dumps(data, indent=2, default=str).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_dashboard(self):
        html = """<!DOCTYPE html>
<html><head><title>Overlay Debug</title>
<meta charset="utf-8">
<style>
body{font-family:Consolas,monospace;background:#1e1e2e;color:#cdd6f4;margin:20px}
h1{color:#89b4fa}h2{color:#a6e3a1;border-bottom:1px solid #45475a;padding-bottom:4px}
pre{background:#181825;padding:12px;border-radius:8px;overflow-x:auto;font-size:13px}
.log-entry{margin:2px 0;padding:4px 8px;border-radius:4px}
.log-entry:hover{background:#313244}
.ts{color:#6c7086}.src{color:#89b4fa}.act{color:#f9e2af}.det{color:#a6e3a1}
.widget{border:1px solid #45475a;padding:8px;margin:4px 0;border-radius:4px;display:inline-block;margin-right:4px}
.widget.hidden{opacity:0.4}
#auto{margin-top:8px}
label{color:#a6e3a1}
button{background:#45475a;border:none;color:#cdd6f4;padding:6px 14px;border-radius:6px;cursor:pointer;margin:2px}
button:hover{background:#585b70}
</style></head><body>
<h1>Overlay Debug Dashboard</h1>
<div>
<button onclick="fetchState()">Refresh State</button>
<button onclick="fetchLog()">Refresh Log</button>
<button onclick="clearLog()">Clear Log</button>
<label><input type="checkbox" id="auto" checked> Auto-refresh (2s)</label>
</div>
<h2>Overlay State</h2>
<pre id="state">Loading...</pre>
<h2>Widget Tree</h2>
<div id="widgets"></div>
<h2>Event Log</h2>
<pre id="log">Loading...</pre>
<script>
let _timer=null;
function startAuto(){if(_timer)clearInterval(_timer);_timer=setInterval(()=>{if(document.getElementById('auto').checked){fetchState();fetchLog()}},2000)}
function fetchState(){fetch('/state').then(r=>r.json()).then(d=>{document.getElementById('state').textContent=JSON.stringify(d.state,null,2)+'\\nLayout items: '+d.layout_count+'\\nDynamic widgets: '+d.tracked_lines.dynamic_widget_count+'\\nMacros: '+d.tracked_lines.macros.length+'\\nProcs: '+d.tracked_lines.procs.length+'\\nBuffs: '+d.tracked_lines.buffs.length;renderWidgets(d)})}
function renderWidgets(d){
  let h='<h3>All layout widgets ('+d.all_widgets.length+')</h3>';
  for(let w of d.all_widgets){h+='<div class="widget'+(w.visible?'':' hidden')+'"><b>'+w.type+'</b>'+(w.text?' '+w.text:'')+'<br><small>'+w.geometry+' sizeHint:'+w.sizeHint+(w.className?' class:'+w.className:'')+'</small></div>'}
  h+='<h3>Dynamic tracked ('+d.dynamic_widgets.length+')</h3>';
  for(let w of d.dynamic_widgets){h+='<div class="widget'+(w.visible?'':' hidden')+'"><b>'+w.type+'</b>'+(w.text?' '+w.text:'')+'<br><small>'+w.geo+'</small></div>'}
  document.getElementById('widgets').innerHTML=h;
}
function fetchLog(){fetch('/log').then(r=>r.json()).then(d=>{document.getElementById('log').innerHTML=d.map(e=>'<div class="log-entry"><span class="ts">'+e.time+'</span> <span class="src">['+e.source+']</span> <span class="act">'+e.action+'</span>'+(e.detail?' <span class="det">'+JSON.stringify(e.detail)+'</span>':'')+(e.caller?' <span class="ts">'+e.caller+'</span>':'')+'</div>').join('')})}
function clearLog(){fetch('/clear').then(()=>fetchLog())}
fetchState();fetchLog();startAuto();
</script></body></html>"""
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


_server = None


def start(port=8420):
    global _server
    _server = HTTPServer(("127.0.0.1", port), _Handler)
    t = threading.Thread(target=_server.serve_forever, daemon=True)
    t.start()
    print(f"Debug server on http://127.0.0.1:{port}")
