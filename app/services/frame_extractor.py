import glob
import logging
import os
import subprocess

logger = logging.getLogger(__name__)


def extract_frames_from_video(
    video_path: str,
    output_dir: str,
    interval: int = 5,
) -> list[str] | None:
    """
    Extract one frame every `interval` seconds from a video using FFmpeg.
    Returns a sorted list of extracted frame paths, or None on failure.
    """
    os.makedirs(output_dir, exist_ok=True)
    output_pattern = os.path.join(output_dir, "frame_%04d.jpg")

    try:
        subprocess.run(
            [
                "ffmpeg", "-i", video_path,
                "-vf", f"fps=1/{interval}",
                "-q:v", "2",
                output_pattern,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return sorted(glob.glob(os.path.join(output_dir, "frame_*.jpg")))
    except Exception as e:
        logger.error("[FFmpeg Frame Error] %s", e)
        return None
