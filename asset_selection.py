import os
from typing import List, Dict, Any


def choose_images_for_slide(slide: Dict[str, Any], images_meta: List[Dict[str, Any]]) -> List[str]:
    """
    Select 0–2 images logically for a given slide.

    Rules:
    - Prefer images whose 'page' is in slide['source_pages'].
    - If none, return an empty list.
    - If multiple matches, pick by largest area.
    - Cap count: 1 (or 2 if layout == 'split').
    """
    source_pages = slide.get("source_pages") or []
    layout = (slide.get("visual_style") or {}).get("layout", "title-bullets-left")
    cap = 2 if layout == "split" else 1

    candidates = []
    for im in images_meta:
        if source_pages and im.get("page") not in source_pages:
            continue
        if not os.path.exists(im["path"]):
            continue
        area = (im.get("width") or 0) * (im.get("height") or 0)
        candidates.append((area, im["path"]))

    candidates.sort(key=lambda x: x[0], reverse=True)
    chosen = [p for _, p in candidates[:cap]]
    return chosen
