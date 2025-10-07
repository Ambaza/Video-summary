import os 
import json 
from typing import Any, Dict, List 
from openai import OpenAI 
from logger_setup import get_logger 
from config import config

logger = get_logger("design")

def build_prompt(pages: List[Dict[str, Any]], images: List[Dict[str, Any]]) -> str: 
    joined = "\n\n".join([f"Page {p['page_number']}:\n{p['text']}" for p in pages[:50]])
    # include page reference with image list img_lines = [] for im in images: img_lines.append(f"page {im['page']}: {im['path']}") img_block = "\n".join(img_lines)
    img_list = [im['path'] for im in images]
    img_block = "\n".join(img_list)
    prompt = f"""
    You are a presentation designer. Summarize the following PDF into an engaging slide deck of 6-10 slides.
    Return a single JSON object: {{ "slides": [ ... ] }}. No commentary.
    For each slide, produce fields:
    - title: string
    - title_emoji: optional string (e.g., "🎯") or ""
    - bullets: array of 3-5 succinct bullet strings
    - bullet_emojis: optional array, same length as bullets, items can be "" if omitted
    - narration_script: 80-140 words conversational voiceover
    - source_pages: array of integers (1-based) indicating which PDF pages informed this slide
    - image_refs: list of suggested image filenames chosen from the list below; prefer images whose "page X" matches source_pages; 0-2 paths max
    - visual_style: object with:
    - theme_color (hex)
    - accent_color (hex)
    - layout: "title-bullets-left" | "title-bullets-right" | "title-bullets-bottom" | "split"
    - bg_style: "solid" | "gradient" | "image"
    - emphasis_words: list of words to highlight in the title
    - effects: object:
        motion: "none" | "kenburns-slow" | "kenburns-normal"
        transition_in: "fade" | "slide-up" | "zoom-in"
        transition_out: "fade" | "slide-left"
        intro_emphasis: "none" | "underline" | "sparkle"
        bg_overlay: "none" | "bokeh-soft" | "grid"
    - timings: optional object
    - intro_sec: float
    - per_bullet_sec: array of floats (length equals bullets)

    Source text: 
    {joined}

    List of available extracted images (use these exact paths): 
    {img_block}
    """
    return prompt


def _strip_code_fences(s: str) -> str:
    s = s.strip() 
    if s.startswith(""): 
        lines = s.splitlines() 
        if lines: lines = lines[1:] 
        if lines and lines[-1].strip().startswith(""): 
            lines = lines[:-1] 
        return "\n".join(lines).strip() 
    return s

def _safe_parse_json(content: str) -> Dict[str, Any]: 
    if not content or not content.strip(): 
        raise ValueError("Empty content from model.") 
    raw = content 
    # First try direct parse 
    try: 
        return json.loads(raw) 
    except Exception: 
        pass 
    # Try stripping code fences 
    try: 
        stripped = _strip_code_fences(raw) 
        return json.loads(stripped) 
    except Exception: 
        pass 
    # Try extracting the first {...} block 
    try: 
        s = stripped if 'stripped' in locals() else raw 
        i = s.find("{") 
        j = s.rfind("}") 
        if i != -1 and j != -1 and j > i: 
            candidate = s[i+1] 
        return json.loads(candidate) 
    except Exception: 
        pass


    preview = (raw[:1000] + "...") if len(raw) > 1000 else raw
    logger.warning("Raw AI response (truncated) could not be parsed as JSON:\n%s", preview)
    raise ValueError("Failed to parse AI response as JSON.")


def _normalize_effects(effects: Dict[str, Any]) -> Dict[str, Any]: 
    allowed_motion = {"none", "kenburns-slow", "kenburns-normal"} 
    allowed_in = {"fade", "slide-up", "zoom-in"} 
    allowed_out = {"fade", "slide-left"} 
    allowed_intro = {"none", "underline", "sparkle"} 
    allowed_bg_overlay = {"none", "bokeh-soft", "grid"}

    eff = effects or {}
    m = eff.get("motion", "kenburns-slow")
    ti = eff.get("transition_in", "fade")
    to = eff.get("transition_out", "fade")
    ie = eff.get("intro_emphasis", "none")
    bo = eff.get("bg_overlay", "none")
    if m not in allowed_motion: m = "kenburns-slow"
    if ti not in allowed_in: ti = "fade"
    if to not in allowed_out: to = "fade"
    if ie not in allowed_intro: ie = "none"
    if bo not in allowed_bg_overlay: bo = "none"
    return {"motion": m, "transition_in": ti, "transition_out": to, "intro_emphasis": ie, "bg_overlay": bo}


def generate_slide_plan(pages: List[Dict[str, Any]], images: List[Dict[str, Any]]) -> Dict[str, Any]: 
    client = OpenAI() 
    prompt = build_prompt(pages, images) 
    logger.info("Requesting slide plan from GPT...")

    try:
        os.makedirs(config.temp_dir, exist_ok=True)
    except Exception:
        pass

    resp = client.chat.completions.create(
        model=config.openai_model,
        messages=[
            {
                "role": "system",
                "content": "You are a structured-output generator. Always return a single, valid JSON object with no markdown, no code fences, and no commentary."
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        response_format={"type": "json_object"},
    )

    content = resp.choices[0].message.content or ""
    try:
        with open(os.path.join(config.temp_dir, "last_gpt_response.txt"), "w", encoding="utf-8") as f:
            f.write(content)
    except Exception:
        pass

    try:
        plan = _safe_parse_json(content)
        if not isinstance(plan, dict):
            raise ValueError("Top-level JSON is not an object.")
        assert "slides" in plan and isinstance(plan["slides"], list), "Missing 'slides' array in plan."

        # Normalize image_refs to ensure they exist, and sanitize additional fields
        valid_paths = set([im["path"] for im in images])
        for slide in plan["slides"]:
            # image_refs
            refs = [p for p in (slide.get("image_refs") or []) if p in valid_paths]
            slide["image_refs"] = refs

            # bullet_emojis alignment
            bullets = slide.get("bullets") or []
            be = slide.get("bullet_emojis") or []
            if len(be) != len(bullets):
                be = (be + [""] * len(bullets))[:len(bullets)]
            slide["bullet_emojis"] = be

            # title_emoji default
            te = slide.get("title_emoji")
            slide["title_emoji"] = te if isinstance(te, str) else ""

            # source_pages normalize
            sp = slide.get("source_pages") or []
            slide["source_pages"] = [int(x) for x in sp if isinstance(x, int) or (isinstance(x, str) and x.isdigit())]

            # visual_style defaults
            vs = slide.get("visual_style") or {}
            vs.setdefault("theme_color", "#0f172a")
            vs.setdefault("accent_color", "#38bdf8")
            vs.setdefault("layout", "title-bullets-left")
            vs.setdefault("bg_style", "solid")
            vs.setdefault("emphasis_words", [])
            effects = _normalize_effects((vs.get("effects") or {}))
            vs["effects"] = effects
            slide["visual_style"] = vs

        logger.info(f"Received {len(plan['slides'])} slides from AI")
        return plan
    except Exception as e:
        logger.error(f"Failed to parse AI response: {e}")
        raise