from pptx import Presentation
from pptx.dml.color import RGBColor

def _rgb_to_hex(rgb) -> str | None:
    if rgb is None:
        return None
    # Try tuple-like first
    try:
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
    except Exception:
        pass
    # Try integer-like fallback
    try:
        ival = int(rgb)
        return f"#{ival:06x}"
    except Exception:
        return None

def extract_theme_colors(pptx_path: str):
    """
    Extract a minimal theme palette from a PPTX template:
    - bg_color: light1 or slide master background color if available
    - fg_color: dark1/text color
    - accent_color: accent1
    Fallbacks provided if anything is missing.
    """
    colors = {"bg_color": "#0f172a", "fg_color": "#e5e7eb", "accent_color": "#38bdf8"}
    try:
        prs = Presentation(pptx_path)
        scheme = prs.slide_master.theme.theme_color_scheme

        # Try scheme-based colors
        try:
            bg_hex = _rgb_to_hex(scheme.light1.rgb) or _rgb_to_hex(scheme.light2.rgb)
            if bg_hex:
                colors["bg_color"] = bg_hex
        except Exception:
            pass

        try:
            fg_hex = _rgb_to_hex(scheme.dark1.rgb) or _rgb_to_hex(scheme.dark2.rgb)
            if fg_hex:
                colors["fg_color"] = fg_hex
        except Exception:
            pass

        try:
            acc_hex = _rgb_to_hex(scheme.accent1.rgb) or _rgb_to_hex(scheme.accent2.rgb)
            if acc_hex:
                colors["accent_color"] = acc_hex
        except Exception:
            pass

        # If slide master explicitly defines a background color, prefer it
        try:
            bg_fill = prs.slide_master.background.fill
            if bg_fill and bg_fill.fore_color and bg_fill.fore_color.rgb:
                explicit_bg = _rgb_to_hex(bg_fill.fore_color.rgb)
                if explicit_bg:
                    colors["bg_color"] = explicit_bg
        except Exception:
            pass

    except Exception:
        # Keep defaults on any failure
        pass

    return colors
