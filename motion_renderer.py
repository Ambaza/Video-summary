import os
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
from moviepy.editor import (
    CompositeVideoClip, ImageClip, ColorClip, AudioFileClip
)
from PIL import Image, ImageDraw
from config import config
from slide_renderer import _load_font, wrap_text, _emoji_to_twemoji_filename


# ---------------------------------------------------------
# Layout computation
# ---------------------------------------------------------
def _compute_layout(W: int, H: int, layout: str) -> Tuple[Tuple[int, int, int, int], Tuple[int, int, int, int]]:
    """Compute bullet and image areas depending on layout."""
    if layout == "title-bullets-right":
        bullet_area = (80, 160, int(W * 0.55), H - 80)
        image_area = (int(W * 0.6), 180, int(W * 0.35), int(H * 0.6))
    elif layout == "title-bullets-bottom":
        bullet_area = (80, 160, W - 80, int(H * 0.5))
        image_area = (80, int(H * 0.55), int(W * 0.6), int(H * 0.35))
    elif layout == "split":
        bullet_area = (int(W * 0.52), 160, W - 80, H - 80)
        image_area = (80, 180, int(W * 0.4), int(H * 0.7))
    else:
        bullet_area = (int(W * 0.45), 160, W - 80, H - 80)
        image_area = (80, 180, int(W * 0.35), int(H * 0.6))
    return bullet_area, image_area


