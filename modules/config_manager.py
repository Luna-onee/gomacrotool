import os
import shutil

import ckdl

from modules.theme import theme

_config_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Jaides_Macro_tool")
_config_file = os.path.join(_config_dir, "config.kdl")
_backup_file = os.path.join(_config_dir, "config.kdl.bak")
data = {}


def _parse_res(val):
    if isinstance(val, str) and "x" in val.lower():
        parts = val.lower().split("x")
        try:
            return {"w": int(parts[0]), "h": int(parts[1])}
        except (ValueError, IndexError):
            return None
    return None


def _res_str(res):
    if res and "w" in res and "h" in res:
        return f"{res['w']}x{res['h']}"
    return None


def _default():
    return {
        "games": {},
        "settings": {
            "defaultDelay": 50,
            "autoDetectGame": True,
            "onlyInGame": True,
            "darkMode": True,
            "toggleKey": "ScrollLock",
            "pixelCheckRate": 250,
            "overlayPosition": "top-left",
            "overlayWidth": 230,
            "overlayOpacity": 0.92,
            "overlayX": 10,
            "overlayY": 10,
        },
        "activeGame": "",
        "activeClass": "",
        "activeSpec": "",
    }


def load():
    global data
    data = _default()
    os.makedirs(_config_dir, exist_ok=True)
    if not os.path.exists(_config_file):
        _legacy = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.kdl")
        if os.path.exists(_legacy):
            shutil.copy2(_legacy, _config_file)
    if os.path.exists(_config_file):
        _load_kdl()
    else:
        save()
    if "darkMode" in data.get("settings", {}):
        theme.set_dark_mode(data["settings"]["darkMode"])


def _load_kdl():
    try:
        with open(_config_file, "r", encoding="utf-8") as f:
            content = f.read()
        if not content.strip():
            return
        doc = ckdl.parse(content)
        _parse_doc(doc)
        validate()
    except Exception as e:
        print(f"Failed to load config: {e}")
        # Attempt to restore from backup
        if os.path.exists(_backup_file):
            try:
                print("[config_manager] Attempting restore from backup...")
                shutil.copy2(_backup_file, _config_file)
                with open(_config_file, "r", encoding="utf-8") as f:
                    content = f.read()
                if content.strip():
                    doc = ckdl.parse(content)
                    _parse_doc(doc)
                    validate()
                    print("[config_manager] Restored from backup successfully.")
            except Exception as e2:
                print(f"[config_manager] Backup restore failed: {e2}")


def _parse_doc(doc):
    for node in doc.nodes:
        if node.name == "settings":
            for key, val in node.properties.items():
                data["settings"][key] = val
        elif node.name == "active":
            data["activeGame"] = node.properties.get("game", "")
            data["activeClass"] = node.properties.get("class", "")
            data["activeSpec"] = node.properties.get("spec", "")
        elif node.name == "game":
            game_name = node.args[0] if node.args else ""
            if not game_name:
                continue
            game_data = {"path": node.properties.get("path", ""), "classes": {}}
            for class_node in node.children:
                if class_node.name != "class":
                    continue
                class_name = class_node.args[0] if class_node.args else ""
                if not class_name:
                    continue
                class_data = {"specs": {}}
                for spec_node in class_node.children:
                    if spec_node.name != "spec":
                        continue
                    spec_name = spec_node.args[0] if spec_node.args else ""
                    if not spec_name:
                        continue
                    spec_data = {"macros": [], "pixelTriggers": [], "buffTimers": [], "detect": None}
                    for item in spec_node.children:
                        if item.name == "macro":
                            spec_data["macros"].append(_parse_macro_node(item))
                        elif item.name == "proc":
                            spec_data["pixelTriggers"].append(_parse_proc_node(item))
                        elif item.name == "buff":
                            spec_data["buffTimers"].append(_parse_buff_node(item))
                        elif item.name == "detect":
                            spec_data["detect"] = _parse_detect_node(item)
                    class_data["specs"][spec_name] = spec_data
                game_data["classes"][class_name] = class_data
            data["games"][game_name] = game_data


