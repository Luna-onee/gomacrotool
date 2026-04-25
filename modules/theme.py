# Material Design 3 — Surface tonal elevation (dark theme)
# Surfaces rise from bg through surfaceContainer to surfaceHigh
# Primary: vibrant pink-red (high contrast on dark), Tertiary: soft teal
DARK = {
    # Surfaces (tonal elevation — M3 spec)
    "bg":                   "#1C1719",   # Base / background
    "surfaceContainerLow":  "#1F191C",   # Cards / panels — lowest elevation
    "surfaceContainer":     "#241C20",   # Main content surfaces
    "surfaceContainerHigh": "#2C2528",   # Elevated cards, dialogs
    "surfaceHigh":          "#352E31",   # Titlebar, highest elevation
    "surfaceBright":        "#3E3639",   # Hover states, active surfaces

    # Text
    "text":                 "#EDE0E4",   # Primary text — warm white
    "textSecondary":        "#A8949C",   # Secondary / label text

    # Primary — vivid rose-pink (M3 Secondary/Primary blend)
    "primary":              "#E09AAE",   # Main accent, buttons, active states
    "onPrimary":            "#3D111D",   # Text/icons ON primary
    "primaryContainer":      "#5D2035",   # Tonal container for primary surface
    "onPrimaryContainer":    "#FFD9E3",   # Text ON primary container

    # Secondary
    "secondary":            "#C8ACBA",   # Secondary labels, icons
    "onSecondary":          "#36242E",   # Text/icons ON secondary
    "secondaryContainer":   "#483444",   # Tonal container
    "onSecondaryContainer":  "#E6CAD6",   # Text ON secondary container

    # Tertiary — soft teal accent
    "tertiary":             "#8CCED4",   # Tertiary labels, decorative
    "onTertiary":           "#1D3D40",   # Text/icons ON tertiary
    "tertiaryContainer":    "#2F5458",   # Tonal container
    "onTertiaryContainer":  "#BFF1F5",   # Text ON tertiary container

    # Outlines / borders (M3 outline hierarchy)
    "outline":              "#998C94",   # Default border / divider
    "outlineVariant":       "#4D434B",   # Subtle border / separator

    # Semantic
    "error":                "#F2B8B5",   # Error text/icon
    "errorContainer":       "#8C3330",   # Error surface
    "onErrorContainer":     "#FFDAD6",   # Text ON error container
    "success":               "#9DD5B8",   # Success text/icon (muted green)
    "successContainer":     "#1D4D35",   # Success surface
    "onSuccessContainer":    "#C8F5D8",   # Text ON success container

    # Shadows
    "shadow":               "#000000",   # Elevation shadow color
}

# Material Design 3 — Light theme
LIGHT = {
    "bg":                   "#FEF7F8",
    "surfaceContainerLow":  "#F9ECEE",
    "surfaceContainer":     "#F4E3E6",
    "surfaceContainerHigh": "#EDE0E2",
    "surfaceHigh":          "#E7D8DB",
    "surfaceBright":        "#FFF8FA",

    "text":                 "#23191C",
    "textSecondary":        "#6D5F65",

    "primary":              "#B03A62",
    "onPrimary":            "#FFFFFF",
    "primaryContainer":      "#FFD9E3",
    "onPrimaryContainer":    "#3D0015",

    "secondary":            "#7D5A6A",
    "onSecondary":          "#FFFFFF",
    "secondaryContainer":   "#FFD8E8",
    "onSecondaryContainer":  "#311126",

    "tertiary":             "#4D6972",
    "onTertiary":           "#FFFFFF",
    "tertiaryContainer":    "#C8F0F5",
    "onTertiaryContainer":  "#052024",

    "outline":              "#99797F",
    "outlineVariant":       "#DBC8CD",

    "error":                "#BA1A1A",
    "errorContainer":       "#FFDAD6",
    "onErrorContainer":     "#410002",
    "success":              "#1E6941",
    "successContainer":     "#B4F1CE",
    "onSuccessContainer":   "#002111",

    "shadow":               "#000000",
}


class ThemeManager:
    def __init__(self):
        self.dark_mode = True
        self._colors = DARK

    def get(self, name):
        return self._colors.get(name, "#000000")

    def set_dark_mode(self, dark):
        self.dark_mode = dark
        self._colors = DARK if dark else LIGHT

    def colors(self):
        return self._colors


theme = ThemeManager()