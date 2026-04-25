# Vision Folder Script Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create `scripts/vision_folder.py` — a CLI script that drives the full vision pipeline (extract frames → classify → ingest slides/notebooks/whiteboards) over a folder of class directories.

**Architecture:** Single script following the pattern of `scripts/transcribe_folder.py`. Discovers class directories (those containing a `video/` subfolder), then for each video runs the requested pipeline steps via the REST API using `api_client.api_request`. Steps are idempotent where local markers exist.

**Tech Stack:** Python 3.13, argparse, pathlib, `api_client.api_request`, `app.config.settings.VIDEO_EXTENSIONS`, pytest + unittest.mock.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `scripts/vision_folder.py` | Create | Full CLI + pipeline orchestration |
| `tests/test_vision_folder.py` | Create | Unit tests for all helpers and step functions |

> `pythonpath = [".", "scripts"]` is already set in `pyproject.toml` so tests can import `from vision_folder import ...` directly.

---

## Task 1: Discovery helpers

**Files:**
- Create: `scripts/vision_folder.py`
- Create: `tests/test_vision_folder.py`

- [ ] **Step 1: Write failing tests for `find_class_dirs` and `frames_dir_for`**

Create `tests/test_vision_folder.py`:

```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from vision_folder import find_class_dirs, frames_dir_for


def test_find_class_dirs_returns_dirs_with_video_subfolder(tmp_path):
    aula = tmp_path / "Aula_01"
    (aula / "video").mkdir(parents=True)
    (aula / "documentos").mkdir()

    result = find_class_dirs(tmp_path, recursive=False)

    assert result == [aula]


def test_find_class_dirs_ignores_dirs_without_video_subfolder(tmp_path):
    other = tmp_path / "random_dir"
    other.mkdir()

    result = find_class_dirs(tmp_path, recursive=False)

    assert result == []


def test_find_class_dirs_non_recursive_ignores_nested(tmp_path):
    nested = tmp_path / "course" / "Aula_01"
    (nested / "video").mkdir(parents=True)

    result = find_class_dirs(tmp_path, recursive=False)

    assert result == []


def test_find_class_dirs_recursive_finds_nested(tmp_path):
    nested = tmp_path / "course" / "Aula_01"
    (nested / "video").mkdir(parents=True)

    result = find_class_dirs(tmp_path, recursive=True)

    assert result == [nested]


def test_find_class_dirs_returns_sorted(tmp_path):
    for name in ["Aula_03", "Aula_01", "Aula_02"]:
        (tmp_path / name / "video").mkdir(parents=True)

    result = find_class_dirs(tmp_path, recursive=False)

    assert result == [
        tmp_path / "Aula_01",
        tmp_path / "Aula_02",
        tmp_path / "Aula_03",
    ]


def test_frames_dir_for_follows_convention(tmp_path):
    # video at <class_dir>/video/Aula_09.mp4
    # frames_dir → <class_dir>/ai_data/Aula_09_frames
    class_dir = tmp_path / "Aula_09_Topic"
    video = class_dir / "video" / "Aula_09.mp4"

    result = frames_dir_for(video)

    assert result == class_dir / "ai_data" / "Aula_09_frames"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /d/Projects/Assistente-Estudos && python -m pytest tests/test_vision_folder.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError: No module named 'vision_folder'`

- [ ] **Step 3: Implement `find_class_dirs` and `frames_dir_for`**

Create `scripts/vision_folder.py`:

```python
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
    candidates = root.rglob("*") if recursive else root.iterdir()
    return sorted(
        p for p in candidates
        if p.is_dir() and (p / "video").is_dir()
    )


def frames_dir_for(video_path: Path) -> Path:
    class_dir = video_path.parent.parent
    return class_dir / "ai_data" / f"{video_path.stem}_frames"
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd /d/Projects/Assistente-Estudos && python -m pytest tests/test_vision_folder.py -v
```

Expected: 6 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add scripts/vision_folder.py tests/test_vision_folder.py
git commit -m "feat: add vision_folder helpers — find_class_dirs, frames_dir_for"
```

---

## Task 2: Extract and classify step functions

**Files:**
- Modify: `scripts/vision_folder.py`
- Modify: `tests/test_vision_folder.py`

- [ ] **Step 1: Write failing tests for `step_extract` and `step_classify`**

Append to `tests/test_vision_folder.py`:

```python
from unittest.mock import patch

from vision_folder import step_extract, step_classify


