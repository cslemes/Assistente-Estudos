import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.whiteboard_ingester import (
    load_whiteboard_frames,
    frames_to_chunks,
)


# --- Helpers ---

def _make_classifications(tmp_path: Path, entries: list[dict]) -> Path:
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    (frames_dir / "classifications.json").write_text(json.dumps(entries))
    return frames_dir


# --- load_whiteboard_frames ---

def test_load_whiteboard_frames_filters_to_whiteboard_classification(tmp_path):
    entries = [
        {"frame": "frame_0001.jpg", "frame_path": "/f/frame_0001.jpg", "classification": "whiteboard"},
        {"frame": "frame_0002.jpg", "frame_path": "/f/frame_0002.jpg", "classification": "slide"},
        {"frame": "frame_0003.jpg", "frame_path": "/f/frame_0003.jpg", "classification": "whiteboard"},
    ]
    frames_dir = _make_classifications(tmp_path, entries)

    result = load_whiteboard_frames(str(frames_dir))

    assert len(result) == 2
    assert all(r["classification"] == "whiteboard" for r in result)


def test_load_whiteboard_frames_raises_when_no_classifications_file(tmp_path):
    empty_dir = tmp_path / "noframes"
    empty_dir.mkdir()

    with pytest.raises(FileNotFoundError):
        load_whiteboard_frames(str(empty_dir))


def test_load_whiteboard_frames_returns_empty_when_no_whiteboard_frames(tmp_path):
    entries = [
        {"frame": "frame_0001.jpg", "frame_path": "/f/frame_0001.jpg", "classification": "slide"},
    ]
    frames_dir = _make_classifications(tmp_path, entries)

    result = load_whiteboard_frames(str(frames_dir))

    assert result == []


# --- frames_to_chunks ---

def test_frames_to_chunks_returns_one_chunk_per_frame_with_text(tmp_path):
    frames = [
        {"frame": "frame_0005.jpg", "frame_path": "/f/frame_0005.jpg", "classification": "whiteboard"},
        {"frame": "frame_0010.jpg", "frame_path": "/f/frame_0010.jpg", "classification": "whiteboard"},
    ]
    mock_reader = MagicMock()
    mock_reader.readtext.side_effect = [
        [(None, "derivada parcial", 0.99)],
        [(None, "gradiente descendente", 0.95)],
    ]

    result = frames_to_chunks(frames, mock_reader, interval=5)

    assert len(result) == 2
    assert result[0]["text"] == "derivada parcial"
    assert result[0]["start_time"] == 20   # (5-1)*5
    assert result[1]["text"] == "gradiente descendente"
    assert result[1]["start_time"] == 45   # (10-1)*5


def test_frames_to_chunks_skips_frames_with_no_text(tmp_path):
    frames = [
        {"frame": "frame_0001.jpg", "frame_path": "/f/frame_0001.jpg", "classification": "whiteboard"},
        {"frame": "frame_0002.jpg", "frame_path": "/f/frame_0002.jpg", "classification": "whiteboard"},
    ]
    mock_reader = MagicMock()
    mock_reader.readtext.side_effect = [
        [],                                   # frame_0001: no text
        [(None, "backpropagation", 0.99)],    # frame_0002: has text
    ]

    result = frames_to_chunks(frames, mock_reader, interval=5)

    assert len(result) == 1
    assert result[0]["text"] == "backpropagation"


def test_frames_to_chunks_computes_correct_start_time():
    frames = [
        {"frame": "frame_0021.jpg", "frame_path": "/f/frame_0021.jpg", "classification": "whiteboard"},
    ]
    mock_reader = MagicMock()
    mock_reader.readtext.return_value = [(None, "some text", 0.99)]

    result = frames_to_chunks(frames, mock_reader, interval=10)

    assert result[0]["start_time"] == 200   # (21-1)*10


def test_frames_to_chunks_returns_frame_path_in_result():
    frames = [
        {"frame": "frame_0001.jpg", "frame_path": "/f/frame_0001.jpg", "classification": "whiteboard"},
    ]
    mock_reader = MagicMock()
    mock_reader.readtext.return_value = [(None, "text", 0.99)]

    result = frames_to_chunks(frames, mock_reader, interval=5)

    assert result[0]["frame_path"] == "/f/frame_0001.jpg"
