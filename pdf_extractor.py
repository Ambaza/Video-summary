import fitz  # PyMuPDF
import os
from typing import Dict, Any
from logger_setup import get_logger

logger = get_logger("pdf")

def extract_pdf(pdf_path: str, out_dir: str) -> Dict[str, Any]:
    os.makedirs(out_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    pages = []
    images_meta = []
    for pno in range(len(doc)):
        page = doc[pno]
        blocks = sorted(page.get_text("blocks"), key=lambda b: (b[1], b[0]))
        page_text = "\n".join([b[4] for b in blocks if isinstance(b[4], str)])
        for img_index, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            pix = fitz.Pixmap(doc, xref)
            if pix.alpha:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            img_name = f"page{pno+1}_img{img_index+1}.png"
            img_path = os.path.join(out_dir, img_name)
            pix.save(img_path)
            images_meta.append({"page": pno+1, "path": img_path, "width": pix.width, "height": pix.height})
        pages.append({"page_number": pno+1, "text": page_text})
    doc.close()
    logger.info(f"Extracted {len(pages)} pages, {len(images_meta)} images")
    return {"pages": pages, "images": images_meta}