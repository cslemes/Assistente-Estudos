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
