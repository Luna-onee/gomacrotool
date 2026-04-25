"""
Material Design 3 QSS generator for PyQt6.
Covers all widgets with proper M3 tokens, state layers, and elevation.
"""
import os
from modules.theme import theme


def _c(name):
    """Shorthand for theme color lookup."""
    return theme.colors().get(name, "#000000")


def generate_qss(arrow_down_path=None, arrow_right_path=None):
    """Generate the full M3 QSS stylesheet."""
    t = theme.colors()
    bg = t["bg"]
    sc_low = t["surfaceContainerLow"]
    sc = t["surfaceContainer"]
    sc_hi = t["surfaceContainerHigh"]
    surf_hi = t["surfaceHigh"]
    surf_bright = t["surfaceBright"]
    text = t["text"]
    text_sec = t["textSecondary"]
    primary = t["primary"]
    on_primary = t["onPrimary"]
    primary_c = t["primaryContainer"]
    on_primary_c = t["onPrimaryContainer"]
    secondary = t["secondary"]
    on_secondary = t["onSecondary"]
    secondary_c = t["secondaryContainer"]
    on_secondary_c = t["onSecondaryContainer"]
    tertiary = t["tertiary"]
    on_tertiary = t["onTertiary"]
    tertiary_c = t["tertiaryContainer"]
    on_tertiary_c = t["onTertiaryContainer"]
    outline = t["outline"]
    outline_var = t["outlineVariant"]
    error = t["error"]
    error_c = t["errorContainer"]
    on_error_c = t["onErrorContainer"]
    success = t["success"]
    success_c = t["successContainer"]
    on_success_c = t["onSuccessContainer"]

    # M3 state-layer opacity
    hover_opacity = "18"
    pressed_opacity = "12"
    focused_opacity = "12"
    dragged_opacity = "16"

    down_img = f"url({arrow_down_path})" if arrow_down_path else "none"
    right_img = f"url({arrow_right_path})" if arrow_right_path else "none"

    return f"""
/* ============================================================
   Material Design 3 — Base
   ============================================================ */

QWidget {{
    background: transparent;
    color: {text};
    font-family: 'Segoe UI', 'Segoe UI Variable', sans-serif;
    font-size: 10pt;
}}

/* ── Main Window & Dialog base ── */
QMainWindow, QDialog {{
    background-color: {sc};
    color: {text};
}}

/* Frameless dialog overlay card */
QFrame[class="dialog-card"] {{
    background-color: {sc_hi};
    border-radius: 16px;
    border: none;
}}

/* ── Title bar (used in frameless windows) */
QFrame[class="titlebar"] {{
    background-color: {surf_hi};
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
    border-bottom: 1px solid {outline_var};
}}

/* ── Card surfaces (profile, settings, etc.) */
QFrame[class="card"] {{
    background-color: {sc_low};
    border-radius: 10px;
    border: none;
}}

/* ── Titlebar labels in main window ── */
QLabel[class="titlebar-icon"] {{
    color: {primary};
    background: transparent;
    border: none;
    font-size: 14px;
}}
QLabel[class="titlebar-title"] {{
    color: {text};
    background: transparent;
    border: none;
    font-weight: bold;
}}
QPushButton[class="titlebar-btn"] {{
    background: transparent;
    color: {text_sec};
    border: none;
    border-radius: 6px;
    font-size: 13px;
    padding: 0px;
    min-height: 0px;
}}
QPushButton[class="titlebar-btn"]:hover {{
    background-color: {sc_hi};
    color: {text};
}}
QPushButton[class="titlebar-close"] {{
    background: transparent;
    color: {text_sec};
    border: none;
    border-top-right-radius: 8px;
    border-bottom-left-radius: 6px;
    border-bottom-right-radius: 6px;
    font-size: 12px;
    font-weight: bold;
    padding: 0px;
    min-height: 0px;
}}
QPushButton[class="titlebar-close"]:hover {{
    background-color: #C42B1C;
    color: white;
}}

/* ── M3-named titlebar (alias) */
QFrame[class="m3-titlebar"] {{
    background-color: {surf_hi};
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
    border-bottom: 1px solid {outline_var};
}}

/* ── Labels ── */
QLabel {{
    background: transparent;
    color: {text};
    border: none;
}}
QLabel[class="sec"] {{ color: {text_sec}; }}
QLabel[class="primary-label"] {{ color: {primary}; }}
QLabel[class="tertiary-label"] {{ color: {tertiary}; }}
QLabel[class="error-label"] {{ color: {error}; }}
QLabel[class="success-label"] {{ color: {success}; }}

/* ── Text inputs ── */
QLineEdit, QTextEdit {{
    background-color: {sc_low};
    color: {text};
    border: 1px solid {outline_var};
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: {primary};
    selection-color: {on_primary};
}}
QLineEdit:focus, QTextEdit:focus {{
    border: 2px solid {primary};
    padding: 5px 9px;
}}
QLineEdit:disabled, QTextEdit:disabled {{
    opacity: 0.45;
}}
QLineEdit[readOnly="true"] {{
    background-color: {sc};
    color: {text_sec};
}}

/* ── ComboBox ── */
QComboBox {{
    background-color: {sc_low};
    color: {text};
    border: 1px solid {outline_var};
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 22px;
}}
QComboBox:hover {{ border-color: {secondary}; }}
QComboBox:focus {{ border: 2px solid {primary}; padding: 5px 9px; }}
QComboBox:disabled {{ opacity: 0.45; }}
QComboBox::drop-down {{
    background-color: transparent;
    border: none;
    width: 24px;
    subcontrol-origin: padding;
    subcontrol-position: right center;
}}
QComboBox::down-arrow {{
    image: {down_img};
    background: transparent;
    width: 12px;
    height: 8px;
    margin-right: 8px;
}}
QComboBox QAbstractItemView,
QComboBox QListView {{
    background-color: {sc_hi};
    color: {text};
    border: 1px solid {outline_var};
    selection-background-color: {primary_c};
    selection-color: {on_primary_c};
    outline: none;
}}
QComboBox::item {{
    background-color: transparent;
    color: {text};
    padding: 4px 8px;
    border-radius: 0px;
}}
QComboBox::item:alternate {{
    background-color: transparent;
    color: {text};
}}
QComboBox::item:hover {{
    background-color: {primary_c};
    color: {on_primary_c};
}}
QComboBox::item:selected {{
    background-color: {primary_c};
    color: {on_primary_c};
}}
QComboBox QListView::item {{
    background-color: transparent;
    color: {text};
    padding: 4px 8px;
    border-radius: 0px;
}}
QComboBox QListView::item:selected {{
    background-color: {primary_c};
    color: {on_primary_c};
}}
QComboBox QListView::item:hover {{
    background-color: {primary_c};
    color: {on_primary_c};
}}

/* ── SpinBox ── */
QSpinBox, QDoubleSpinBox {{
    background-color: {sc_low};
    color: {text};
    border: 1px solid {outline_var};
    border-radius: 6px;
    padding: 5px 8px;
}}
QSpinBox:hover, QDoubleSpinBox:hover {{ border-color: {secondary}; }}
QSpinBox:focus, QDoubleSpinBox:focus {{ border: 2px solid {primary}; padding: 4px 7px; }}
QSpinBox:disabled, QDoubleSpinBox:disabled {{ opacity: 0.45; }}
QSpinBox::up-button, QDoubleSpinBox::up-button {{
    border: none;
    width: 16px;
    subcontrol-origin: padding;
    subcontrol-position: top right;
}}
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    border: none;
    width: 16px;
    subcontrol-origin: padding;
    subcontrol-position: bottom right;
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid {text_sec};
}}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {text_sec};
}}

/* ── CheckBox ── */
QCheckBox {{
    color: {text};
    spacing: 8px;
    background: transparent;
    min-height: 20px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid {outline};
    background: transparent;
    margin-left: 2px;
}}
QCheckBox::indicator:hover {{ border-color: {secondary}; }}
QCheckBox::indicator:checked {{
    background-color: {primary};
    border: 2px solid {primary};
}}
QCheckBox::indicator:checked::after {{
    /* not supported in Qt QSS */
}}
QCheckBox::indicator:indeterminate {{
    background-color: {primary_c};
    border-color: {primary};
}}
QCheckBox:disabled {{ opacity: 0.45; }}

/* ── RadioButton ── */
QRadioButton {{
    color: {text};
    spacing: 8px;
    background: transparent;
    min-height: 20px;
}}
QRadioButton::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 9px;
    border: 2px solid {outline};
    background: transparent;
}}
QRadioButton::indicator:hover {{ border-color: {secondary}; }}
QRadioButton::indicator:checked {{
    border-color: {primary};
    background-color: {primary};
}}
QRadioButton:disabled {{ opacity: 0.45; }}

/* ── Buttons — M3 Filled (primary action) ── */
QPushButton[class="btn-filled"] {{
    background-color: {primary};
    color: {on_primary};
    border: 1px solid transparent;
    border-radius: 14px;
    padding: 8px 24px;
    font-weight: 600;
    font-size: 10pt;
    min-height: 30px;
}}
QPushButton[class="btn-filled"]:hover {{
    background-color: {on_primary_c};
    color: {primary};
}}
QPushButton[class="btn-filled"]:pressed {{
    background-color: {primary};
    opacity: 0.78;
}}
QPushButton[class="btn-filled"]:disabled {{
    opacity: 0.38;
}}

/* ── Buttons — M3 Filled Tonal ── */
QPushButton[class="btn-tonal"] {{
    background-color: {primary_c};
    color: {on_primary_c};
    border: 1px solid transparent;
    border-radius: 14px;
    padding: 8px 24px;
    font-weight: 600;
    min-height: 30px;
}}
QPushButton[class="btn-tonal"]:hover {{
    background-color: {primary};
    color: {on_primary};
}}
QPushButton[class="btn-tonal"]:pressed {{
    opacity: 0.78;
}}
QPushButton[class="btn-tonal"]:disabled {{ opacity: 0.38; }}

/* ── Buttons — M3 Outlined ── */
QPushButton[class="btn-outlined"] {{
    background-color: transparent;
    color: {primary};
    border: 1px solid {outline};
    border-radius: 14px;
    padding: 8px 24px;
    font-weight: 600;
    min-height: 30px;
}}
QPushButton[class="btn-outlined"]:hover {{
    background-color: {primary_c};
    border-color: {primary};
}}
QPushButton[class="btn-outlined"]:pressed {{
    opacity: 0.78;
}}
QPushButton[class="btn-outlined"]:disabled {{
    opacity: 0.38;
    border-color: {outline_var};
}}

/* ── Buttons — M3 Text (no container) ── */
QPushButton[class="btn-text"] {{
    background-color: transparent;
    color: {primary};
    border: 1px solid transparent;
    border-radius: 14px;
    padding: 8px 16px;
    font-weight: 600;
    min-height: 30px;
}}
QPushButton[class="btn-text"]:hover {{ background-color: {primary_c}; }}
QPushButton[class="btn-text"]:pressed {{ opacity: 0.78; }}
QPushButton[class="btn-text"]:disabled {{ opacity: 0.38; }}

/* ── Buttons — Surface tint (secondary actions) ── */
QPushButton[class="btn-surface"] {{
    background-color: {secondary_c};
    color: {on_secondary_c};
    border: 1px solid transparent;
    border-radius: 14px;
    padding: 8px 24px;
    font-weight: 600;
    min-height: 30px;
}}
QPushButton[class="btn-surface"]:hover {{
    background-color: {secondary};
    color: {on_secondary};
}}
QPushButton[class="btn-surface"]:pressed {{ opacity: 0.78; }}
QPushButton[class="btn-surface"]:disabled {{ opacity: 0.38; }}

/* ── Buttons — Danger / error ── */
QPushButton[class="btn-danger"] {{
    background-color: {error};
    color: {on_error_c};
    border: 1px solid transparent;
    border-radius: 14px;
    padding: 8px 24px;
    font-weight: 600;
    min-height: 30px;
}}
QPushButton[class="btn-danger"]:hover {{
    background-color: {error_c};
    color: {on_error_c};
}}
QPushButton[class="btn-danger"]:pressed {{ opacity: 0.78; }}
QPushButton[class="btn-danger"]:disabled {{ opacity: 0.38; }}

/* ── Generic push button (base for unclassed QPushButton) ── */
QPushButton {{
    border-radius: 14px;
    border: 1px solid transparent;
    padding: 6px 16px;
    font-weight: 600;
    min-height: 24px;
}}

/* ── Tooltip ── */
QToolTip {{
    background-color: {surf_hi};
    color: {text};
    border: 1px solid {outline_var};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 9pt;
}}

/* ── Tables ── */
QTableWidget, QTableView {{
    background-color: {sc_low};
    color: {text};
    border: 1px solid {outline_var};
    border-radius: 12px;
    gridline-color: {outline_var};
    outline: none;
    font-size: 10pt;
}}
QTableWidget::item, QTableView::item {{
    padding: 4px 8px;
    border-bottom: 1px solid {outline_var};
}}
QTableWidget::item:selected, QTableView::item:selected {{
    background-color: {primary};
    color: {on_primary};
    font-weight: 600;
}}
QTableWidget::item:hover, QTableView::item:hover {{
    background-color: {secondary_c};
}}
QHeaderView::section {{
    background-color: {surf_hi};
    color: {text};
    border: none;
    border-bottom: 2px solid {outline_var};
    padding: 6px 8px;
    font-weight: 600;
    font-size: 9pt;
}}
QHeaderView::section:first {{
    border-top-left-radius: 11px;
}}
QHeaderView::section:last {{
    border-top-right-radius: 11px;
    border-right: none;
}}
QTableCornerButton::section {{
    background-color: {surf_hi};
    border: none;
}}
QTableWidget QTableCornerButton::section {{
    border-top-left-radius: 12px;
}}

/* ── ScrollBars ── */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {outline_var};
    border-radius: 3px;
    min-height: 32px;
    margin: 0px 1px;
}}
QScrollBar::handle:vertical:hover {{ background: {secondary}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
    margin: 0px;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal {{
    background: {outline_var};
    border-radius: 3px;
    min-width: 32px;
    margin: 1px 0px;
}}
QScrollBar::handle:horizontal:hover {{ background: {secondary}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
}}

/* ── Tab bar ── */
QTabBar::tab {{
    background: transparent;
    color: {text_sec};
    padding: 8px 16px;
    border-bottom: 2px solid transparent;
    font-weight: 500;
}}
QTabBar::tab:selected {{
    color: {primary};
    border-bottom: 2px solid {primary};
}}
QTabBar::tab:hover:!selected {{
    color: {text};
    background: {sc_low};
}}
QTabWidget::pane {{
    border: none;
    background: transparent;
}}

/* ── Sliders ── */
QSlider::groove:horizontal {{
    border: none;
    height: 4px;
    background: {outline_var};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {primary};
    border: none;
    width: 16px;
    height: 16px;
    border-radius: 8px;
    margin: -6px 0;
}}
QSlider::handle:horizontal:hover {{
    background: {primary};
    border: 2px solid {on_primary};
}}
QSlider::groove:vertical {{
    border: none;
    width: 4px;
    background: {outline_var};
    border-radius: 2px;
}}
QSlider::handle:vertical {{
    background: {primary};
    border: none;
    width: 16px;
    height: 16px;
    border-radius: 8px;
    margin: 0 -6px;
}}

/* ── Progress bar ── */
QProgressBar {{
    background: {outline_var};
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background: {primary};
    border-radius: 4px;
}}

/* ── Menu ── */
QMenu {{
    background-color: {sc_hi};
    color: {text};
    border: 1px solid {outline_var};
    padding: 4px;
}}
QMenu::item {{
    background-color: transparent;
    color: {text};
    padding: 8px 12px;
    border-radius: 0px;
}}
QMenu::item:selected {{
    background-color: {primary_c};
    color: {on_primary_c};
}}
QMenu::separator {{
    height: 1px;
    background: {outline_var};
    margin: 4px 0;
}}
QMenu::indicator {{
    background-color: transparent;
    width: 18px;
    height: 18px;
}}
QMenu::icon {{
    background-color: transparent;
}}
QMenu::right-arrow {{
    image: {right_img};
    background: transparent;
    width: 8px;
    height: 12px;
    margin-right: 4px;
}}

/* ── Message / File dialog ── */
QMessageBox {{
    background-color: {sc_hi};
    color: {text};
}}
QFileDialog {{
    background-color: {sc_hi};
    color: {text};
}}

/* ── Status bar ── */
QStatusBar {{
    background-color: {surf_hi};
    color: {text_sec};
    border-top: 1px solid {outline_var};
    padding: 2px 8px;
}}

/* ── Splitter ── */
QSplitter::handle {{
    background: {outline_var};
}}
QSplitter::handle:hover {{
    background: {secondary};
}}

/* ── Dialog frameless window styling ── */
QFrame[class="dialog-backdrop"] {{
    background-color: rgba(0, 0, 0, 0.45);
}}
"""