def test_step_extract_skips_when_frames_exist(tmp_path):
    frames_dir = tmp_path / "Aula_01_frames"
    frames_dir.mkdir()
    (frames_dir / "frame_0001.jpg").touch()

    with patch("vision_folder.api_request") as mock_api:
        result = step_extract(tmp_path / "video" / "Aula_01.mp4", frames_dir, interval=5, dry_run=False)

    mock_api.assert_not_called()
    assert result is True


def test_step_extract_calls_api_when_frames_missing(tmp_path):
    frames_dir = tmp_path / "Aula_01_frames"
    video = tmp_path / "video" / "Aula_01.mp4"

    with patch("vision_folder.api_request", return_value={"frame_count": 100}) as mock_api:
        result = step_extract(video, frames_dir, interval=5, dry_run=False)

    mock_api.assert_called_once_with(
        "POST", "/extract-frames",
        {"file_path": str(video), "interval": 5}
    )
    assert result is True


def test_step_extract_returns_false_on_api_error(tmp_path):
    frames_dir = tmp_path / "Aula_01_frames"
    video = tmp_path / "video" / "Aula_01.mp4"

    with patch("vision_folder.api_request", side_effect=RuntimeError("connection refused")):
        result = step_extract(video, frames_dir, interval=5, dry_run=False)

    assert result is False


def test_step_extract_dry_run_does_not_call_api(tmp_path):
    frames_dir = tmp_path / "Aula_01_frames"
    video = tmp_path / "video" / "Aula_01.mp4"

    with patch("vision_folder.api_request") as mock_api:
        result = step_extract(video, frames_dir, interval=5, dry_run=True)

    mock_api.assert_not_called()
    assert result is True


def test_step_classify_skips_when_classifications_exist(tmp_path):
    frames_dir = tmp_path / "Aula_01_frames"
    frames_dir.mkdir()
    (frames_dir / "classifications.json").touch()

    with patch("vision_folder.api_request") as mock_api:
        result = step_classify(frames_dir, dry_run=False)

    mock_api.assert_not_called()
    assert result is True


def test_step_classify_calls_api_when_classifications_missing(tmp_path):
    frames_dir = tmp_path / "Aula_01_frames"
    frames_dir.mkdir()

    with patch("vision_folder.api_request", return_value={"counts": {"slide": 10}}) as mock_api:
        result = step_classify(frames_dir, dry_run=False)

    mock_api.assert_called_once_with(
        "POST", "/classify-frames",
        {"frames_dir": str(frames_dir)}
    )
    assert result is True


def test_step_classify_returns_false_on_api_error(tmp_path):
    frames_dir = tmp_path / "Aula_01_frames"
    frames_dir.mkdir()

    with patch("vision_folder.api_request", side_effect=RuntimeError("timeout")):
        result = step_classify(frames_dir, dry_run=False)

    assert result is False


def test_step_classify_dry_run_does_not_call_api(tmp_path):
    frames_dir = tmp_path / "Aula_01_frames"
    frames_dir.mkdir()

    with patch("vision_folder.api_request") as mock_api:
        result = step_classify(frames_dir, dry_run=True)

    mock_api.assert_not_called()
    assert result is True
```

- [ ] **Step 2: Run to confirm they fail**

```bash
cd /d/Projects/Assistente-Estudos && python -m pytest tests/test_vision_folder.py::test_step_extract_skips_when_frames_exist -v 2>&1 | head -10
```

Expected: `ImportError: cannot import name 'step_extract'`

- [ ] **Step 3: Implement `step_extract` and `step_classify`**

Append to `scripts/vision_folder.py`:

```python

def step_extract(video_path: Path, frames_dir: Path, interval: int, dry_run: bool) -> bool:
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
```

- [ ] **Step 4: Run all tests**

```bash
cd /d/Projects/Assistente-Estudos && python -m pytest tests/test_vision_folder.py -v
```

Expected: 14 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add scripts/vision_folder.py tests/test_vision_folder.py
git commit -m "feat: add step_extract and step_classify to vision_folder"
```

---

## Task 3: Slides, notebooks, and whiteboards step functions

**Files:**
- Modify: `scripts/vision_folder.py`
- Modify: `tests/test_vision_folder.py`

- [ ] **Step 1: Write failing tests for `step_slides`, `step_notebooks`, `step_whiteboards`**

Append to `tests/test_vision_folder.py`:

