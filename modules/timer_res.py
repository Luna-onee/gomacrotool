import ctypes

_winmm = ctypes.windll.winmm
_ref_count = 0
_is_set = False


def set_high_resolution():
    global _ref_count, _is_set
    _ref_count += 1
    if not _is_set:
        _winmm.timeBeginPeriod(1)
        _is_set = True


def restore_default():
    global _ref_count, _is_set
    _ref_count = max(0, _ref_count - 1)
    if _ref_count == 0 and _is_set:
        _winmm.timeEndPeriod(1)
        _is_set = False
