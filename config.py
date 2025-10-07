import os 
from pydantic import BaseModel

class AppConfig(BaseModel): 
    
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "") 
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    elevenlabs_api_key: str = os.getenv("ELEVENLABS_API_KEY", "")
    elevenlabs_voice_id: str = os.getenv("ELEVENLABS_VOICE_ID", "")

    slide_width: int = 1920
    slide_height: int = 1080
    fps: int = 30
    video_bitrate: str = "6000k"
    audio_bitrate: str = "192k"
    crossfade_sec: float = 0.5

    # Visual/animation flags
    enable_animation: bool = True
    enable_emojis: bool = True
    enable_music: bool = False
    music_volume: float = 0.15
    effect_profile: str = "subtle"  # "minimal" | "subtle" | "lively"
    bullet_reveal: str = "fade-slide"  # "fade" | "slide" | "fade-slide"
    kenburns_zoom_min: float = 1.03
    kenburns_zoom_max: float = 1.08

    # Assets
    bg_music_path: str = ""  # optional music bed path
    emoji_pack_dir: str = os.getenv("EMOJI_PACK_DIR", os.path.join("assets", "emoji_twemoji"))

    # Temp/output
    temp_dir: str = "project_runtime"

config = AppConfig()