```python
from vision_folder import step_slides, step_notebooks, step_whiteboards


def test_step_slides_calls_api_for_each_pptx(tmp_path):
    video = tmp_path / "video" / "Aula_01.mp4"
    frames_dir = tmp_path / "ai_data" / "Aula_01_frames"
    pptx_files = [tmp_path / "documentos" / "slides.pptx"]

    with patch("vision_folder.api_request", return_value={"ingested": 5}) as mock_api:
        total = step_slides(video, frames_dir, pptx_files, interval=5, dry_run=False)

    mock_api.assert_called_once_with(
        "POST", "/ingest/slides",
        {"pptx_path": str(pptx_files[0]), "video_path": str(video), "frames_dir": str(frames_dir), "interval": 5}
    )
    assert total == 5


def test_step_slides_returns_zero_when_no_pptx(tmp_path):
    video = tmp_path / "video" / "Aula_01.mp4"
    frames_dir = tmp_path / "ai_data" / "Aula_01_frames"

    with patch("vision_folder.api_request") as mock_api:
        total = step_slides(video, frames_dir, [], interval=5, dry_run=False)

    mock_api.assert_not_called()
    assert total == 0


def test_step_slides_dry_run_does_not_call_api(tmp_path):
    video = tmp_path / "video" / "Aula_01.mp4"
    frames_dir = tmp_path / "ai_data" / "Aula_01_frames"
    pptx_files = [tmp_path / "documentos" / "slides.pptx"]

    with patch("vision_folder.api_request") as mock_api:
        total = step_slides(video, frames_dir, pptx_files, interval=5, dry_run=True)

    mock_api.assert_not_called()
    assert total == 0


def test_step_notebooks_calls_api_for_each_ipynb(tmp_path):
    video = tmp_path / "video" / "Aula_01.mp4"
    frames_dir = tmp_path / "ai_data" / "Aula_01_frames"
    ipynb_files = [tmp_path / "scripts" / "notebook.ipynb"]

    with patch("vision_folder.api_request", return_value={"ingested": 3}) as mock_api:
        total = step_notebooks(video, frames_dir, ipynb_files, interval=5, dry_run=False)

    mock_api.assert_called_once_with(
        "POST", "/ingest/notebook",
        {"ipynb_path": str(ipynb_files[0]), "video_path": str(video), "frames_dir": str(frames_dir), "interval": 5}
    )
    assert total == 3


def test_step_notebooks_returns_zero_when_no_ipynb(tmp_path):
    video = tmp_path / "video" / "Aula_01.mp4"
    frames_dir = tmp_path / "ai_data" / "Aula_01_frames"

    with patch("vision_folder.api_request") as mock_api:
        total = step_notebooks(video, frames_dir, [], interval=5, dry_run=False)

    mock_api.assert_not_called()
    assert total == 0


def test_step_whiteboards_calls_api(tmp_path):
    video = tmp_path / "video" / "Aula_01.mp4"
    frames_dir = tmp_path / "ai_data" / "Aula_01_frames"

    with patch("vision_folder.api_request", return_value={"ingested": 2}) as mock_api:
        total = step_whiteboards(video, frames_dir, interval=5, dry_run=False)

    mock_api.assert_called_once_with(
        "POST", "/ingest/whiteboard",
        {"video_path": str(video), "frames_dir": str(frames_dir), "interval": 5}
    )
    assert total == 2


def test_step_whiteboards_dry_run_does_not_call_api(tmp_path):
    video = tmp_path / "video" / "Aula_01.mp4"
    frames_dir = tmp_path / "ai_data" / "Aula_01_frames"

    with patch("vision_folder.api_request") as mock_api:
        total = step_whiteboards(video, frames_dir, interval=5, dry_run=True)

    mock_api.assert_not_called()
    assert total == 0
```

- [ ] **Step 2: Run to confirm they fail**

```bash
cd /d/Projects/Assistente-Estudos && python -m pytest tests/test_vision_folder.py::test_step_slides_calls_api_for_each_pptx -v 2>&1 | head -10
```

Expected: `ImportError: cannot import name 'step_slides'`

- [ ] **Step 3: Implement `step_slides`, `step_notebooks`, `step_whiteboards`**

Append to `scripts/vision_folder.py`:

```python

def step_slides(video_path: Path, frames_dir: Path, pptx_files: list[Path], interval: int, dry_run: bool) -> int:
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
```

- [ ] **Step 4: Run all tests**

```bash
cd /d/Projects/Assistente-Estudos && python -m pytest tests/test_vision_folder.py -v
```

Expected: 21 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add scripts/vision_folder.py tests/test_vision_folder.py
git commit -m "feat: add step_slides, step_notebooks, step_whiteboards to vision_folder"
```

---

## Task 4: `process_video` orchestrator and `main()` CLI

**Files:**
- Modify: `scripts/vision_folder.py`
- Modify: `tests/test_vision_folder.py`

- [ ] **Step 1: Write failing tests for `process_video`**

Append to `tests/test_vision_folder.py`:

```python
from vision_folder import process_video


