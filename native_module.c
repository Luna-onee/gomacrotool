#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <Windows.h>
#include <stdlib.h>
#include <string.h>

/* ==================== VK Name Table ==================== */

typedef struct {
    const char* name;
    int vk;
} VkEntry;

static VkEntry vk_table[] = {
    {"1",0x31},{"2",0x32},{"3",0x33},{"4",0x34},{"5",0x35},
    {"6",0x36},{"7",0x37},{"8",0x38},{"9",0x39},{"0",0x30},
    {"a",0x41},{"b",0x42},{"c",0x43},{"d",0x44},{"e",0x45},
    {"f",0x46},{"g",0x47},{"h",0x48},{"i",0x49},{"j",0x4A},
    {"k",0x4B},{"l",0x4C},{"m",0x4D},{"n",0x4E},{"o",0x4F},
    {"p",0x50},{"q",0x51},{"r",0x52},{"s",0x53},{"t",0x54},
    {"u",0x55},{"v",0x56},{"w",0x57},{"x",0x58},{"y",0x59},{"z",0x5A},
    {"F1",0x70},{"F2",0x71},{"F3",0x72},{"F4",0x73},{"F5",0x74},
    {"F6",0x75},{"F7",0x76},{"F8",0x77},{"F9",0x78},{"F10",0x79},
    {"F11",0x7A},{"F12",0x7B},
    {"Tab",0x09},{"Enter",0x0D},{"Escape",0x1B},{"Backspace",0x08},
    {"Space",0x20},{"Delete",0x2E},{"Insert",0x2D},
    {"Home",0x24},{"End",0x23},{"PgUp",0x21},{"PgDn",0x22},
    {"Up",0x26},{"Down",0x28},{"Left",0x25},{"Right",0x27},
    {"CapsLock",0x14},{"ScrollLock",0x91},{"NumLock",0x90},
    {"PrintScreen",0x2C},{"Pause",0x13},
    {"Shift",0x10},{"Ctrl",0x11},{"Alt",0x12},
    {"LButton",0x01},{"RButton",0x02},{"MButton",0x04},
    {"XButton1",0x05},{"XButton2",0x06},
    {"Numpad0",0x60},{"Numpad1",0x61},{"Numpad2",0x62},{"Numpad3",0x63},
    {"Numpad4",0x64},{"Numpad5",0x65},{"Numpad6",0x66},{"Numpad7",0x67},
    {"Numpad8",0x68},{"Numpad9",0x69},
    {"NumpadEnter",0x0D},{"NumpadAdd",0x6B},{"NumpadSub",0x6D},
    {"NumpadMult",0x6A},{"NumpadDiv",0x6F},
    {NULL,0}
};

static const char* ext_keys[] = {
    "Insert","Delete","Home","End","PgUp","PgDn",
    "Up","Down","Left","Right","NumpadEnter","NumpadDiv",NULL
};

static const char* mse_keys[] = {
    "LButton","RButton","MButton","XButton1","XButton2",NULL
};

static LARGE_INTEGER qpc_freq;
static int qpc_ready = 0;

/* ==================== Helpers ==================== */

static int _name_to_vk(const char* name) {
    for (int i = 0; vk_table[i].name; i++)
        if (_stricmp(vk_table[i].name, name) == 0) return vk_table[i].vk;
    return 0;
}

static const char* _vk_to_name(int vk) {
    for (int i = 0; vk_table[i].name; i++)
        if (vk_table[i].vk == vk) return vk_table[i].name;
    return NULL;
}

static int _is_ext(const char* n) {
    for (int i = 0; ext_keys[i]; i++)
        if (_stricmp(ext_keys[i], n) == 0) return 1;
    return 0;
}

static int _is_mouse(const char* n) {
    for (int i = 0; mse_keys[i]; i++)
        if (_stricmp(mse_keys[i], n) == 0) return 1;
    return 0;
}

static void _make_key(INPUT* inp, WORD vk, int up, const char* name) {
    memset(inp, 0, sizeof(INPUT));
    inp->type = INPUT_KEYBOARD;
    inp->ki.wVk = vk;
    inp->ki.wScan = (WORD)MapVirtualKeyW(vk, 0);
    if (up) inp->ki.dwFlags |= KEYEVENTF_KEYUP;
    if (_is_ext(name)) inp->ki.dwFlags |= KEYEVENTF_EXTENDEDKEY;
}

