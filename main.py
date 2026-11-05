import os 
import json 
from typing import Callable, Dict 
from logger_setup import get_logger 
from pdf_extractor import extract_pdf 
from design_agent import generate_slide_plan 
from slide_renderer import render_slide 
from tts_elevenlabs import synthesize_to_file 
from video_renderer import assemble_video 
from ppt_exporter import build_pptx 
from config import config
from theme_importer import extract_theme_colors  # NEW

logger = get_logger("main")

def apply_runtime_settings(settings: Dict): 
    if not settings: 
        return 
    # Toggle features 
    config.enable_animation = bool(settings.get("enable_animation", config.enable_animation)) 
    config.enable_emojis = bool(settings.get("enable_emojis", config.enable_emojis)) 
    config.enable_music = bool(settings.get("enable_music", config.enable_music)) 
    config.music_volume = float(settings.get("music_volume", config.music_volume)) 
    config.effect_profile = settings.get("effect_profile", config.effect_profile) 
    config.bullet_reveal = settings.get("bullet_reveal", config.bullet_reveal) 
    config.kenburns_zoom_min = float(settings.get("kenburns_zoom_min", config.kenburns_zoom_min)) 
    config.kenburns_zoom_max = float(settings.get("kenburns_zoom_max", config.kenburns_zoom_max)) 
    bg_music_path = settings.get("bg_music_path", "") 
    if bg_music_path: 
        config.bg_music_path = bg_music_path


def run_pipeline( 
    pdf_path: str, 
    template_path: str, 
    out_dir: str, 
    api_keys: Dict[str, str], 
    progress_cb: Callable[[str], None] = lambda m: None, 
    settings: Dict = None 
):
    if not pdf_path: 
        raise ValueError("No PDF selected")

    # Apply API keys/voice id for this run as environment variables
    if api_keys.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = api_keys["OPENAI_API_KEY"]
    if api_keys.get("ELEVENLABS_API_KEY"):
        os.environ["ELEVENLABS_API_KEY"] = api_keys["ELEVENLABS_API_KEY"]
    if api_keys.get("ELEVENLABS_VOICE_ID"):
        os.environ["ELEVENLABS_VOICE_ID"] = api_keys["ELEVENLABS_VOICE_ID"]

    # Apply runtime feature settings
    apply_runtime_settings(settings or {})

    os.makedirs(out_dir, exist_ok=True)
    assets_dir = os.path.join(out_dir, "assets")
    slides_dir = os.path.join(out_dir, "slides_raster")
    audio_dir = os.path.join(out_dir, "audio")
    video_dir = os.path.join(out_dir, "video")
    os.makedirs(assets_dir, exist_ok=True)

    progress_cb("Extracting PDF...")
    extracted = extract_pdf(pdf_path, assets_dir)
    with open(os.path.join(out_dir, "extracted_text.json"), "w", encoding="utf-8") as f:
        json.dump(extracted, f, ensure_ascii=False, indent=2)

    progress_cb("Generating slide plan via GPT...")
    plan = generate_slide_plan(extracted["pages"], extracted["images"])
    slides = plan["slides"]
    with open(os.path.join(out_dir, "slides.json"), "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    # Enrich slides with logical assets and emojis
    try:
        from asset_selection import choose_images_for_slide
    except Exception:
        choose_images_for_slide = None
    try:
        from emoji_mapper import suggest_emojis_for_slide
    except Exception:
        suggest_emojis_for_slide = None

    if choose_images_for_slide:
        progress_cb("Selecting logical images for slides...")
        for s in slides:
            if not s.get("image_refs"):
                s["image_refs"] = choose_images_for_slide(s, extracted["images"])
    if config.enable_emojis and suggest_emojis_for_slide:
        progress_cb("Adding tasteful emojis...")
        for i, s in enumerate(slides):
            slides[i] = suggest_emojis_for_slide(s)

    # Extract theme from PPTX (if provided) and apply to slides for consistency
    theme = None
    if template_path and os.path.exists(template_path):
        theme = extract_theme_colors(template_path)
        # Override AI colors with template theme for visual consistency
        for i, s in enumerate(slides):
            vs = s.get("visual_style") or {}
            vs["theme_color"] = theme.get("bg_color", vs.get("theme_color", "#0f172a"))
            vs["accent_color"] = theme.get("accent_color", vs.get("accent_color", "#38bdf8"))
            s["visual_style"] = vs
            slides[i] = s

    progress_cb("Synthesizing narration (ElevenLabs)...")
    os.makedirs(audio_dir, exist_ok=True)
    for i, slide in enumerate(slides, start=1):
        text = slide.get("narration_script") or "This slide is intentionally left blank."
        synthesize_to_file(text, os.path.join(audio_dir, f"slide_{i:02d}.mp3"))

    # Render static PNGs (used for PPTX and as fallback)
    progress_cb("Rendering slides to PNG...")
    os.makedirs(slides_dir, exist_ok=True)
    for i, slide in enumerate(slides, start=1):
        render_slide(slide, os.path.join(slides_dir, f"slide_{i:02d}.png"), theme=theme)

    # Optional PPTX export
    try:
        pptx_out = os.path.join(out_dir, "output.pptx")
        build_pptx(slides, pptx_out, template_path)
        progress_cb(f"PPTX exported: {pptx_out}")
    except Exception as e:
        logger.warning(f"Failed to build PPTX: {e}")

    progress_cb("Composing video...")
    os.makedirs(video_dir, exist_ok=True)
    video_out = os.path.join(video_dir, "output.mp4")
    assemble_video(slides, slides_dir, audio_dir, video_out)
    progress_cb(f"Video generated: {video_out}")
    return video_out