# ---------------------------------------------------------
# Title rendering
# ---------------------------------------------------------
def _render_title_layer(slide: Dict[str, Any], fg: str, accent: str) -> ImageClip:
    W, H = config.slide_width, config.slide_height
    title = slide.get("title", "Slide")
    title_emoji = (slide.get("title_emoji") or "").strip()
    title_font = _load_font(56)

    canvas = Image.new("RGBA", (W, 140), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    tx, ty = 60, 40

    if title_emoji and config.enable_emojis:
        ep = _emoji_to_twemoji_filename(title_emoji)
        if os.path.exists(ep):
            try:
                eimg = Image.open(ep).convert("RGBA")
                eimg.thumbnail((64, 64), Image.LANCZOS)
                canvas.paste(eimg, (tx, ty - 6), eimg)
                tx += eimg.width + 12
            except Exception:
                pass

    draw.text((tx, ty), title, fill=fg, font=title_font)
    draw.line([40, 110, W - 40, 110], fill=accent, width=4)

    # Convert PIL image to NumPy array for MoviePy
    np_img = np.array(canvas)
    title_clip = ImageClip(np_img).set_position(("left", "top")).set_duration(10)
    title_clip = (
        title_clip.set_start(0)
        .set_opacity(lambda t: min(1, t / 0.4))
        .set_position(lambda t: (0, -10 + 10 * min(1, t / 0.4)))
    )
    return title_clip


# ---------------------------------------------------------
# Bullets rendering
# ---------------------------------------------------------
def _render_bullet_layers(slide: Dict[str, Any], fg: str) -> List[Tuple[ImageClip, int]]:
    W, H = config.slide_width, config.slide_height
    layout = (slide.get("visual_style") or {}).get("layout", "title-bullets-left")
    bullets = slide.get("bullets", [])
    bullet_emojis = slide.get("bullet_emojis", [])
    bullet_font = _load_font(36)
    reveal_style = config.bullet_reveal

    bx, by, bw, bh = _compute_layout(W, H, layout)[0]
    line_y = by
    line_spacing = 12
    layers = []
    emoji_size = (36, 36)

    for idx, b in enumerate(bullets):
        canvas = Image.new("RGBA", (W, 80), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        ex = bx

        # Emoji
        if config.enable_emojis and idx < len(bullet_emojis) and bullet_emojis[idx]:
            ep = _emoji_to_twemoji_filename(bullet_emojis[idx])
            if os.path.exists(ep):
                try:
                    eimg = Image.open(ep).convert("RGBA")
                    eimg.thumbnail(emoji_size, Image.LANCZOS)
                    canvas.paste(eimg, (ex, 0), eimg)
                    ex += eimg.width + 10
                except Exception:
                    pass

        # Wrap text
        fake_draw = ImageDraw.Draw(Image.new("RGBA", (bw, 200), (0, 0, 0, 0)))
        lines = wrap_text(str(b), bullet_font, bw - 40, fake_draw)
        text = lines[0] if lines else ""
        draw.text((ex, 0), ("• " if ex == bx else "") + text, fill=fg, font=bullet_font)

        np_img = np.array(canvas)
        clip = ImageClip(np_img).set_position(("left", line_y))

        # Reveal animations
        if reveal_style == "fade":
            clip = clip.set_opacity(lambda t: min(1, max(0, t / 0.3)))
        elif reveal_style == "slide":
            clip = clip.set_position(lambda t, y=line_y: (0, y + (20 * (1 - min(1, max(0, t / 0.3))))))
        else:  # fade-slide
            clip = clip.set_opacity(lambda t: min(1, max(0, t / 0.3)))
            clip = clip.set_position(lambda t, y=line_y: (0, y + (20 * (1 - min(1, max(0, t / 0.3))))))

        layers.append((clip, line_y))
        line_y += bullet_font.size + 4 + line_spacing

    return layers


# ---------------------------------------------------------
# Image rendering
# ---------------------------------------------------------
def _render_image_layer(slide: Dict[str, Any]) -> Optional[ImageClip]:
    W, H = config.slide_width, config.slide_height
    layout = (slide.get("visual_style") or {}).get("layout", "title-bullets-left")
    _, (ix, iy, iw, ih) = _compute_layout(W, H, layout)

    img_refs = [p for p in (slide.get("image_refs") or []) if os.path.exists(p)]
    if not img_refs:
        return None

    img = Image.open(img_refs[0]).convert("RGB")
    img.thumbnail((iw, ih), Image.LANCZOS)

    mask = Image.new("L", img.size, 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0, 0, img.size[0], img.size[1]], radius=24, fill=255)

    rounded = Image.new("RGBA", img.size, (0, 0, 0, 0))
    rounded.paste(img, (0, 0), mask)

    np_img = np.array(rounded)
    clip = ImageClip(np_img).set_position((ix, iy))
    motion = ((slide.get("visual_style") or {}).get("effects") or {}).get("motion", "kenburns-slow")

    if motion != "none":
        zmin, zmax = config.kenburns_zoom_min, config.kenburns_zoom_max
        zoom_delta = zmax - zmin
        clip = clip.resize(lambda t: zmin + zoom_delta * min(1, t / 8.0))  # slow zoom-in

    return clip


# ---------------------------------------------------------
# Timing computation
# ---------------------------------------------------------
def _timings_for_bullets(audio_dur: float, n: int) -> List[float]:
    if n <= 0:
        return []
    intro = min(1.0, audio_dur * 0.08)
    remain = max(0.0, audio_dur - intro)
    base = remain / n if n else 0
    starts = []
    cur = intro
    for _ in range(n):
        starts.append(cur)
        cur += base
    return starts


# ---------------------------------------------------------
# Main motion composition
# ---------------------------------------------------------
def render_motion_clip(slide: Dict[str, Any], audio_path: str) -> CompositeVideoClip:
    W, H = config.slide_width, config.slide_height
    vs = slide.get("visual_style") or {}
    theme_color = vs.get("theme_color", "#0f172a")
    accent = vs.get("accent_color", "#38bdf8")
    fg = "#e5e7eb"

    audio = AudioFileClip(audio_path)
    duration = audio.duration

    bg = ColorClip(size=(W, H), color=_hex_to_rgb(theme_color)).set_duration(duration)
    title_layer = _render_title_layer(slide, fg=fg, accent=accent).set_duration(duration)

    image_layer = _render_image_layer(slide)
    if image_layer is not None:
        image_layer = image_layer.set_duration(duration)

    bullet_layers = _render_bullet_layers(slide, fg=fg)
    starts = _timings_for_bullets(duration, len(bullet_layers))

    layers = [bg, title_layer]
    if image_layer is not None:
        layers.append(image_layer)
    for (clip, y), st in zip(bullet_layers, starts):
        layers.append(clip.set_start(st))

    comp = CompositeVideoClip(layers, size=(W, H)).set_audio(audio).set_duration(duration)
    return comp


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def _hex_to_rgb(h: str) -> Tuple[int, int, int]:
    """Convert hex color string to RGB tuple."""
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join([c * 2 for c in h])
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

