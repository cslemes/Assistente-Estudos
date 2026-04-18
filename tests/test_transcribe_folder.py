from pathlib import Path
from transcribe_folder import find_videos, extract_audio
from unittest.mock import patch
import subprocess


def test_find_videos_returns_only_video_files(tmp_path):
    (tmp_path / "aula01.mp4").touch()
    (tmp_path / "aula01.txt").touch()
    (tmp_path / "notes.pdf").touch()

    result = find_videos(tmp_path, recursive=False)

    assert result == [tmp_path / "aula01.mp4"]


def test_find_videos_returns_empty_when_no_videos(tmp_path):
    (tmp_path / "notes.txt").touch()

    result = find_videos(tmp_path, recursive=False)

    assert result == []


def test_find_videos_returns_all_supported_extensions(tmp_path):
    for name in ["a.mp4", "b.mkv", "c.avi", "d.mov", "e.flv", "f.wmv"]:
        (tmp_path / name).touch()

    result = find_videos(tmp_path, recursive=False)

    assert len(result) == 6


def test_find_videos_is_case_insensitive(tmp_path):
    (tmp_path / "aula01.MP4").touch()
    (tmp_path / "aula02.Mkv").touch()

    result = find_videos(tmp_path, recursive=False)

    assert len(result) == 2


def test_find_videos_returns_sorted_list(tmp_path):
    (tmp_path / "c.mp4").touch()
    (tmp_path / "a.mp4").touch()
    (tmp_path / "b.mp4").touch()

    result = find_videos(tmp_path, recursive=False)

    assert result == [tmp_path / "a.mp4", tmp_path / "b.mp4", tmp_path / "c.mp4"]


def test_find_videos_non_recursive_ignores_subfolders(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "aula01.mp4").touch()

    result = find_videos(tmp_path, recursive=False)

    assert result == []


def test_find_videos_recursive_finds_in_subfolders(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "aula01.mp4").touch()

    result = find_videos(tmp_path, recursive=True)

    assert result == [sub / "aula01.mp4"]


def test_find_videos_skips_directories_named_with_video_extension(tmp_path):
    fake_dir = tmp_path / "fake.mp4"
    fake_dir.mkdir()

    result = find_videos(tmp_path, recursive=False)

    assert result == []


# --- extract_audio ---

def test_extract_audio_skips_ffmpeg_when_audio_exists(tmp_path):
    video = tmp_path / "video" / "aula01.mp4"
    video.parent.mkdir()
    video.touch()
    ai_data = tmp_path / "ai_data"
    ai_data.mkdir()
    existing_audio = ai_data / "aula01.mp3"
    existing_audio.touch()

    with patch("subprocess.run") as mock_run:
        result = extract_audio(video, ai_data)

    mock_run.assert_not_called()
    assert result == existing_audio


def test_extract_audio_calls_ffmpeg_and_returns_path(tmp_path):
    video = tmp_path / "video" / "aula01.mp4"
    video.parent.mkdir()
    video.touch()
    ai_data = tmp_path / "ai_data"
    expected_audio = ai_data / "aula01.mp3"

    def fake_ffmpeg(*args, **kwargs):
        expected_audio.touch()

    with patch("subprocess.run", side_effect=fake_ffmpeg) as mock_run:
        result = extract_audio(video, ai_data)

    mock_run.assert_called_once()
    assert result == expected_audio
    assert ai_data.is_dir()


def test_extract_audio_returns_none_on_ffmpeg_error(tmp_path):
    video = tmp_path / "video" / "aula01.mp4"
    video.parent.mkdir()
    video.touch()
    ai_data = tmp_path / "ai_data"

    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "ffmpeg")):
        result = extract_audio(video, ai_data)

    assert result is None
