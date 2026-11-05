import os
from typing import List, Dict, Any, Tuple
from pptx import Presentation
from pptx.util import Emu
from pptx.enum.shapes import PP_PLACEHOLDER
from logger_setup import get_logger
from config import config

logger = get_logger("pptx")

# ------------------------------
# Internal utility functions
# ------------------------------

def _pick_layout_by_name(prs: Presentation, slide_spec: Dict[str, Any]):
    """
    Choose a layout that best matches the desired structure.
    Uses fuzzy name matching to common layout names in templates.
    """
    desired = ((slide_spec.get("visual_style") or {}).get("layout") or "title-bullets-left").lower()

    # Map desired layout to preferred layout name patterns
    preferences = []
    if desired in ("title-bullets-left", "title-bullets-right", "title-bullets-bottom"):
        preferences = [
            ("title and content",),
            ("content with caption",),
            ("title only",),
        ]
    elif desired == "split":
        preferences = [
            ("two content",),
            ("comparison",),
            ("content with caption",),
        ]
    else:
        preferences = [("title and content",)]

    layouts = list(prs.slide_layouts)
    name_to_layout = [(i, (getattr(l, "name", "") or "").lower(), l) for i, l in enumerate(layouts)]

    # Try preferences in order
    for preference in preferences:
        for _, name, layout in name_to_layout:
            if all(token in name for token in preference):
                return layout

    # Fallback to "Title and Content" if exists
    for _, name, layout in name_to_layout:
        if "title and content" in name:
            return layout

    # Final fallback
    return prs.slide_layouts[1] if len(prs.slide_layouts) > 1 else prs.slide_layouts[0]


def _find_text_placeholder(slide, types=None):
    """
    Find a text-capable placeholder. Prefer BODY, but fallback to other title/body variants.
    """
    if types is None:
        types = (
            PP_PLACEHOLDER.BODY,
            PP_PLACEHOLDER.TITLE,
            PP_PLACEHOLDER.CENTER_TITLE,
            PP_PLACEHOLDER.SUBTITLE,
            PP_PLACEHOLDER.VERTICAL_BODY,
            PP_PLACEHOLDER.VERTICAL_TITLE,
        )

    preferred_order = [
        PP_PLACEHOLDER.BODY,
        PP_PLACEHOLDER.VERTICAL_BODY,
        PP_PLACEHOLDER.TITLE,
        PP_PLACEHOLDER.CENTER_TITLE,
        PP_PLACEHOLDER.SUBTITLE,
        PP_PLACEHOLDER.VERTICAL_TITLE,
    ]

    # First pass: exact preferred order
    for want in preferred_order:
        for ph in slide.placeholders:
            try:
                if ph.placeholder_format.type == want and hasattr(ph, "text_frame"):
                    return ph
            except Exception:
                continue

    # Second pass: any in provided types
    for ph in slide.placeholders:
        try:
            if ph.placeholder_format.type in types and hasattr(ph, "text_frame"):
                return ph
        except Exception:
            continue

    return None


def _find_picture_placeholder(slide):
    """Find a picture placeholder if available."""
    for ph in slide.placeholders:
        try:
            if ph.placeholder_format.type == PP_PLACEHOLDER.PICTURE:
                return ph
        except Exception:
            continue
    return None


def _px_to_emu(prs: Presentation, x_px: int, total_px: int, total_emu: Emu) -> Emu:
    """Convert pixels to EMU based on total size proportion."""
    return int(total_emu * (x_px / float(total_px)))