static void _make_mouse_by_vk(INPUT* inp, int vk, int up) {
    memset(inp, 0, sizeof(INPUT));
    inp->type = INPUT_MOUSE;
    switch (vk) {
        case 0x01: inp->mi.dwFlags = up ? MOUSEEVENTF_LEFTUP : MOUSEEVENTF_LEFTDOWN; break;
        case 0x02: inp->mi.dwFlags = up ? MOUSEEVENTF_RIGHTUP : MOUSEEVENTF_RIGHTDOWN; break;
        case 0x04: inp->mi.dwFlags = up ? MOUSEEVENTF_MIDDLEUP : MOUSEEVENTF_MIDDLEDOWN; break;
        case 0x05: inp->mi.dwFlags = up ? MOUSEEVENTF_XUP : MOUSEEVENTF_XDOWN; inp->mi.mouseData = XBUTTON1; break;
        case 0x06: inp->mi.dwFlags = up ? MOUSEEVENTF_XUP : MOUSEEVENTF_XDOWN; inp->mi.mouseData = XBUTTON2; break;
    }
}

static void _make_mouse(INPUT* inp, const char* name, int up) {
    int vk = _name_to_vk(name);
    _make_mouse_by_vk(inp, vk, up);
}

static void _send(INPUT* arr, int n) { SendInput(n, arr, sizeof(INPUT)); }

static void _precise_sleep_internal(double ms) {
    if (ms <= 0.0) return;
    if (!qpc_ready) { Sleep((DWORD)ms); return; }
    if (ms > 5.0) { Sleep((DWORD)(ms - 2.0)); ms = 2.0; }
    LARGE_INTEGER start, cur;
    QueryPerformanceCounter(&start);
    LONGLONG target = start.QuadPart + (LONGLONG)(qpc_freq.QuadPart * ms / 1000.0);
    while (1) { SwitchToThread(); QueryPerformanceCounter(&cur); if (cur.QuadPart >= target) break; }
}

/* ==================== Module Functions ==================== */

static PyObject* native_init(PyObject* self, PyObject* args) {
    SetProcessDPIAware();
    QueryPerformanceFrequency(&qpc_freq);
    qpc_ready = 1;
    Py_RETURN_NONE;
}

static PyObject* native_send_key(PyObject* self, PyObject* args) {
    const char* name;
    if (!PyArg_ParseTuple(args, "s", &name)) return NULL;
    if (_is_mouse(name)) {
        INPUT inp[2];
        _make_mouse(&inp[0], name, 0);
        _make_mouse(&inp[1], name, 1);
        _send(inp, 2);
    } else {
        int vk = _name_to_vk(name);
        if (!vk) Py_RETURN_NONE;
        INPUT inp[2];
        _make_key(&inp[0], (WORD)vk, 0, name);
        _make_key(&inp[1], (WORD)vk, 1, name);
        _send(inp, 2);
    }
    Py_RETURN_NONE;
}

static PyObject* native_send_key_down(PyObject* self, PyObject* args) {
    const char* name;
    if (!PyArg_ParseTuple(args, "s", &name)) return NULL;
    INPUT inp;
    if (_is_mouse(name)) { _make_mouse(&inp, name, 0); }
    else { int vk = _name_to_vk(name); if(!vk) Py_RETURN_NONE; _make_key(&inp,(WORD)vk,0,name); }
    _send(&inp, 1);
    Py_RETURN_NONE;
}

static PyObject* native_send_key_up(PyObject* self, PyObject* args) {
    const char* name;
    if (!PyArg_ParseTuple(args, "s", &name)) return NULL;
    INPUT inp;
    if (_is_mouse(name)) { _make_mouse(&inp, name, 1); }
    else { int vk = _name_to_vk(name); if(!vk) Py_RETURN_NONE; _make_key(&inp,(WORD)vk,1,name); }
    _send(&inp, 1);
    Py_RETURN_NONE;
}

