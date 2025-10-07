from pptx import Presentation

def extract_theme_colors(pptx_path: str): 
    prs = Presentation(pptx_path) 
    colors = {"bg_color": "#0f172a", "fg_color": "#e5e7eb", "accent_color": "#38bdf8"} 
    try: 
        # Placeholder: advanced parsing can be added later. 
        _ = prs.slide_master.theme.theme_color_scheme 
    except Exception: 
        pass 
    return colors