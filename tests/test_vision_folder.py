import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from vision_folder import find_class_dirs, frames_dir_for, step_extract, step_classify


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