static PyObject* native_send_key_batch(PyObject* self, PyObject* args) {
    PyObject* list;
    if (!PyArg_ParseTuple(args, "O", &list)) return NULL;
    if (!PyList_Check(list)) { PyErr_SetString(PyExc_TypeError,"list"); return NULL; }
    Py_ssize_t len = PyList_Size(list);
    INPUT buf[256];
    int cnt = 0;
    for (Py_ssize_t i = 0; i < len; i++) {
        const char* name = PyUnicode_AsUTF8(PyList_GetItem(list, i));
        if (!name) continue;
        if (_is_mouse(name)) {
            if (cnt > 0) { _send(buf, cnt); cnt = 0; }
            INPUT mi[2];
            _make_mouse(&mi[0], name, 0);
            _make_mouse(&mi[1], name, 1);
            _send(mi, 2);
        } else {
            int vk = _name_to_vk(name);
            if (vk) {
                _make_key(&buf[cnt++], (WORD)vk, 0, name);
                _make_key(&buf[cnt++], (WORD)vk, 1, name);
            }
        }
        if (cnt >= 254) { _send(buf, cnt); cnt = 0; }
    }
    if (cnt > 0) _send(buf, cnt);
    Py_RETURN_NONE;
}

static PyObject* native_get_pixel_color(PyObject* self, PyObject* args) {
    int x, y;
    if (!PyArg_ParseTuple(args, "ii", &x, &y)) return NULL;
    HDC hdc = GetDC(NULL);
    if (!hdc) return PyLong_FromLong(0);
    COLORREF c = GetPixel(hdc, x, y);
    ReleaseDC(NULL, hdc);
    if (c == CLR_INVALID) return PyLong_FromLong(0);
    return PyLong_FromLong(((int)(c & 0xFF) << 16) | (int)(c & 0xFF00) | ((int)((c >> 16) & 0xFF)));
}

static PyObject* native_precise_sleep(PyObject* self, PyObject* args) {
    double ms;
    if (!PyArg_ParseTuple(args, "d", &ms)) return NULL;
    _precise_sleep_internal(ms);
    Py_RETURN_NONE;
}

static PyObject* native_get_time(PyObject* self, PyObject* Py_UNUSED(args)) {
    if (!qpc_ready) return PyFloat_FromDouble(0.0);
    LARGE_INTEGER cur;
    QueryPerformanceCounter(&cur);
    return PyFloat_FromDouble(cur.QuadPart * 1000.0 / qpc_freq.QuadPart);
}

static PyObject* native_color_match(PyObject* self, PyObject* args) {
    int c1, c2, v;
    if (!PyArg_ParseTuple(args, "iii", &c1, &c2, &v)) return NULL;
    if (abs(((c1>>16)&0xFF)-((c2>>16)&0xFF)) <= v &&
        abs(((c1>>8)&0xFF)-((c2>>8)&0xFF)) <= v &&
        abs((c1&0xFF)-(c2&0xFF)) <= v)
        Py_RETURN_TRUE;
    Py_RETURN_FALSE;
}

static PyObject* native_is_key_down(PyObject* self, PyObject* args) {
    int vk;
    if (!PyArg_ParseTuple(args, "i", &vk)) return NULL;
    if (GetAsyncKeyState(vk) & 0x8000) Py_RETURN_TRUE;
    Py_RETURN_FALSE;
}

static PyObject* native_get_toggle_state(PyObject* self, PyObject* args) {
    int vk;
    if (!PyArg_ParseTuple(args, "i", &vk)) return NULL;
    if (GetKeyState(vk) & 0x0001) Py_RETURN_TRUE;
    Py_RETURN_FALSE;
}

static PyObject* native_name_to_vk(PyObject* self, PyObject* args) {
    const char* name;
    if (!PyArg_ParseTuple(args, "s", &name)) return NULL;
    return PyLong_FromLong(_name_to_vk(name));
}

static PyObject* native_vk_to_name(PyObject* self, PyObject* args) {
    int vk;
    if (!PyArg_ParseTuple(args, "i", &vk)) return NULL;
    const char* n = _vk_to_name(vk);
    if (n) return PyUnicode_FromString(n);
    return PyUnicode_FromFormat("%d", vk);
}