def _parse_macro_node(node):
    keys = []
    for child in node.children:
        if child.name == "key" and child.args:
            keys.append(str(child.args[0]))
    return {
        "name": node.properties.get("name", "Unnamed"),
        "hotkey": str(node.properties.get("hotkey", "")),
        "delay": node.properties.get("delay", data["settings"]["defaultDelay"]),
        "holdMode": bool(node.properties.get("holdMode", False)),
        "keys": keys,
        "interKeyDelay": node.properties.get("interKeyDelay", 0),
        "enabled": bool(node.properties.get("enabled", True)),
    }


def _parse_proc_node(node):
    pixels = []
    anchor = None
    blocker = None
    for child in node.children:
        if child.name == "pixel":
            color = child.properties.get("color", "0x000000")
            if isinstance(color, int):
                color = f"0x{color:06X}"
            pixels.append({
                "x": child.properties.get("x", 0),
                "y": child.properties.get("y", 0),
                "color": color,
                "variation": child.properties.get("variation", 10),
            })
        elif child.name == "anchor":
            anchor_pixels = []
            for ac in child.children:
                if ac.name == "pixel":
                    color = ac.properties.get("color", "0x000000")
                    if isinstance(color, int):
                        color = f"0x{color:06X}"
                    anchor_pixels.append({
                        "x": ac.properties.get("x", 0),
                        "y": ac.properties.get("y", 0),
                        "color": color,
                        "variation": ac.properties.get("variation", 10),
                    })
            anchor = {
                "pixels": anchor_pixels,
                "matchMode": str(child.properties.get("matchMode", "all")),
            }
        elif child.name == "blocker":
            blocker_pixels = []
            for bc in child.children:
                if bc.name == "pixel":
                    color = bc.properties.get("color", "0x000000")
                    if isinstance(color, int):
                        color = f"0x{color:06X}"
                    blocker_pixels.append({
                        "x": bc.properties.get("x", 0),
                        "y": bc.properties.get("y", 0),
                        "color": color,
                        "variation": bc.properties.get("variation", 10),
                    })
            blocker = {
                "pixels": blocker_pixels,
                "matchMode": str(child.properties.get("matchMode", "all")),
            }
    capture_res = _parse_res(node.properties.get("captureRes", None))
    return {
        "name": node.properties.get("name", "Unnamed"),
        "actionKey": str(node.properties.get("actionKey", node.properties.get("key", ""))),
        "pixels": pixels,
        "matchMode": str(node.properties.get("matchMode", "all")),
        "inverse": bool(node.properties.get("inverse", False)),
        "enabled": bool(node.properties.get("enabled", True)),
        "cooldown": node.properties.get("cooldown", 1000),
        "lastFired": 0,
        "triggerMode": str(node.properties.get("triggerMode", "macro")),
        "macroHotkey": str(node.properties.get("macroHotkey", "")),
        "captureRes": capture_res,
        "anchor": anchor,
        "blocker": blocker,
    }


def _parse_buff_node(node):
    watch_keys = []
    pixels = []
    for child in node.children:
        if child.name == "watchKey" and child.args:
            watch_keys.append(str(child.args[0]))
        elif child.name == "pixel":
            color = child.properties.get("color", "0x000000")
            if isinstance(color, int):
                color = f"0x{color:06X}"
            pixels.append({
                "x": child.properties.get("x", 0),
                "y": child.properties.get("y", 0),
                "color": color,
                "variation": child.properties.get("variation", 10),
            })
    capture_res = _parse_res(node.properties.get("captureRes", None))
    return {
        "name": node.properties.get("name", "Unnamed"),
        "watchKeys": watch_keys,
        "duration": node.properties.get("duration", 5000),
        "actionKey": str(node.properties.get("actionKey", "")),
        "onRefresh": str(node.properties.get("onRefresh", "reset")),
        "extendMs": node.properties.get("extendMs", 0),
        "enabled": bool(node.properties.get("enabled", True)),
        "triggerType": str(node.properties.get("triggerType", "keys")),
        "triggerPixels": pixels,
        "triggerMatchMode": str(node.properties.get("triggerMatchMode", "all")),
        "captureRes": capture_res,
    }


def _parse_detect_node(node):
    pixels = []
    for child in node.children:
        if child.name == "pixel":
            color = child.properties.get("color", "0x000000")
            if isinstance(color, int):
                color = f"0x{color:06X}"
            pixels.append({
                "x": child.properties.get("x", 0),
                "y": child.properties.get("y", 0),
                "color": color,
                "variation": child.properties.get("variation", 10),
            })
    capture_res = _parse_res(node.properties.get("captureRes", None))
    return {
        "pixels": pixels,
        "matchMode": str(node.properties.get("matchMode", "all")),
        "captureRes": capture_res,
    }


