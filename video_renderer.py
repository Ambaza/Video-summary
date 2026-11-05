# File: video_renderer.py
import os
from typing import List, Dict, Any
from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    concatenate_videoclips,
    CompositeAudioClip,
)
from logger_setup import get_logger
from config import config

logger = get_logger("video")


def _assemble_static(slides: List[Dict[str, Any]], slides_dir: str, audio_dir: str):
    """
    Assemble static slides into video clips.
    Each image (slide) is paired with its corresponding audio file.
    """
    clips = []

    for i, _ in enumerate(slides, start=1):
        # Fix: use underscore in filename to match render output
        img_path = os.path.join(slides_dir, f"slide_{i:02d}.png")
        audio_path = os.path.join(audio_dir, f"slide_{i:02d}.mp3")

        if not os.path.exists(img_path):
            logger.warning(f"Missing image: {img_path}")
            continue

        if not os.path.exists(audio_path):
            logger.warning(f"Missing audio: {audio_path}")
            continue

        try:
            audio = AudioFileClip(audio_path)
            img_clip = ImageClip(img_path).set_duration(audio.duration).set_audio(audio)
            if i > 1:
                img_clip = img_clip.crossfadein(config.crossfade_sec)
            clips.append(img_clip)
        except Exception as e:
            logger.error(f"Failed to create clip for slide {i}: {e}", exc_info=True)

    return clips


def _assemble_animated(slides: List[Dict[str, Any]], audio_dir: str):
    """
    Assemble animated motion slides if motion_renderer is available.
    Falls back to static assembly if unavailable.
    """
    try:
        from motion_renderer import render_motion_clip
    except Exception as e:
        logger.warning(f"motion_renderer unavailable ({e}); falling back to static mode")
        return None

    clips = []
    for i, slide in enumerate(slides, start=1):
        audio_path = os.path.join(audio_dir, f"slide_{i:02d}.mp3")
        try:
            clip = render_motion_clip(slide, audio_path)
            if i > 1:
                clip = clip.crossfadein(config.crossfade_sec)
            clips.append(clip)
        except Exception as e:
            logger.error(f"Failed to render animated clip for slide {i}: {e}", exc_info=True)

    return clips


def _add_music(final_clip):
    """
    Add background music track to the final video (if enabled and path exists).
    """
    if not getattr(config, "enable_music", False):
        return final_clip

    try:
        if not (config.bg_music_path and os.path.exists(config.bg_music_path)):
            logger.warning("Background music path not set or not found; skipping music bed.")
            return final_clip

        music = AudioFileClip(config.bg_music_path).volumex(config.music_volume)
        music = music.audio_loop(duration=final_clip.duration)

        # Mix voice audio + background music
        mixed_audio = CompositeAudioClip([
            final_clip.audio.volumex(1.0),
            music
        ])

        return final_clip.set_audio(mixed_audio)

    except Exception as e:
        logger.warning(f"Failed to add background music: {e}", exc_info=True)
        return final_clip


def assemble_video(slides: List[Dict[str, Any]], slides_dir: str, audio_dir: str, out_path: str):
    """
    Assemble a full video from slide images, audio narration, and optional background music.
    Supports both static and animated rendering modes.
    """
    if getattr(config, "enable_animation", False):
        clips = _assemble_animated(slides, audio_dir)
        if clips is None or len(clips) == 0:
            logger.info("Falling back to static slide assembly.")
            clips = _assemble_static(slides, slides_dir, audio_dir)
    else:
        clips = _assemble_static(slides, slides_dir, audio_dir)

    if not clips:
        logger.error("No clips were generated. Aborting video assembly.")
        return

    # Combine all clips with smooth transitions
    try:
        final = concatenate_videoclips(clips, method="compose", padding=-config.crossfade_sec)
    except Exception as e:
        logger.error(f"Failed to concatenate clips: {e}", exc_info=True)
        return

    # Add background music if enabled
    final = _add_music(final)

    # Ensure output directory exists
    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    try:
        final.write_videofile(
            out_path,
            fps=config.fps,
            codec="libx264",
            bitrate=config.video_bitrate,
            audio_codec="aac",
            audio_bitrate=config.audio_bitrate,
            threads=4,
            preset="medium",
        )
        logger.info(f"Video successfully written: {out_path}")
    except Exception as e:
        logger.error(f"Error writing video to file: {e}", exc_info=True)