/* check_pixels: takes list of dicts [{x,y,color(str),variation}] */
static PyObject* native_check_pixels(PyObject* self, PyObject* args) {
    PyObject* pxlist;
    const char* mode;
    if (!PyArg_ParseTuple(args, "Os", &pxlist, &mode)) return NULL;
    if (!PyList_Check(pxlist)) { PyErr_SetString(PyExc_TypeError,"list"); return NULL; }

    HDC hdc = GetDC(NULL);
    if (!hdc) Py_RETURN_FALSE;
    int all = (_stricmp(mode, "all") == 0);
    Py_ssize_t n = PyList_Size(pxlist);
    int result = all ? 1 : 0;

    for (Py_ssize_t i = 0; i < n; i++) {
        PyObject* px = PyList_GetItem(pxlist, i);
        int x = (int)PyLong_AsLong(PyDict_GetItemString(px, "x"));
        int y = (int)PyLong_AsLong(PyDict_GetItemString(px, "y"));
        int var = (int)PyLong_AsLong(PyDict_GetItemString(px, "variation"));
        PyObject* co = PyDict_GetItemString(px, "color");
        int exp;
        if (PyUnicode_Check(co)) {
            const char* cs = PyUnicode_AsUTF8(co);
            exp = (int)strtol(cs, NULL, 16);
        } else {
            exp = (int)PyLong_AsLong(co);
        }

        COLORREF f = GetPixel(hdc, x, y);
        if (f == CLR_INVALID) { if (all) { result = 0; break; } continue; }

        int match = (abs((int)(f&0xFF)-((exp>>16)&0xFF)) <= var &&
                     abs((int)((f>>8)&0xFF)-((exp>>8)&0xFF)) <= var &&
                     abs((int)((f>>16)&0xFF)-(exp&0xFF)) <= var);

        if (all) { if (!match) { result = 0; break; } }
        else { if (match) { result = 1; break; } }
    }
    ReleaseDC(NULL, hdc);
    if (result) Py_RETURN_TRUE;
    Py_RETURN_FALSE;
}

/* check_pixels_packed: takes bytes with packed [x,y,color_int,var] per pixel */
static PyObject* native_check_pixels_packed(PyObject* self, PyObject* args) {
    Py_buffer buf;
    const char* mode;
    if (!PyArg_ParseTuple(args, "y*s", &buf, &mode)) return NULL;

    int* data = (int*)buf.buf;
    Py_ssize_t count = buf.len / (4 * (Py_ssize_t)sizeof(int));

    HDC hdc = GetDC(NULL);
    if (!hdc) { PyBuffer_Release(&buf); Py_RETURN_FALSE; }
    int all = (_stricmp(mode, "all") == 0);
    int result = all ? 1 : 0;

    for (Py_ssize_t i = 0; i < count; i++) {
        int x = data[i*4], y = data[i*4+1], exp = data[i*4+2], var = data[i*4+3];
        COLORREF f = GetPixel(hdc, x, y);
        if (f == CLR_INVALID) { if (all) { result = 0; break; } continue; }
        int match = (abs((int)(f&0xFF)-((exp>>16)&0xFF)) <= var &&
                     abs((int)((f>>8)&0xFF)-((exp>>8)&0xFF)) <= var &&
                     abs((int)((f>>16)&0xFF)-(exp&0xFF)) <= var);
        if (all) { if (!match) { result = 0; break; } }
        else { if (match) { result = 1; break; } }
    }
    ReleaseDC(NULL, hdc);
    PyBuffer_Release(&buf);
    if (result) Py_RETURN_TRUE;
    Py_RETURN_FALSE;
}