def test_process_video_skips_classify_if_extract_fails(tmp_path):
    video = tmp_path / "video" / "Aula_01.mp4"
    frames_dir = tmp_path / "ai_data" / "Aula_01_frames"
    stats = {"extracted": 0, "classified": 0, "slides": 0, "notebooks": 0, "whiteboards": 0, "failed": 0}

    with patch("vision_folder.step_extract", return_value=False) as mock_extract, \
         patch("vision_folder.step_classify") as mock_classify:
        process_video(video, frames_dir, [], [], ALL_STEPS, interval=5, dry_run=False, stats=stats)

    mock_extract.assert_called_once()
    mock_classify.assert_not_called()
    assert stats["failed"] == 1


def test_process_video_skips_ingestion_if_classify_fails(tmp_path):
    video = tmp_path / "video" / "Aula_01.mp4"
    frames_dir = tmp_path / "ai_data" / "Aula_01_frames"
    stats = {"extracted": 0, "classified": 0, "slides": 0, "notebooks": 0, "whiteboards": 0, "failed": 0}

    with patch("vision_folder.step_extract", return_value=True), \
         patch("vision_folder.step_classify", return_value=False), \
         patch("vision_folder.step_slides") as mock_slides, \
         patch("vision_folder.step_notebooks") as mock_notebooks, \
         patch("vision_folder.step_whiteboards") as mock_whiteboards:
        process_video(video, frames_dir, [], [], ALL_STEPS, interval=5, dry_run=False, stats=stats)

    mock_slides.assert_not_called()
    mock_notebooks.assert_not_called()
    mock_whiteboards.assert_not_called()
    assert stats["failed"] == 1


def test_process_video_runs_all_steps_on_success(tmp_path):
    video = tmp_path / "video" / "Aula_01.mp4"
    frames_dir = tmp_path / "ai_data" / "Aula_01_frames"
    pptx_files = [tmp_path / "documentos" / "slides.pptx"]
    ipynb_files = [tmp_path / "scripts" / "nb.ipynb"]
    stats = {"extracted": 0, "classified": 0, "slides": 0, "notebooks": 0, "whiteboards": 0, "failed": 0}

    with patch("vision_folder.step_extract", return_value=True), \
         patch("vision_folder.step_classify", return_value=True), \
         patch("vision_folder.step_slides", return_value=3), \
         patch("vision_folder.step_notebooks", return_value=2), \
         patch("vision_folder.step_whiteboards", return_value=1):
        process_video(video, frames_dir, pptx_files, ipynb_files, ALL_STEPS, interval=5, dry_run=False, stats=stats)

    assert stats["extracted"] == 1
    assert stats["classified"] == 1
    assert stats["slides"] == 3
    assert stats["notebooks"] == 2
    assert stats["whiteboards"] == 1
    assert stats["failed"] == 0


def test_process_video_respects_steps_filter(tmp_path):
    video = tmp_path / "video" / "Aula_01.mp4"
    frames_dir = tmp_path / "ai_data" / "Aula_01_frames"
    stats = {"extracted": 0, "classified": 0, "slides": 0, "notebooks": 0, "whiteboards": 0, "failed": 0}

    with patch("vision_folder.step_extract", return_value=True) as mock_extract, \
         patch("vision_folder.step_classify") as mock_classify:
        process_video(video, frames_dir, [], [], ["extract"], interval=5, dry_run=False, stats=stats)

    mock_extract.assert_called_once()
    mock_classify.assert_not_called()
```

- [ ] **Step 2: Run to confirm they fail**

```bash
cd /d/Projects/Assistente-Estudos && python -m pytest tests/test_vision_folder.py::test_process_video_skips_classify_if_extract_fails -v 2>&1 | head -10
```

Expected: `ImportError: cannot import name 'process_video'`

- [ ] **Step 3: Implement `process_video` and `main()`**

Append to `scripts/vision_folder.py`:

```python

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
```

- [ ] **Step 4: Run all tests**

```bash
cd /d/Projects/Assistente-Estudos && python -m pytest tests/test_vision_folder.py -v
```

Expected: 25 tests PASSED

- [ ] **Step 5: Smoke-test the CLI dry-run**

```bash
python scripts/vision_folder.py Downloads/ --dry-run --recursive
```

Expected: prints discovered class dirs and `[dry-run]` lines for each step, no API calls made.

- [ ] **Step 6: Commit**

```bash
git add scripts/vision_folder.py tests/test_vision_folder.py
git commit -m "feat: complete vision_folder script with process_video and main CLI"
```
