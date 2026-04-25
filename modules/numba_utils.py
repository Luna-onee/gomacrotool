"""
Numba-accelerated pixel and color matching.
Falls back to pure Python if numba is unavailable.
"""

try:
    from numba import jit
    import numpy as np
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False
    np = None


# =============================================================================
# Color matching (the hot path in pixel detection)
# =============================================================================

if HAS_NUMBA:
    @jit(nopython=True, cache=True, parallel=True)
    def _color_match_vec(r1, g1, b1, r2, g2, b2, v):
        """Vectorized color match: returns True if colors are within variation."""
        return (abs(r1 - r2) <= v and
                abs(g1 - g2) <= v and
                abs(b1 - b2) <= v)

    @jit(nopython=True, cache=True)
    def _color_match_scalar(r1, g1, b1, r2, g2, b2, v):
        """Scalar color match."""
        return (abs(r1 - r2) <= v and
                abs(g1 - g2) <= v and
                abs(b1 - b2) <= v)
else:
    # Pure Python fallback
    def _color_match_vec(r1, g1, b1, r2, g2, b2, v):
        return (abs(r1 - r2) <= v and
                abs(g1 - g2) <= v and
                abs(b1 - b2) <= v)

    def _color_match_scalar(r1, g1, b1, r2, g2, b2, v):
        return (abs(r1 - r2) <= v and
                abs(g1 - g2) <= v and
                abs(b1 - b2) <= v)


# =============================================================================
# Packed pixel matching (x, y, color_int, variation per pixel)
# Uses numpy structured arrays for cache-efficient batch processing
# =============================================================================

if HAS_NUMBA:
    @jit(nopython=True, cache=True)
    def _match_pixels_packed_inner(found_colors, expected_colors, variations, match_mode):
        """
        Core inner loop for pixel matching.
        
        Args:
            found_colors: (N, 3) array of [r, g, b] values from screen
            expected_colors: (N, 3) array of [r, g, b] expected values
            variations: (N,) array of variation thresholds
            match_mode: 0 = all must match, 1 = any can match
        
        Returns:
            True/False for match
        """
        n = len(found_colors)
        if n == 0:
            return False
        
        if match_mode == 0:  # all
            for i in range(n):
                r1, g1, b1 = found_colors[i]
                r2, g2, b2 = expected_colors[i]
                v = variations[i]
                if not (abs(r1 - r2) <= v and
                        abs(g1 - g2) <= v and
                        abs(b1 - b2) <= v):
                    return False
            return True
        else:  # any
            for i in range(n):
                r1, g1, b1 = found_colors[i]
                r2, g2, b2 = expected_colors[i]
                v = variations[i]
                if (abs(r1 - r2) <= v and
                    abs(g1 - g2) <= v and
                    abs(b1 - b2) <= v):
                    return True
            return False

    @jit(nopython=True, cache=True)
    def _get_pixels_from_bitmap_inner(bmp_data, stride, x_coords, y_coords):
        """
        Extract pixel colors from a bitmap buffer.
        
        Args:
            bmp_data: flat array of BGRA bytes from GetDIBits
            stride: bytes per row in bitmap
            x_coords: (N,) array of x positions
            y_coords: (N,) array of y positions
        
        Returns:
            (N, 3) array of [r, g, b] values
        """
        n = len(x_coords)
        result = np.zeros((n, 3), dtype=np.uint8)
        
        for i in range(n):
            x = x_coords[i]
            y = y_coords[i]
            # BGRA format in Windows DIB
            pixel_offset = y * stride + x * 4
            b = bmp_data[pixel_offset]
            g = bmp_data[pixel_offset + 1]
            r = bmp_data[pixel_offset + 2]
            result[i, 0] = r
            result[i, 1] = g
            result[i, 2] = b
        
        return result
