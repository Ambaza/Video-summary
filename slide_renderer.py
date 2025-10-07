from typing import Dict, Any, Tuple, List, Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
import re

from logger_setup import get_logger
from config import config

logger = get_logger("render")


def _load_font(size: int) -> ImageFont.ImageFont:
    """
    Try common OS font paths, fallback to PIL default font.
    """
    # Prefer raw strings for Windows path
    candidates = [
        r"C:\Windows\Fonts\arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        try:
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def wrap_text(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
    """
    Wrap `text` into lines so each line fits into max_width when measured with `draw.textlength`.
    """
    if not text:
        return []
    words = text.split()
    lines: List[str] = []
    cur = ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _rounded_image_with_shadow(src_path: str, size: Tuple[int, int], radius: int = 24) -> Tuple[Optional[Image.Image], Optional[Image.Image]]:
    """
    Returns (shadow_image, rounded_image) or (None, None) if the path does not exist.
    shadow_image and rounded_image are RGBA images ready to be pasted.
    """
    if not src_path or not os.path.exists(src_path):
        return None, None

    img = Image.open(src_path).convert("RGBA")
    img.thumbnail(size, Image.LANCZOS)
    w, h = img.size

    # Rounded mask
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0, 0, w, h], radius=radius, fill=255)

    # Shadow (slightly larger to allow blur offset)
    shadow_w, shadow_h = w + 20, h + 20
    shadow = Image.new("RGBA", (shadow_w, shadow_h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle([10, 10, 10 + w, 10 + h], radius=radius, fill=(0, 0, 0, 180))
    shadow = shadow.filter(ImageFilter.GaussianBlur(10))

    # Rounded image on transparent background using mask
    rounded = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    rounded.paste(img, (0, 0), mask=mask)

    return shadow, rounded


def _emoji_to_twemoji_filename(emoji: str) -> str:
    """
    Convert emoji string into a twemoji-style filename using codepoints (hex lowercased).
    Skips variation selector FE0F and zero-width-joiner 200D in the output filename.
    """
    if not emoji:
        return ""
    codepoints: List[str] = []
    for ch in emoji:
        cp = f"{ord(ch):x}"  # hex without 0x, lower-case
        if cp in ("fe0f", "200d"):
            continue
        codepoints.append(cp)
    if not codepoints:
        return ""
    name = "-".join(codepoints)
    return os.path.join(config.emoji_pack_dir, f"{name}.png")


def _draw_title_with_emphasis(draw: ImageDraw.ImageDraw, title: str, x: int, y: int,
                              font: ImageFont.ImageFont, fg: str, accent: str,
                              emphasis_words: List[str]) -> None:
    """
    Draw title text at (x,y) and underline any emphasis_words found in the title.
    Underline is drawn with the 'accent' color.
    """
    title_str = str(title or "")
    # Draw the title first
    draw.text((x, y), title_str, fill=fg, font=font)

    if not emphasis_words:
        return

    # measure text height for baseline calculation
    try:
        text_height = font.getsize(title_str)[1]
    except Exception:
        # fallback to a reasonable estimate
        text_height = getattr(font, "size", 16)

    baseline = y + text_height + 6

    try:
        for ew in emphasis_words:
            if not ew:
                continue
            # case-insensitive search
            m = re.search(re.escape(ew), title_str, flags=re.IGNORECASE)
            if not m:
                continue
            pre = title_str[:m.start()]
            pre_w = draw.textlength(pre, font=font)
            ew_text = title_str[m.start():m.end()]
            ew_w = draw.textlength(ew_text, font=font)
            start_x = x + int(pre_w)
            end_x = start_x + int(ew_w)
            draw.line([start_x, baseline, end_x, baseline], fill=accent, width=4)
    except Exception:
        # don't break drawing on any unexpected font/measurement issues
        logger.exception("Error drawing emphasis underline")


def render_slide(slide_spec: Dict[str, Any], out_path: str, theme: Optional[Dict[str, Any]] = None) -> None:
    """
    Render a slide according to slide_spec and save to out_path (PNG).
    """
    W, H = config.slide_width, config.slide_height
    theme = theme or {}
    bg_color = theme.get("bg_color", "#0f172a")
    accent = (slide_spec.get("visual_style", {}) or {}).get("accent_color") or theme.get("accent_color", "#38bdf8")
    fg = theme.get("fg_color", "#e5e7eb")
    layout = (slide_spec.get("visual_style", {}) or {}).get("layout", "title-bullets-left")

    bg = Image.new("RGB", (W, H), color=bg_color)
    draw = ImageDraw.Draw(bg)
    title_font = _load_font(56)
    bullet_font = _load_font(36)

    title = slide_spec.get("title", "Slide")
    title_emoji = (slide_spec.get("title_emoji") or "").strip()
    emphasis_words = (slide_spec.get("visual_style", {}) or {}).get("emphasis_words", []) or []

    # Accent bar
    draw.line([40, 110, W - 40, 110], fill=accent, width=4)

    # Title with optional emoji
    tx = 60
    ty = 40
    if title_emoji and getattr(config, "enable_emojis", False):
        emoji_path = _emoji_to_twemoji_filename(title_emoji)
        if emoji_path and os.path.exists(emoji_path):
            try:
                eimg = Image.open(emoji_path).convert("RGBA")
                eimg.thumbnail((64, 64), Image.LANCZOS)
                bg.paste(eimg, (tx, ty - 6), eimg)
                tx += eimg.width + 12
            except Exception:
                logger.debug("Failed to paste title emoji", exc_info=True)

    _draw_title_with_emphasis(draw, title, tx, ty, title_font, fg, accent, emphasis_words)

    # Layout regions: define as (x, y, width, height)
    if layout == "title-bullets-right":
        bullet_area = (80, 160, int(W * 0.55) - 80, H - 80 - 160)
        image_area = (int(W * 0.6), 180, int(W * 0.35), int(H * 0.6))
    elif layout == "title-bullets-bottom":
        bullet_area = (80, 160, W - 160, int(H * 0.5) - 160)
        image_area = (80, int(H * 0.55), int(W * 0.6), int(H * 0.35))
    elif layout == "split":
        bullet_area = (int(W * 0.52), 160, W - 80 - int(W * 0.52), H - 80 - 160)
        image_area = (80, 180, int(W * 0.4), int(H * 0.7))
    else:
        # default: title left, bullets right
        bullet_area = (int(W * 0.45), 160, W - 80 - int(W * 0.45), H - 80 - 160)
        image_area = (80, 180, int(W * 0.35), int(H * 0.6))

    # Draw bullets
    bullets = slide_spec.get("bullets", []) or []
    bullet_emojis = slide_spec.get("bullet_emojis", []) or []
    bx, by, bw, bh = bullet_area
    line_y = by
    line_spacing = 12
    max_bullet_width = bw - 40

    for idx, b in enumerate(bullets):
        lines = wrap_text(str(b), bullet_font, max_bullet_width, draw)
        # Optional emoji for the bullet
        ex = bx
        emoji_drawn = False
        if getattr(config, "enable_emojis", False) and idx < len(bullet_emojis) and bullet_emojis[idx]:
            ep = _emoji_to_twemoji_filename(bullet_emojis[idx])
            if ep and os.path.exists(ep):
                try:
                    eimg = Image.open(ep).convert("RGBA")
                    eimg.thumbnail((36, 36), Image.LANCZOS)
                    bg.paste(eimg, (bx, line_y), eimg)
                    ex = bx + eimg.width + 10
                    emoji_drawn = True
                except Exception:
                    logger.debug("Failed to draw bullet emoji", exc_info=True)

        for i, l in enumerate(lines):
            prefix = "• " if i == 0 and not emoji_drawn else ""
            draw.text((ex, line_y), prefix + l, fill=fg, font=bullet_font)
            # update vertical position using font metrics if available
            try:
                line_height = bullet_font.getsize(l)[1]
            except Exception:
                line_height = getattr(bullet_font, "size", 36)
            line_y += line_height + 4

        line_y += line_spacing

    # Image(s)
    img_refs = [p for p in (slide_spec.get("image_refs") or []) if p and os.path.exists(p)]
    if img_refs:
        ix, iy, iw, ih = image_area
        shadow, rounded = _rounded_image_with_shadow(img_refs[0], (iw, ih), radius=24)
        if rounded is not None:
            rw, rh = rounded.size
            paste_x = ix + max(0, (iw - rw) // 2)
            paste_y = iy + max(0, (ih - rh) // 2)
            if shadow:
                # shadow image is larger by 20 px pad: place it offset by -10 to align
                bg.paste(shadow, (paste_x - 10, paste_y - 10), shadow)
            bg.paste(rounded, (paste_x, paste_y), rounded)

    # Ensure output directory exists and save
    out_dir = os.path.dirname(out_path) or "."
    os.makedirs(out_dir, exist_ok=True)
    bg.save(out_path, "PNG")
    logger.info(f"Slide rendered: {out_path}")
