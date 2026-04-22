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
