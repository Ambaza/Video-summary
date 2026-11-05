import os
import requests
from logger_setup import get_logger

logger = get_logger("tts")
ELEVEN_BASE = "https://api.elevenlabs.io/v1"

def synthesize_to_file(
    text: str,
    out_path: str,
    voice_id: str = None,
    model_id: str = "eleven_multilingual_v2",
    stability: float = 0.5,
    similarity_boost: float = 0.75,
):
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY is not set. Provide it in environment or GUI.")
    voice = voice_id or os.getenv("ELEVENLABS_VOICE_ID")
    if not voice:
        raise ValueError("ELEVENLABS_VOICE_ID is not set. Provide it in environment or GUI.")

    headers = {
        "xi-api-key": api_key,
        "accept": "audio/mpeg",
        "content-type": "application/json",
    }
    body = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {"stability": stability, "similarity_boost": similarity_boost},
    }
    url = f"{ELEVEN_BASE}/text-to-speech/{voice}"
    r = requests.post(url, headers=headers, json=body, timeout=120)
    r.raise_for_status()
    with open(out_path, "wb") as f:
        f.write(r.content)
    logger.info(f"TTS written: {out_path}")