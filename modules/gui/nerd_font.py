"""NerdFont icon helpers for PyQt6.

Tries common NerdFont families and falls back to Segoe UI.
Provides icon codepoints for common UI symbols.
"""
from PyQt6.QtGui import QFont, QFontDatabase

# Common NerdFont family names on Windows
_NERD_FAMILIES = [
    "JetBrainsMono Nerd Font",
    "JetBrainsMono NF",
    "FiraCode Nerd Font",
    "FiraCode NF",
    "Hack Nerd Font",
    "Hack NF",
    "CaskaydiaCove Nerd Font",
    "CaskaydiaCove NF",
    "CaskaydiaCove NFM",
    "MesloLGS NF",
    "MesloLGS Nerd Font",
    "DejaVuSansM Nerd Font",
    "DejaVuSansM NF",
]

_cached_font = None
_cached_family = None


def get_family():
    """Return the best available NerdFont family name, or 'Segoe UI'."""
    global _cached_family
    if _cached_family is not None:
        return _cached_family

    families = QFontDatabase.families()
    families_lower = {f.lower() for f in families}

    for name in _NERD_FAMILIES:
        if name.lower() in families_lower:
            _cached_family = name
            return _cached_family

    # Try partial match
    for fam in families:
        fam_l = fam.lower()
        if "nerd" in fam_l or "nf" in fam_l.split() or "nfm" in fam_l.split():
            _cached_family = fam
            return _cached_family

    _cached_family = "Segoe UI"
    return _cached_family


def get_font(size=10, weight=QFont.Weight.Normal):
    """Return a QFont using the best available NerdFont family."""
    global _cached_font
    if _cached_font is not None and _cached_font.pointSize() == size and _cached_font.weight() == weight:
        return _cached_font

    font = QFont(get_family(), size, weight)
    _cached_font = font
    return font


# NerdFont codepoints (Font Awesome / Material / Codicons mix)
class ICONS:
    """Common NerdFont icon codepoints."""
    # Actions
    PLUS = "\uf067"
    PENCIL = "\uf040"
    POWER = "\uf011"
    TRASH = "\uf014"
    COG = "\uf013"
    SEARCH = "\uf002"
    REFRESH = "\uf021"
    RELOAD = "\uf021"
    COPY = "\uf0c5"
    FOLDER = "\uf07b"
    FOLDER_OPEN = "\uf07c"
    X = "\uf00d"
    MINUS = "\uf068"

    # Theme
    SUN = "\uf185"
    MOON = "\uf186"

    # Toggle
    TOGGLE = "\uf204"  # generic toggle icon
    TOGGLE_ON = "\uf205"
    TOGGLE_OFF = "\uf204"

    # Status / State
    CIRCLE = "\uf111"       # filled
    CIRCLE_O = "\uf10c"     # empty
    CHECK = "\uf00c"
    TIMES = "\uf00d"
    BOLT = "\uf0e7"
    FIRE = "\uf06d"
    STAR = "\uf005"
    STAR_O = "\uf006"
    HEART = "\uf004"

    # Navigation / UI
    CHEVRON_DOWN = "\uf078"
    CHEVRON_UP = "\uf077"
    CHEVRON_LEFT = "\uf053"
    CHEVRON_RIGHT = "\uf054"
    ARROW_DOWN = "\uf063"
    ARROW_UP = "\uf062"
    ARROW_LEFT = "\uf060"
    ARROW_RIGHT = "\uf061"

    # Game / Input
    GAMEPAD = "\uf11b"
    KEYBOARD = "\uf11c"
    MOUSE = "\uf245"
    DESKTOP = "\uf108"

    # Time
    CLOCK = "\uf017"
    HOURGLASS = "\uf254"

    # Misc
    ELLIPSIS = "\uf141"
    BARS = "\uf0c9"
    INFO = "\uf129"
    QUESTION = "\uf128"
    EXCLAMATION = "\uf12a"
    EYE = "\uf06e"
    EYE_SLASH = "\uf070"
    LOCK = "\uf023"
    UNLOCK = "\uf09c"


def get_icon(name: str) -> str:
    """Get an icon by name (uppercase). Returns empty string if unknown."""
    return getattr(ICONS, name.upper(), "")