def _build_doc():
    nodes = []

    s = data.get("settings", {})
    nodes.append(ckdl.Node("settings", properties={
        "defaultDelay": s.get("defaultDelay", 50),
        "autoDetectGame": s.get("autoDetectGame", True),
        "onlyInGame": s.get("onlyInGame", True),
        "darkMode": theme.dark_mode,
        "toggleKey": s.get("toggleKey", "ScrollLock"),
        "pixelCheckRate": s.get("pixelCheckRate", 250),
        "overlayPosition": s.get("overlayPosition", "top-left"),
        "overlayWidth": s.get("overlayWidth", 230),
        "overlayOpacity": s.get("overlayOpacity", 0.92),
        "overlayX": s.get("overlayX", 10),
        "overlayY": s.get("overlayY", 10),
    }))

    nodes.append(ckdl.Node("active", properties={
        "game": data.get("activeGame", ""),
        "class": data.get("activeClass", ""),
        "spec": data.get("activeSpec", ""),
    }))

    for g_name, g_data in data.get("games", {}).items():
        class_nodes = []
        for c_name, c_data in g_data.get("classes", {}).items():
            spec_nodes = []
            for s_name, s_data in c_data.get("specs", {}).items():
                item_nodes = []
                detect = s_data.get("detect")
                if detect and detect.get("pixels"):
                    detect_px_nodes = [ckdl.Node("pixel", properties={
                        "x": px.get("x", 0),
                        "y": px.get("y", 0),
                        "color": px.get("color", "0x000000"),
                        "variation": px.get("variation", 10),
                    }) for px in detect["pixels"]]
                    detect_props = {"matchMode": detect.get("matchMode", "all")}
                    cr = _res_str(detect.get("captureRes"))
                    if cr:
                        detect_props["captureRes"] = cr
                    item_nodes.append(ckdl.Node("detect", properties=detect_props,
                                               children=detect_px_nodes))
                for m in s_data.get("macros", []):
                    key_nodes = [ckdl.Node("key", args=[k]) for k in m.get("keys", [])]
                    item_nodes.append(ckdl.Node("macro", properties={
                        "name": m.get("name", "Unnamed"),
                        "hotkey": m.get("hotkey", ""),
                        "delay": m.get("delay", 0),
                        "holdMode": m.get("holdMode", False),
                        "interKeyDelay": m.get("interKeyDelay", 0),
                        "enabled": m.get("enabled", True),
                    }, children=key_nodes if key_nodes else None))
                for p in s_data.get("pixelTriggers", []):
                    proc_children = []
                    anchor = p.get("anchor")
                    if anchor and anchor.get("pixels"):
                        anchor_px_nodes = [ckdl.Node("pixel", properties={
                            "x": px.get("x", 0),
                            "y": px.get("y", 0),
                            "color": px.get("color", "0x000000"),
                            "variation": px.get("variation", 10),
                        }) for px in anchor["pixels"]]
                        proc_children.append(ckdl.Node("anchor", properties={
                            "matchMode": anchor.get("matchMode", "all"),
                        }, children=anchor_px_nodes))
                    blocker = p.get("blocker")
                    if blocker and blocker.get("pixels"):
                        blocker_px_nodes = [ckdl.Node("pixel", properties={
                            "x": px.get("x", 0),
                            "y": px.get("y", 0),
                            "color": px.get("color", "0x000000"),
                            "variation": px.get("variation", 10),
                        }) for px in blocker["pixels"]]
                        proc_children.append(ckdl.Node("blocker", properties={
                            "matchMode": blocker.get("matchMode", "all"),
                        }, children=blocker_px_nodes))
                    for px in p.get("pixels", []):
                        proc_children.append(ckdl.Node("pixel", properties={
                            "x": px.get("x", 0),
                            "y": px.get("y", 0),
                            "color": px.get("color", "0x000000"),
                            "variation": px.get("variation", 10),
                        }))
                    proc_props = {
                        "name": p.get("name", "Unnamed"),
                        "actionKey": p.get("actionKey", ""),
                        "matchMode": p.get("matchMode", "all"),
                        "triggerMode": p.get("triggerMode", "macro"),
                        "inverse": p.get("inverse", False),
                        "enabled": p.get("enabled", True),
                        "cooldown": p.get("cooldown", 1000),
                        "macroHotkey": p.get("macroHotkey", ""),
                    }
                    cr = _res_str(p.get("captureRes"))
                    if cr:
                        proc_props["captureRes"] = cr
                    item_nodes.append(ckdl.Node("proc", properties=proc_props,
                                               children=proc_children if proc_children else None))
                for b in s_data.get("buffTimers", []):
                    buff_children = []
                    for wk in b.get("watchKeys", []):
                        buff_children.append(ckdl.Node("watchKey", args=[wk]))
                    for px in b.get("triggerPixels", []):
                        buff_children.append(ckdl.Node("pixel", properties={
                            "x": px.get("x", 0),
                            "y": px.get("y", 0),
                            "color": px.get("color", "0x000000"),
                            "variation": px.get("variation", 10),
                        }))
                    buff_props = {
                        "name": b.get("name", "Unnamed"),
                        "triggerType": b.get("triggerType", "keys"),
                        "duration": b.get("duration", 5000),
                        "actionKey": b.get("actionKey", ""),
                        "onRefresh": b.get("onRefresh", "reset"),
                        "extendMs": b.get("extendMs", 0),
                        "enabled": b.get("enabled", True),
                        "triggerMatchMode": b.get("triggerMatchMode", "all"),
                    }
                    cr = _res_str(b.get("captureRes"))
                    if cr:
                        buff_props["captureRes"] = cr
                    item_nodes.append(ckdl.Node("buff", properties=buff_props,
                                               children=buff_children if buff_children else None))
                spec_nodes.append(ckdl.Node("spec", args=[s_name],
                                            children=item_nodes if item_nodes else None))
            class_nodes.append(ckdl.Node("class", args=[c_name],
                                         children=spec_nodes if spec_nodes else None))
        nodes.append(ckdl.Node("game", args=[g_name], properties={
            "path": g_data.get("path", ""),
        }, children=class_nodes if class_nodes else None))

    return ckdl.Document(nodes)


