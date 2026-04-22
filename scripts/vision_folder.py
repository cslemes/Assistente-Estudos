"""
Usage:
    python scripts/vision_folder.py <root_folder>
    python scripts/vision_folder.py <root_folder> --recursive
    python scripts/vision_folder.py <root_folder> --steps extract,classify
    python scripts/vision_folder.py <root_folder> --dry-run
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api_client import api_request
from app.config.settings import VIDEO_EXTENSIONS

ALL_STEPS = ["extract", "classify", "slides", "notebooks", "whiteboards"]


def find_class_dirs(root: Path, recursive: bool) -> list[Path]:
    """Find directories containing a 'video' subdirectory.

    Args:
        root: Root directory to search
        recursive: If True, search recursively; if False, only search direct children

    Returns:
        Sorted list of Path objects representing class directories
    """
    candidates = root.rglob("*") if recursive else root.iterdir()
    return sorted(
        p for p in candidates
        if p.is_dir() and (p / "video").is_dir()
    )


def frames_dir_for(video_path: Path) -> Path:
    """Get the frames directory for a video file.

    Convention:
        Video at: <class_dir>/video/Aula_09.mp4
        Frames dir: <class_dir>/ai_data/Aula_09_frames

    Args:
        video_path: Path to video file

    Returns:
        Path to the frames directory
    """
    class_dir = video_path.parent.parent
    return class_dir / "ai_data" / f"{video_path.stem}_frames"


def step_extract(video_path: Path, frames_dir: Path, interval: int, dry_run: bool) -> bool:
    """Extract frames from a video file.

    Args:
        video_path: Path to video file
        frames_dir: Path to output frames directory
        interval: Interval in seconds between frames
        dry_run: If True, only print what would be done

    Returns:
        True on success, False on error
    """
    if frames_dir.exists() and any(frames_dir.iterdir()):
        print(f"    extract  → skipped (frames exist)", flush=True)
        return True
    if dry_run:
        print(f"    [dry-run] extract → POST /extract-frames", flush=True)
        return True
    try:
        result = api_request("POST", "/extract-frames", {"file_path": str(video_path), "interval": interval})
        print(f"    extract  → {result.get('frame_count', '?')} frames", flush=True)
        return True
    except RuntimeError as exc:
        print(f"    extract  → ERROR: {exc}", flush=True)
        return False


def step_classify(frames_dir: Path, dry_run: bool) -> bool:
    """Classify frames using CLIP model.

    Args:
        frames_dir: Path to frames directory
        dry_run: If True, only print what would be done

    Returns:
        True on success, False on error
    """
    if (frames_dir / "classifications.json").exists():
        print(f"    classify → skipped (classifications.json exists)", flush=True)
        return True
    if dry_run:
        print(f"    [dry-run] classify → POST /classify-frames", flush=True)
        return True
    try:
        result = api_request("POST", "/classify-frames", {"frames_dir": str(frames_dir)})
        counts = result.get("counts", {})
        counts_str = " ".join(f"{k}:{v}" for k, v in counts.items())
        print(f"    classify → {counts_str}", flush=True)
        return True
    except RuntimeError as exc:
        print(f"    classify → ERROR: {exc}", flush=True)
        return False