/* capture_and_check: BitBlt the bounding rect once, check all pixels from memory */
static PyObject* native_capture_and_check(PyObject* self, PyObject* args) {
    Py_buffer buf;
    const char* mode;
    if (!PyArg_ParseTuple(args, "y*s", &buf, &mode)) return NULL;

    int* data = (int*)buf.buf;
    Py_ssize_t count = buf.len / (4 * (Py_ssize_t)sizeof(int));
    if (count == 0) { PyBuffer_Release(&buf); Py_RETURN_FALSE; }

    /* find bounding box */
    int minx = data[0], miny = data[1], maxx = data[0], maxy = data[1];
    for (Py_ssize_t i = 1; i < count; i++) {
        int x = data[i*4], y = data[i*4+1];
        if (x < minx) minx = x; if (x > maxx) maxx = x;
        if (y < miny) miny = y; if (y > maxy) maxy = y;
    }
    int w = maxx - minx + 1, h = maxy - miny + 1;

    HDC screen = GetDC(NULL);
    if (!screen) { PyBuffer_Release(&buf); Py_RETURN_FALSE; }
    HDC mem = CreateCompatibleDC(screen);
    HBITMAP bmp = CreateCompatibleBitmap(screen, w, h);
    HBITMAP old = (HBITMAP)SelectObject(mem, bmp);
    BitBlt(mem, 0, 0, w, h, screen, minx, miny, SRCCOPY);

    int all = (_stricmp(mode, "all") == 0);
    int result = all ? 1 : 0;

    for (Py_ssize_t i = 0; i < count; i++) {
        int x = data[i*4] - minx, y = data[i*4+1] - miny;
        int exp = data[i*4+2], var = data[i*4+3];
        COLORREF f = GetPixel(mem, x, y);
        if (f == CLR_INVALID) {
            if (all) { result = 0; break; }
            continue;
        }
        int match = (abs((int)(f&0xFF)-((exp>>16)&0xFF)) <= var &&
                     abs((int)((f>>8)&0xFF)-((exp>>8)&0xFF)) <= var &&
                     abs((int)((f>>16)&0xFF)-(exp&0xFF)) <= var);
        if (all) { if (!match) { result = 0; break; } }
        else { if (match) { result = 1; break; } }
    }

    SelectObject(mem, old);
    DeleteObject(bmp);
    DeleteDC(mem);
    ReleaseDC(NULL, screen);
    PyBuffer_Release(&buf);
    if (result) Py_RETURN_TRUE;
    Py_RETURN_FALSE;
}

/* ==================== Cached Key for GIL-free loops ==================== */

typedef struct {
    int vk;
    int is_mouse;
    int is_ext;
} CachedKey;

/* Send a single key (down+up) using cached key data. GIL-free safe. */
static void _send_cached_key(const CachedKey* ck) {
    if (ck->is_mouse) {
        INPUT mi[2];
        _make_mouse_by_vk(&mi[0], ck->vk, 0);
        _make_mouse_by_vk(&mi[1], ck->vk, 1);
        SendInput(2, mi, sizeof(INPUT));
    } else if (ck->vk) {
        INPUT inp[2];
        memset(&inp[0], 0, sizeof(INPUT));
        inp[0].type = INPUT_KEYBOARD;
        inp[0].ki.wVk = (WORD)ck->vk;
        inp[0].ki.wScan = (WORD)MapVirtualKeyW(ck->vk, 0);
        if (ck->is_ext) inp[0].ki.dwFlags |= KEYEVENTF_EXTENDEDKEY;

        memset(&inp[1], 0, sizeof(INPUT));
        inp[1].type = INPUT_KEYBOARD;
        inp[1].ki.wVk = (WORD)ck->vk;
        inp[1].ki.wScan = (WORD)MapVirtualKeyW(ck->vk, 0);
        inp[1].ki.dwFlags = KEYEVENTF_KEYUP;
        if (ck->is_ext) inp[1].ki.dwFlags |= KEYEVENTF_EXTENDEDKEY;

        SendInput(2, inp, sizeof(INPUT));
    }
}

/* Send all cached keys as a batch (down+up pairs). GIL-free safe. */
static void _send_cached_batch(const CachedKey* ck, Py_ssize_t nkeys) {
    INPUT buf[256];
    int cnt = 0;
    for (Py_ssize_t i = 0; i < nkeys; i++) {
        if (ck[i].is_mouse) {
            if (cnt > 0) { SendInput(cnt, buf, sizeof(INPUT)); cnt = 0; }
            _send_cached_key(&ck[i]);
        } else if (ck[i].vk) {
            memset(&buf[cnt], 0, sizeof(INPUT));
            buf[cnt].type = INPUT_KEYBOARD;
            buf[cnt].ki.wVk = (WORD)ck[i].vk;
            buf[cnt].ki.wScan = (WORD)MapVirtualKeyW(ck[i].vk, 0);
            if (ck[i].is_ext) buf[cnt].ki.dwFlags |= KEYEVENTF_EXTENDEDKEY;
            cnt++;

            memset(&buf[cnt], 0, sizeof(INPUT));
            buf[cnt].type = INPUT_KEYBOARD;
            buf[cnt].ki.wVk = (WORD)ck[i].vk;
            buf[cnt].ki.wScan = (WORD)MapVirtualKeyW(ck[i].vk, 0);
            buf[cnt].ki.dwFlags = KEYEVENTF_KEYUP;
            if (ck[i].is_ext) buf[cnt].ki.dwFlags |= KEYEVENTF_EXTENDEDKEY;
            cnt++;
        }
        if (cnt >= 254) { SendInput(cnt, buf, sizeof(INPUT)); cnt = 0; }
    }
    if (cnt > 0) SendInput(cnt, buf, sizeof(INPUT));
}