def save():
    try:
        os.makedirs(_config_dir, exist_ok=True)
        doc = _build_doc()
        kdl_text = doc.dump()
        # Atomic write: temp file -> rename over original
        temp_file = _config_file + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(kdl_text)
            f.flush()
            os.fsync(f.fileno())
        # Keep one backup
        if os.path.exists(_config_file):
            shutil.copy2(_config_file, _backup_file)
        os.replace(temp_file, _config_file)
    except Exception as e:
        print(f"Failed to save config: {e}")
        # Clean up temp file on failure
        temp_file = _config_file + ".tmp"
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass


def validate():
    if "settings" not in data:
        data["settings"] = _default()["settings"]

    defaults = _default()["settings"]
    for k, v in defaults.items():
        if k not in data["settings"]:
            data["settings"][k] = v

    if "sendMode" in data["settings"]:
        del data["settings"]["sendMode"]

    if "games" not in data:
        data["games"] = {}

    for g_name, g_data in data["games"].items():
        if "classes" not in g_data:
            g_data["classes"] = {}
        for c_name, c_data in g_data["classes"].items():
            if "specs" not in c_data:
                c_data["specs"] = {}
            for s_name, s_data in c_data["specs"].items():
                if "macros" not in s_data:
                    s_data["macros"] = []
                if "pixelTriggers" not in s_data:
                    s_data["pixelTriggers"] = []
                if "buffTimers" not in s_data:
                    s_data["buffTimers"] = []
                s_data.setdefault("detect", None)
                _validate_macros(s_data["macros"])
                _validate_pixels(s_data["pixelTriggers"])
                _validate_buffs(s_data["buffTimers"])
                _validate_detect(s_data.get("detect"))


def _validate_macros(macros):
    if not isinstance(macros, list):
        return
    for m in macros:
        if not isinstance(m, dict):
            continue
        m.setdefault("name", "Unnamed")
        m.setdefault("hotkey", "")
        m.setdefault("delay", data["settings"]["defaultDelay"])
        m.setdefault("keys", [])
        if "isToggle" in m and "holdMode" not in m:
            m["holdMode"] = m["isToggle"]
        m.setdefault("holdMode", False)
        m.setdefault("interKeyDelay", 0)
        m.setdefault("enabled", True)