def _content_area_for_layout(prs: Presentation, layout_name: str) -> Tuple[int, int, int, int]:
    """
    Approximate area for a freeform image when no picture placeholder is present.
    Uses the same proportional logic as PNG renderer for consistency.
    Returns EMU values: (left, top, width, height)
    """
    W_px, H_px = config.slide_width, config.slide_height
    W_emu, H_emu = prs.slide_width, prs.slide_height

    if layout_name == "title-bullets-right":
        ix, iy, iw, ih = (int(W_px * 0.6), 180, int(W_px * 0.35), int(H_px * 0.6))
    elif layout_name == "title-bullets-bottom":
        ix, iy, iw, ih = (80, int(H_px * 0.55), int(W_px * 0.6), int(H_px * 0.35))
    elif layout_name == "split":
        ix, iy, iw, ih = (80, 180, int(W_px * 0.4), int(H_px * 0.7))
    else:
        ix, iy, iw, ih = (80, 180, int(W_px * 0.35), int(H_px * 0.6))

    left = _px_to_emu(prs, ix, W_px, W_emu)
    top = _px_to_emu(prs, iy, H_px, H_emu)
    width = _px_to_emu(prs, iw, W_px, W_emu)
    height = _px_to_emu(prs, ih, H_px, H_emu)
    return left, top, width, height


# ------------------------------
# Main export functions
# ------------------------------

def build_pptx(slides: List[Dict[str, Any]], out_path: str, template_path: str = None):
    """
    Build a PPTX by reusing template layouts so styles, background, colors, and fonts are inherited.
    - Chooses a layout per slide based on desired visual_style.layout.
    - Fills title and body placeholders (no explicit font formatting to preserve theme).
    - Inserts image into picture placeholder if present; otherwise places it in a consistent area.
    """
    prs = Presentation(template_path) if template_path and os.path.exists(template_path) else Presentation()

    for idx, slide_spec in enumerate(slides, start=1):
        layout = _pick_layout_by_name(prs, slide_spec)
        slide = prs.slides.add_slide(layout)

        # Title
        if slide.shapes.title is not None:
            try:
                title_text = slide_spec.get("title", "")
                slide.shapes.title.text = title_text
            except Exception:
                pass

        # Body/content placeholder
        body_ph = _find_text_placeholder(slide)
        if body_ph is not None:
            try:
                tf = body_ph.text_frame
                tf.clear()
                bullets = slide_spec.get("bullets", []) or []
                for i, b in enumerate(bullets):
                    p = tf.add_paragraph() if i > 0 else tf.paragraphs[0]
                    p.text = str(b)
                    p.level = 0
                # Do not manipulate run fonts to preserve template typography
            except Exception:
                pass

        # Images: prefer a picture placeholder
        img_paths = [p for p in (slide_spec.get("image_refs") or []) if p and os.path.exists(p)]
        if img_paths:
            image_path = img_paths[0]
            pic_ph = _find_picture_placeholder(slide)
            try:
                if pic_ph is not None:
                    pic_ph.insert_picture(image_path)
                else:
                    # Place image in an area that matches our PNG renderer geometry
                    desired_layout = (slide_spec.get("visual_style") or {}).get("layout", "title-bullets-left")
                    left, top, width, height = _content_area_for_layout(prs, desired_layout)
                    slide.shapes.add_picture(image_path, left, top, width=width, height=height)
            except Exception as e:
                logger.warning(f"Failed to insert image on slide {idx}: {e}")

    prs.save(out_path)
    logger.info(f"PPTX written: {out_path}")


def export_pptx_to_mp4_via_com(pptx_path: str, out_mp4: str):
    """
    Export a PPTX presentation to MP4 using the Windows PowerPoint COM interface.
    Only works on Windows with PowerPoint installed.
    """
    try:
        import win32com.client
        from time import sleep

        ppApp = win32com.client.Dispatch("PowerPoint.Application")
        ppApp.Visible = True
        pres = ppApp.Presentations.Open(pptx_path, WithWindow=False)

        # CreateVideo(FileName, UseTimingsAndNarrations, DefaultSlideDuration, VertResolution, FramesPerSecond, Quality)
        pres.CreateVideo(out_mp4, False, 6, 1080, 30, 85)

        while pres.CreateVideoStatus == 1:
            sleep(1)

        pres.Close()
        ppApp.Quit()
        logger.info(f"Exported video via PowerPoint: {out_mp4}")

    except Exception as e:
        logger.error(f"PowerPoint export failed: {e}")
        raise
