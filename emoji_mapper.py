import re
from typing import Dict, Any, List, Tuple

TITLE_EMOJI_MAP: List[Tuple[str, str]] = [
    ("goal|objective|aim|target|vision|strategy", "🎯"),
    ("plan|roadmap|timeline|milestone", "🗺️"),
    ("result|impact|outcome|win|success", "🏁"),
    ("overview|summary|intro|introduction", "🧭"),
    ("improve|optimize|enhance|growth|scale", "📈"),
    ("security|risk|trust|safety", "🛡️"),
    ("idea|insight|learn|lesson|concept", "💡"),
    ("speed|time|deadline|delay|faster", "⏱️"),
    ("launch|rollout|deploy|start", "🚀"),
]

BULLET_EMOJI_MAP: List[Tuple[str, str]] = [
    ("benefit|value|advantage|positive|pro", "✅"),
    ("metric|kpi|growth|increase|trend|chart", "📈"),
    ("tool|process|method|framework|system", "⚙️"),
    ("insight|idea|tip|note|key", "💡"),
    ("risk|issue|problem|gap", "⚠️"),
    ("checklist|steps|task|action", "📝"),
    ("measure|analyze|data|evidence", "🔍"),
    ("secure|privacy|safety|trust", "🛡️"),
]


def _pick_from_map(text: str, mapping: List[Tuple[str, str]]) -> str:
    """Return the first matching emoji from a regex mapping."""
    low = (text or "").lower()
    for pattern, emoji in mapping:
        if re.search(pattern, low):
            return emoji
    return ""


def suggest_emojis_for_slide(slide: Dict[str, Any]) -> Dict[str, Any]:
    """Suggest appropriate emojis for slide title and bullets."""
    title = slide.get("title", "")
    bullets = slide.get("bullets", [])
    be = slide.get("bullet_emojis", [""] * len(bullets))

    # Title emoji if missing
    if not (slide.get("title_emoji") or "").strip():
        slide["title_emoji"] = _pick_from_map(title, TITLE_EMOJI_MAP)

    # Bullet emojis (avoid repeating same emoji more than twice)
    used = []
    for i, b in enumerate(bullets):
        if i < len(be) and be[i]:
            continue
        e = _pick_from_map(b, BULLET_EMOJI_MAP)
        if e and used.count(e) >= 2:
            e = ""
        be[i] = e
        if e:
            used.append(e)

    slide["bullet_emojis"] = be[:len(bullets)]
    return slide
