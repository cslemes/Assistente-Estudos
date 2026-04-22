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


def step_slides(video_path: Path, frames_dir: Path, pptx_files: list[Path], interval: int, dry_run: bool) -> int:
    """Ingest slides from PowerPoint files matched against video frames.

    Args:
        video_path: Path to video file
        frames_dir: Path to frames directory
        pptx_files: List of PowerPoint files to ingest
        interval: Interval in seconds between frames
        dry_run: If True, only print what would be done

    Returns:
        Total number of chunks ingested
    """
    if not pptx_files:
        return 0
    total = 0
    for pptx in pptx_files:
        if dry_run:
            print(f"    [dry-run] slides  → POST /ingest/slides ({pptx.name})", flush=True)
            continue
        try:
            result = api_request("POST", "/ingest/slides", {
                "pptx_path": str(pptx),
                "video_path": str(video_path),
                "frames_dir": str(frames_dir),
                "interval": interval,
            })
            n = result.get("ingested", 0)
            total += n
            print(f"    slides   → {n} chunks ({pptx.name})", flush=True)
        except RuntimeError as exc:
            print(f"    slides   → ERROR ({pptx.name}): {exc}", flush=True)
    return total


def step_notebooks(video_path: Path, frames_dir: Path, ipynb_files: list[Path], interval: int, dry_run: bool) -> int:
    """Ingest notebook cells matched against video frames.

    Args:
        video_path: Path to video file
        frames_dir: Path to frames directory
        ipynb_files: List of Jupyter notebook files to ingest
        interval: Interval in seconds between frames
        dry_run: If True, only print what would be done

    Returns:
        Total number of chunks ingested
    """
    if not ipynb_files:
        return 0
    total = 0
    for ipynb in ipynb_files:
        if dry_run:
            print(f"    [dry-run] notebooks → POST /ingest/notebook ({ipynb.name})", flush=True)
            continue
        try:
            result = api_request("POST", "/ingest/notebook", {
                "ipynb_path": str(ipynb),
                "video_path": str(video_path),
                "frames_dir": str(frames_dir),
                "interval": interval,
            })
            n = result.get("ingested", 0)
            total += n
            print(f"    notebooks→ {n} chunks ({ipynb.name})", flush=True)
        except RuntimeError as exc:
            print(f"    notebooks→ ERROR ({ipynb.name}): {exc}", flush=True)
    return total


def step_whiteboards(video_path: Path, frames_dir: Path, interval: int, dry_run: bool) -> int:
    """Extract and ingest whiteboard content from video frames.

    Args:
        video_path: Path to video file
        frames_dir: Path to frames directory
        interval: Interval in seconds between frames
        dry_run: If True, only print what would be done

    Returns:
        Number of chunks ingested
    """
    if dry_run:
        print(f"    [dry-run] whiteboards → POST /ingest/whiteboard", flush=True)
        return 0
    try:
        result = api_request("POST", "/ingest/whiteboard", {
            "video_path": str(video_path),
            "frames_dir": str(frames_dir),
            "interval": interval,
        })
        n = result.get("ingested", 0)
        print(f"    whiteboards → {n} chunks", flush=True)
        return n
    except RuntimeError as exc:
        print(f"    whiteboards → ERROR: {exc}", flush=True)
        return 0


def process_video(
    video_path: Path,
    frames_dir: Path,
    pptx_files: list[Path],
    ipynb_files: list[Path],
    steps: list[str],
    interval: int,
    dry_run: bool,
    stats: dict,
) -> None:
    """Process a single video through the vision pipeline.

    Orchestrates the extraction, classification, and ingestion steps.
    If extract or classify fail, stops early to avoid downstream errors.

    Args:
        video_path: Path to video file
        frames_dir: Path to frames directory
        pptx_files: List of PowerPoint files to ingest
        ipynb_files: List of Jupyter notebook files to ingest
        steps: List of steps to run (subset of ALL_STEPS)
        interval: Interval in seconds between frames
        dry_run: If True, only print what would be done
        stats: Dict to accumulate statistics
    """
    if "extract" in steps:
        ok = step_extract(video_path, frames_dir, interval, dry_run)
        if ok:
            stats["extracted"] += 1
        else:
            stats["failed"] += 1
            return

    if "classify" in steps:
        ok = step_classify(frames_dir, dry_run)
        if ok:
            stats["classified"] += 1
        else:
            stats["failed"] += 1
            return

    if "slides" in steps:
        stats["slides"] += step_slides(video_path, frames_dir, pptx_files, interval, dry_run)

    if "notebooks" in steps:
        stats["notebooks"] += step_notebooks(video_path, frames_dir, ipynb_files, interval, dry_run)

    if "whiteboards" in steps:
        stats["whiteboards"] += step_whiteboards(video_path, frames_dir, interval, dry_run)


def main() -> None:
    """CLI entry point for vision_folder script."""
    parser = argparse.ArgumentParser(
        description="Run the vision pipeline (extract → classify → ingest) over a folder of class directories."
    )
    parser.add_argument("root_folder", type=Path, help="Root folder to scan for class directories")
    parser.add_argument(
        "--steps",
        default=",".join(ALL_STEPS),
        help=f"Comma-separated steps to run (default: all). Choices: {', '.join(ALL_STEPS)}",
    )
    parser.add_argument("--interval", type=int, default=5, help="Frame extraction interval in seconds (default: 5)")
    parser.add_argument("--recursive", action="store_true", help="Scan subdirectories for class dirs")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without executing")
    args = parser.parse_args()

    root = args.root_folder.resolve()
    if not root.is_dir():
        parser.error(f"Not a directory: {root}")

    steps = [s.strip() for s in args.steps.split(",")]
    invalid = [s for s in steps if s not in ALL_STEPS]
    if invalid:
        parser.error(f"Unknown step(s): {', '.join(invalid)}. Choices: {', '.join(ALL_STEPS)}")

    class_dirs = find_class_dirs(root, args.recursive)
    if not class_dirs:
        print(f"No class directories found in {root}")
        return

    print(f"Found {len(class_dirs)} class dir(s) in {root}\n")

    stats = {"extracted": 0, "classified": 0, "slides": 0, "notebooks": 0, "whiteboards": 0, "failed": 0}

    for class_dir in class_dirs:
        video_dir = class_dir / "video"
        docs_dir = class_dir / "documentos"
        scripts_dir = class_dir / "scripts"

        videos = sorted(
            p for p in video_dir.iterdir()
            if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
        )
        pptx_files = sorted(docs_dir.glob("*.pptx")) if docs_dir.is_dir() else []
        ipynb_files = sorted(scripts_dir.glob("*.ipynb")) if scripts_dir.is_dir() else []

        if not videos:
            print(f"[{class_dir.name}] no videos found, skipping\n")
            continue

        for video in videos:
            frames_dir = frames_dir_for(video)
            print(f"[{class_dir.name}] {video.relative_to(class_dir)}")
            process_video(video, frames_dir, pptx_files, ipynb_files, steps, args.interval, args.dry_run, stats)

        print()

    print(
        f"Done: {stats['extracted']} extracted, {stats['classified']} classified, "
        f"{stats['slides']} slides ingested, {stats['notebooks']} notebooks ingested, "
        f"{stats['whiteboards']} whiteboards ingested, {stats['failed']} failed."
    )


if __name__ == "__main__":
    main()