else:
    def _match_pixels_packed_inner(found_colors, expected_colors, variations, match_mode):
        n = len(found_colors)
        if n == 0:
            return False
        
        if match_mode == 0:  # all
            for i in range(n):
                r1, g1, b1 = found_colors[i]
                r2, g2, b2 = expected_colors[i]
                v = variations[i]
                if not (abs(r1 - r2) <= v and
                        abs(g1 - g2) <= v and
                        abs(b1 - b2) <= v):
                    return False
            return True
        else:  # any
            for i in range(n):
                r1, g1, b1 = found_colors[i]
                r2, g2, b2 = expected_colors[i]
                v = variations[i]
                if (abs(r1 - r2) <= v and
                    abs(g1 - g2) <= v and
                    abs(b1 - b2) <= v):
                    return True
            return False
    
    def _get_pixels_from_bitmap_inner(bmp_data, stride, x_coords, y_coords):
        n = len(x_coords)
        result = np.zeros((n, 3), dtype=np.uint8) if np else None
        for i in range(n):
            x = x_coords[i]
            y = y_coords[i]
            pixel_offset = y * stride + x * 4
            if np:
                b = bmp_data[pixel_offset]
                g = bmp_data[pixel_offset + 1]
                r = bmp_data[pixel_offset + 2]
                result[i, 0] = r
                result[i, 1] = g
                result[i, 2] = b
        return result


# =============================================================================
# High-level API functions
# =============================================================================

def color_match(c1, c2, v):
    """Check if two colors match within variation (hex strings or ints)."""
    if isinstance(c1, str):
        c1 = int(c1, 16)
    if isinstance(c2, str):
        c2 = int(c2, 16)
    
    r1 = (c1 >> 16) & 0xFF
    g1 = (c1 >> 8) & 0xFF
    b1 = c1 & 0xFF
    r2 = (c2 >> 16) & 0xFF
    g2 = (c2 >> 8) & 0xFF
    b2 = c2 & 0xFF
    
    return _color_match_scalar(r1, g1, b1, r2, g2, b2, v)


def match_pixels_batch(xyz_var_arrays, found_colors, match_mode="all"):
    """
    Match a batch of pixels efficiently.
    
    Args:
        xyz_var_arrays: (N, 4) numpy array where each row is [x, y, color_int, variation]
        found_colors: (N, 3) numpy array of [r, g, b] values
        match_mode: "all" or "any"
    
    Returns:
        True if matched, False otherwise
    """
    if not HAS_NUMBA or xyz_var_arrays is None or len(xyz_var_arrays) == 0:
        return False
    
    n = len(xyz_var_arrays)
    expected = np.zeros((n, 3), dtype=np.uint8)
    variations = np.zeros(n, dtype=np.int32)
    
    for i in range(n):
        color_int = int(xyz_var_arrays[i, 2])
        expected[i, 0] = (color_int >> 16) & 0xFF  # r
        expected[i, 1] = (color_int >> 8) & 0xFF   # g
        expected[i, 2] = color_int & 0xFF          # b
        variations[i] = int(xyz_var_arrays[i, 3])
    
    mode = 0 if match_mode == "all" else 1
    return _match_pixels_packed_inner(found_colors, expected, variations, mode)


def unpack_pixels_to_arrays(pixels):
    """
    Convert list of pixel dicts to numpy arrays for fast matching.
    
    Args:
        pixels: list of {"x": int, "y": int, "color": str/int, "variation": int}
    
    Returns:
        (N, 4) numpy array [x, y, color_int, variation]
    """
    if not HAS_NUMBA or not pixels:
        return None
    
    n = len(pixels)
    arr = np.zeros((n, 4), dtype=np.int32)
    
    for i, px in enumerate(pixels):
        arr[i, 0] = px.get("x", 0)
        arr[i, 1] = px.get("y", 0)
        c = px.get("color", 0)
        if isinstance(c, str):
            c = int(c, 16)
        arr[i, 2] = c
        arr[i, 3] = px.get("variation", 10)
    
    return arr


def warm_up():
    """Trigger JIT compilation at load time to avoid first-call latency."""
    if not HAS_NUMBA:
        return
    
    # Warm up the JIT-compiled functions with dummy data
    dummy_colors = np.zeros((2, 3), dtype=np.uint8)
    dummy_variations = np.array([10, 10], dtype=np.int32)
    _match_pixels_packed_inner(dummy_colors, dummy_colors, dummy_variations, 0)
    _match_pixels_packed_inner(dummy_colors, dummy_colors, dummy_variations, 1)


# Auto warm-up on import
if HAS_NUMBA:
    warm_up()