def _generate_arrow_images():
    """Generate small arrow PNGs for QSS use. Returns (down_path, right_path)."""
    from PyQt6.QtGui import QPainter, QPixmap, QColor, QPolygon
    from PyQt6.QtCore import Qt, QPoint

    cache_dir = os.path.join(os.path.dirname(__file__), "__qss_cache")
    os.makedirs(cache_dir, exist_ok=True)

    down_path = os.path.join(cache_dir, "arrow_down.png")
    right_path = os.path.join(cache_dir, "arrow_right.png")
    color = QColor(_c("textSecondary"))

    if not os.path.exists(down_path):
        pm = QPixmap(12, 8)
        pm.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(QPolygon([QPoint(1, 1), QPoint(11, 1), QPoint(6, 7)]))
        painter.end()
        pm.save(down_path)

    if not os.path.exists(right_path):
        pm = QPixmap(8, 12)
        pm.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(QPolygon([QPoint(1, 1), QPoint(7, 6), QPoint(1, 11)]))
        painter.end()
        pm.save(right_path)

    return down_path, right_path


def apply_theme(app):
    """Apply the M3 QSS stylesheet to a QApplication instance."""
    app.setStyle("Fusion")

    # Try NerdFont for icon support, fall back to Segoe UI
    from modules.gui.nerd_font import get_font
    app.setFont(get_font(10))

    t = theme.colors()
    from PyQt6.QtGui import QPalette, QColor
    pal = QPalette()
    c = lambda name: QColor(t.get(name, "#000000"))
    pal.setColor(QPalette.ColorRole.Window,          c("surfaceContainer"))
    pal.setColor(QPalette.ColorRole.WindowText,      c("text"))
    pal.setColor(QPalette.ColorRole.Base,            c("surfaceContainerLow"))
    pal.setColor(QPalette.ColorRole.AlternateBase,   c("surfaceContainerHigh"))
    pal.setColor(QPalette.ColorRole.Text,            c("text"))
    pal.setColor(QPalette.ColorRole.Button,          c("surfaceContainerLow"))
    pal.setColor(QPalette.ColorRole.ButtonText,      c("text"))
    pal.setColor(QPalette.ColorRole.Highlight,       c("primaryContainer"))
    pal.setColor(QPalette.ColorRole.HighlightedText, c("onPrimaryContainer"))
    pal.setColor(QPalette.ColorRole.ToolTipBase,     c("surfaceHigh"))
    pal.setColor(QPalette.ColorRole.ToolTipText,     c("text"))
    pal.setColor(QPalette.ColorRole.PlaceholderText, c("textSecondary"))
    # 3D bevel roles used by some styles — force dark to avoid white leakage
    pal.setColor(QPalette.ColorRole.Light,     c("surfaceContainerHigh"))
    pal.setColor(QPalette.ColorRole.Midlight,  c("surfaceContainer"))
    pal.setColor(QPalette.ColorRole.Dark,      c("surfaceContainerLow"))
    pal.setColor(QPalette.ColorRole.Mid,       c("outline"))
    pal.setColor(QPalette.ColorRole.Shadow,    c("bg"))
    app.setPalette(pal)

    # Force every QComboBox to use a QListView for its popup — this is the
    # only reliable way to make the dropdown respect QSS on Windows PyQt6.
    _fix_combo_popups()

    down_path, right_path = _generate_arrow_images()
    app.setStyleSheet(generate_qss(arrow_down_path=down_path, arrow_right_path=right_path))


def _fix_combo_popups():
    """Monkey-patch QComboBox so all popups use QListView and respect QSS."""
    from PyQt6.QtWidgets import QComboBox, QListView
    if getattr(QComboBox, "_popup_fixed", False):
        return
    _orig = QComboBox.__init__
    def _init(self, *args, **kwargs):
        _orig(self, *args, **kwargs)
        self.setView(QListView())
    QComboBox.__init__ = _init
    QComboBox._popup_fixed = True