/* Send cached keys one at a time with inter-key delay. GIL-free safe.
   Returns 1 if stop requested, 0 if completed normally. */
static int _send_cached_sequential(const CachedKey* ck, Py_ssize_t nkeys,
                                    double ikd_ms, volatile int* stop_flag) {
    for (Py_ssize_t i = 0; i < nkeys; i++) {
        if (*stop_flag) return 1;
        if (i > 0 && ikd_ms > 0.0) {
            _precise_sleep_internal(ikd_ms);
        }
        if (*stop_flag) return 1;
        _send_cached_key(&ck[i]);
    }
    return 0;
}

/* ==================== GIL-Free Hold Loop ==================== */

/* hold_loop: runs the ENTIRE hold loop in C with GIL released.
   stop_ptr points to a volatile int (1 = stop).
   game_ptr points to a volatile int (1 = game active).
   Returns number of iterations completed. */
static PyObject* native_hold_loop(PyObject* self, PyObject* args) {
    PyObject* keys_list;
    double interval_ms;
    double ikd_ms;
    long long stop_ptr_val;
    long long game_ptr_val;

    if (!PyArg_ParseTuple(args, "OddLL", &keys_list, &interval_ms, &ikd_ms,
                          &stop_ptr_val, &game_ptr_val))
        return NULL;

    volatile int* stop_flag = (volatile int*)stop_ptr_val;
    volatile int* game_flag = (volatile int*)game_ptr_val;

    Py_ssize_t nkeys = PyList_Size(keys_list);
    if (nkeys == 0) Py_RETURN_NONE;

    /* Cache key data while GIL is held */
    CachedKey* ck = (CachedKey*)malloc(nkeys * sizeof(CachedKey));
    if (!ck) Py_RETURN_NONE;

    int all_keyboard = 1;
    for (Py_ssize_t i = 0; i < nkeys; i++) {
        const char* name = PyUnicode_AsUTF8(PyList_GetItem(keys_list, i));
        ck[i].vk = _name_to_vk(name ? name : "");
        ck[i].is_mouse = name ? _is_mouse(name) : 0;
        ck[i].is_ext = name ? _is_ext(name) : 0;
        if (ck[i].is_mouse) all_keyboard = 0;
    }

    /* Pre-build batch INPUT array for keyboard-only macros (ikd==0) */
    INPUT* batch = NULL;
    int batch_count = 0;
    if (all_keyboard && ikd_ms <= 0.0) {
        batch_count = (int)nkeys * 2;
        batch = (INPUT*)malloc(batch_count * sizeof(INPUT));
        if (batch) {
            int idx = 0;
            for (Py_ssize_t i = 0; i < nkeys; i++) {
                if (!ck[i].vk) { batch_count -= 2; continue; }
                /* down */
                memset(&batch[idx], 0, sizeof(INPUT));
                batch[idx].type = INPUT_KEYBOARD;
                batch[idx].ki.wVk = (WORD)ck[i].vk;
                batch[idx].ki.wScan = (WORD)MapVirtualKeyW(ck[i].vk, 0);
                if (ck[i].is_ext) batch[idx].ki.dwFlags |= KEYEVENTF_EXTENDEDKEY;
                idx++;
                /* up */
                memset(&batch[idx], 0, sizeof(INPUT));
                batch[idx].type = INPUT_KEYBOARD;
                batch[idx].ki.wVk = (WORD)ck[i].vk;
                batch[idx].ki.wScan = (WORD)MapVirtualKeyW(ck[i].vk, 0);
                batch[idx].ki.dwFlags = KEYEVENTF_KEYUP;
                if (ck[i].is_ext) batch[idx].ki.dwFlags |= KEYEVENTF_EXTENDEDKEY;
                idx++;
            }
            batch_count = idx;
        }
    }

    int iterations = 0;

    /* === RELEASE GIL === */
    Py_BEGIN_ALLOW_THREADS

    while (!*stop_flag && *game_flag) {
        /* Send keys */
        if (batch && batch_count > 0) {
            /* Pre-built batch: single SendInput call, no struct building */
            SendInput(batch_count, batch, sizeof(INPUT));
        } else if (ikd_ms > 0.0 && nkeys > 1) {
            if (_send_cached_sequential(ck, nkeys, ikd_ms, stop_flag)) break;
        } else {
            _send_cached_batch(ck, nkeys);
        }

        if (*stop_flag || !*game_flag) break;

        /* Sleep for interval */
        if (interval_ms > 0.0) {
            double sl = interval_ms;
            if (qpc_ready) {
                if (sl > 5.0) { Sleep((DWORD)(sl - 2.0)); sl = 2.0; }
                LARGE_INTEGER s, c;
                QueryPerformanceCounter(&s);
                LONGLONG tgt = s.QuadPart + (LONGLONG)(qpc_freq.QuadPart * sl / 1000.0);
                while (!*stop_flag && *game_flag) {
                    SwitchToThread();
                    QueryPerformanceCounter(&c);
                    if (c.QuadPart >= tgt) break;
                }
            } else {
                Sleep((DWORD)sl);
            }
        }
        iterations++;
    }

    /* === REACQUIRE GIL === */
    Py_END_ALLOW_THREADS

    free(batch);
    free(ck);
    return PyLong_FromLong(iterations);
}