def _validate_pixels(triggers):
    if not isinstance(triggers, list):
        return
    for t in triggers:
        if not isinstance(t, dict):
            continue
        t.setdefault("name", "Unnamed")
        t.setdefault("actionKey", t.get("key", ""))
        t.setdefault("inverse", False)
        t.setdefault("enabled", True)
        t.setdefault("cooldown", 1000)
        t.setdefault("lastFired", 0)
        t.setdefault("triggerMode", "macro")
        t.setdefault("macroHotkey", "")
        t.setdefault("matchMode", "all")
        t.setdefault("captureRes", None)
        t.setdefault("anchor", None)
        t.setdefault("blocker", None)
        if "pixels" not in t or not isinstance(t.get("pixels"), list) or len(t["pixels"]) == 0:
            px = {"x": 0, "y": 0, "color": "0x000000", "variation": 10}
            if "x" in t:
                px["x"] = t["x"]
            if "y" in t:
                px["y"] = t["y"]
            if "color" in t:
                px["color"] = t["color"]
            if "variation" in t:
                px["variation"] = t["variation"]
            t["pixels"] = [px]
        else:
            for px in t["pixels"]:
                if not isinstance(px, dict):
                    continue
                px.setdefault("x", 0)
                px.setdefault("y", 0)
                px.setdefault("color", "0x000000")
                px.setdefault("variation", 10)
        if isinstance(t.get("anchor"), dict):
            for px in t["anchor"].get("pixels", []):
                if not isinstance(px, dict):
                    continue
                px.setdefault("x", 0)
                px.setdefault("y", 0)
                px.setdefault("color", "0x000000")
                px.setdefault("variation", 10)
        if isinstance(t.get("blocker"), dict):
            for px in t["blocker"].get("pixels", []):
                if not isinstance(px, dict):
                    continue
                px.setdefault("x", 0)
                px.setdefault("y", 0)
                px.setdefault("color", "0x000000")
                px.setdefault("variation", 10)


def _validate_buffs(buffs):
    if not isinstance(buffs, list):
        return
    for b in buffs:
        if not isinstance(b, dict):
            continue
        b.setdefault("name", "Unnamed")
        b.setdefault("watchKeys", [])
        b.setdefault("duration", 5000)
        b.setdefault("actionKey", "")
        b.setdefault("onRefresh", "reset")
        b.setdefault("extendMs", 0)
        b.setdefault("enabled", True)
        b.setdefault("triggerType", "keys")
        b.setdefault("triggerPixels", [])
        b.setdefault("triggerMatchMode", "all")
        b.setdefault("captureRes", None)
        if isinstance(b.get("triggerPixels"), list):
            for px in b["triggerPixels"]:
                if not isinstance(px, dict):
                    continue
                px.setdefault("x", 0)
                px.setdefault("y", 0)
                px.setdefault("color", "0x000000")
                px.setdefault("variation", 10)


def _validate_detect(detect):
    if not isinstance(detect, dict):
        return
    detect.setdefault("pixels", [])
    detect.setdefault("matchMode", "all")
    detect.setdefault("captureRes", None)
    for px in detect.get("pixels", []):
        if not isinstance(px, dict):
            continue
        px.setdefault("x", 0)
        px.setdefault("y", 0)
        px.setdefault("color", "0x000000")
        px.setdefault("variation", 10)


def _get_spec():
    try:
        return data["games"][data["activeGame"]]["classes"][data["activeClass"]]["specs"][data["activeSpec"]]
    except (KeyError, TypeError):
        return None


def get_macros():
    spec = _get_spec()
    if spec is None:
        return []
    return spec.get("macros", [])


def get_pixels():
    spec = _get_spec()
    if spec is None:
        return []
    return spec.get("pixelTriggers", [])


def get_buffs():
    spec = _get_spec()
    if spec is None:
        return []
    return spec.get("buffTimers", [])


def get_active_spec():
    return data.get("activeSpec", "")


def get_active_game():
    return data.get("activeGame", "")


def get_active_class():
    return data.get("activeClass", "")
