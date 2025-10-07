import os
from typing import List, Dict, Any
from pptx import Presentation
from logger_setup import get_logger

logger = get_logger("pptx")

def build_pptx(slides: List[Dict[str, Any]], out_path: str, template_path: str = None):
    prs = Presentation(template_path) if template_path and os.path.exists(template_path) else Presentation()
    for slide_spec in slides:
        layout = prs.slide_layouts[1] if len(prs.slide_layouts) > 1 else prs.slide_layouts[0]
        slide = prs.slides.add_slide(layout)
        title_shape = slide.shapes.title
        body_shape = slide.shapes.placeholders[1] if len(slide.shapes.placeholders) > 1 else None
        if title_shape:
            title_shape.text = slide_spec.get("title", "")
        if body_shape:
            tf = body_shape.text_frame
            tf.clear()
            for i, b in enumerate(slide_spec.get("bullets", [])):
                p = tf.add_paragraph() if i > 0 else tf.paragraphs[0]
                p.text = b
                p.level = 0
    prs.save(out_path)
    logger.info(f"PPTX written: {out_path}")

def export_pptx_to_mp4_via_com(pptx_path: str, out_mp4: str):
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