/* send_wait: send one cycle of keys + sleep, GIL released.
   Lighter version for when Python needs to check things between cycles. */
static PyObject* native_send_wait(PyObject* self, PyObject* args) {
    PyObject* keys_list;
    double interval_ms;
    double ikd_ms;
    long long stop_ptr_val;

    if (!PyArg_ParseTuple(args, "OddL", &keys_list, &interval_ms, &ikd_ms,
                          &stop_ptr_val))
        return NULL;

    volatile int* stop_flag = (volatile int*)stop_ptr_val;
    Py_ssize_t nkeys = PyList_Size(keys_list);
    if (nkeys == 0 || *stop_flag) Py_RETURN_NONE;

    /* Cache key data */
    CachedKey* ck = (CachedKey*)malloc(nkeys * sizeof(CachedKey));
    if (!ck) Py_RETURN_NONE;
    for (Py_ssize_t i = 0; i < nkeys; i++) {
        const char* name = PyUnicode_AsUTF8(PyList_GetItem(keys_list, i));
        ck[i].vk = _name_to_vk(name ? name : "");
        ck[i].is_mouse = name ? _is_mouse(name) : 0;
        ck[i].is_ext = name ? _is_ext(name) : 0;
    }

    /* RELEASE GIL */
    Py_BEGIN_ALLOW_THREADS

    /* Send keys */
    if (ikd_ms > 0.0 && nkeys > 1) {
        _send_cached_sequential(ck, nkeys, ikd_ms, stop_flag);
    } else {
        _send_cached_batch(ck, nkeys);
    }

    /* Sleep for interval */
    if (!*stop_flag && interval_ms > 0.0) {
        _precise_sleep_internal(interval_ms);
    }

    /* REACQUIRE GIL */
    Py_END_ALLOW_THREADS

    free(ck);
    Py_RETURN_NONE;
}

/* send_keys_once: send a full key sequence once (for press-mode macros).
   GIL released during send. Supports inter-key delay. */
static PyObject* native_send_keys_once(PyObject* self, PyObject* args) {
    PyObject* keys_list;
    double ikd_ms;

    if (!PyArg_ParseTuple(args, "Od", &keys_list, &ikd_ms))
        return NULL;

    Py_ssize_t nkeys = PyList_Size(keys_list);
    if (nkeys == 0) Py_RETURN_NONE;

    /* Cache key data */
    CachedKey* ck = (CachedKey*)malloc(nkeys * sizeof(CachedKey));
    if (!ck) Py_RETURN_NONE;
    for (Py_ssize_t i = 0; i < nkeys; i++) {
        const char* name = PyUnicode_AsUTF8(PyList_GetItem(keys_list, i));
        ck[i].vk = _name_to_vk(name ? name : "");
        ck[i].is_mouse = name ? _is_mouse(name) : 0;
        ck[i].is_ext = name ? _is_ext(name) : 0;
    }

    /* RELEASE GIL */
    Py_BEGIN_ALLOW_THREADS

    if (ikd_ms > 0.0 && nkeys > 1) {
        volatile int dummy_stop = 0;
        _send_cached_sequential(ck, nkeys, ikd_ms, &dummy_stop);
    } else {
        _send_cached_batch(ck, nkeys);
    }

    /* REACQUIRE GIL */
    Py_END_ALLOW_THREADS

    free(ck);
    Py_RETURN_NONE;
}

/* set_thread_priority: 0=normal, 1=below_normal, 2=above_normal, 3=high */
static PyObject* native_set_thread_priority(PyObject* self, PyObject* args) {
    int priority;
    if (!PyArg_ParseTuple(args, "i", &priority)) return NULL;
    int p;
    switch(priority) {
        case 0: p = THREAD_PRIORITY_NORMAL; break;
        case 1: p = THREAD_PRIORITY_BELOW_NORMAL; break;
        case 2: p = THREAD_PRIORITY_ABOVE_NORMAL; break;
        case 3: p = THREAD_PRIORITY_HIGHEST; break;
        default: p = THREAD_PRIORITY_NORMAL;
    }
    SetThreadPriority(GetCurrentThread(), p);
    Py_RETURN_NONE;
}

/* message_pump: runs GetMessageW loop with GIL released.
   Stops when WM_QUIT (0x0012) is received via PostThreadMessage.
   This allows WH_MOUSE_LL hook callbacks to acquire the GIL. */
static PyObject* native_message_pump(PyObject* self, PyObject* args) {
    MSG msg;

    /* Ensure message queue exists before hooks can be installed */
    PeekMessageW(&msg, NULL, 0, 0, 0);

    Py_BEGIN_ALLOW_THREADS

    while (GetMessageW(&msg, NULL, 0, 0) > 0) {
        if (msg.message == 0x0012) break; /* WM_QUIT */
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }

    Py_END_ALLOW_THREADS

    Py_RETURN_NONE;
}

/* ==================== Method Table ==================== */

static PyMethodDef methods[] = {
    {"init",                native_init,              METH_VARARGS, "Init DPI + QPC"},
    {"send_key",            native_send_key,          METH_VARARGS, "Send key down+up"},
    {"send_key_down",       native_send_key_down,     METH_VARARGS, "Send key down"},
    {"send_key_up",         native_send_key_up,       METH_VARARGS, "Send key up"},
    {"send_key_batch",      native_send_key_batch,    METH_VARARGS, "Batch send keys"},
    {"get_pixel_color",     native_get_pixel_color,   METH_VARARGS, "Get pixel 0xRRGGBB"},
    {"precise_sleep",       native_precise_sleep,     METH_VARARGS, "Precise sleep ms"},
    {"get_time",            native_get_time,          METH_NOARGS,  "QPC time in ms"},
    {"color_match",         native_color_match,       METH_VARARGS, "Color match check"},
    {"is_key_down",         native_is_key_down,       METH_VARARGS, "GetAsyncKeyState"},
    {"get_toggle_state",    native_get_toggle_state,  METH_VARARGS, "GetKeyState toggle"},
    {"name_to_vk",          native_name_to_vk,        METH_VARARGS, "Name->VK"},
    {"vk_to_name",          native_vk_to_name,        METH_VARARGS, "VK->name"},
    {"check_pixels",        native_check_pixels,      METH_VARARGS, "Check pixel dicts"},
    {"check_pixels_packed", native_check_pixels_packed,METH_VARARGS, "Check packed pixels"},
    {"capture_and_check",   native_capture_and_check,  METH_VARARGS, "BitBlt + check packed pixels"},
    {"hold_loop",           native_hold_loop,           METH_VARARGS, "GIL-free hold loop"},
    {"send_wait",           native_send_wait,           METH_VARARGS, "GIL-free send+wait"},
    {"send_keys_once",      native_send_keys_once,      METH_VARARGS, "GIL-free send keys once"},
    {"set_thread_priority", native_set_thread_priority, METH_VARARGS, "Set thread priority"},
    {"message_pump",        native_message_pump,        METH_NOARGS,  "GetMessage loop with GIL released"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef _native_module = {
    PyModuleDef_HEAD_INIT,
    "_native",
    "Native performance primitives for game macro automation",
    -1,
    methods
};

PyMODINIT_FUNC PyInit__native(void) {
    return PyModule_Create(&_native_module);
}
