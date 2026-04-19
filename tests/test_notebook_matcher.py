import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.notebook_matcher import (
    extract_notebook_cells,
    load_notebook_frames,
    match_cells_to_frames,
    ocr_frame,
)


# --- Helpers ---

def _make_ipynb(tmp_path: Path, cells: list[dict]) -> str:
    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {},
        "cells": cells,
    }
    path = str(tmp_path / "aula.ipynb")
    Path(path).write_text(json.dumps(nb))
    return path


def _make_code_cell(source: str) -> dict:
    return {"cell_type": "code", "source": source, "metadata": {}, "outputs": []}


def _make_markdown_cell(source: str) -> dict:
    return {"cell_type": "markdown", "source": source, "metadata": {}}


def _make_classifications(tmp_path: Path, entries: list[dict]) -> Path:
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    (frames_dir / "classifications.json").write_text(json.dumps(entries))
    return frames_dir


# --- extract_notebook_cells ---

def test_extract_notebook_cells_returns_one_entry_per_cell(tmp_path):
    ipynb = _make_ipynb(tmp_path, [_make_code_cell("x = 1"), _make_markdown_cell("# Title")])

    result = extract_notebook_cells(ipynb)

    assert len(result) == 2
    assert all("cell_index" in r and "text" in r and "cell_type" in r for r in result)


def test_extract_notebook_cells_correct_index(tmp_path):
    ipynb = _make_ipynb(tmp_path, [_make_code_cell("a = 1"), _make_code_cell("b = 2")])

    result = extract_notebook_cells(ipynb)

    assert result[0]["cell_index"] == 0
    assert result[1]["cell_index"] == 1


def test_extract_notebook_cells_includes_cell_type(tmp_path):
    ipynb = _make_ipynb(tmp_path, [_make_code_cell("x"), _make_markdown_cell("text")])

    result = extract_notebook_cells(ipynb)

    assert result[0]["cell_type"] == "code"
    assert result[1]["cell_type"] == "markdown"


def test_extract_notebook_cells_handles_list_source(tmp_path):
    cell = {"cell_type": "code", "source": ["line1\n", "line2"], "metadata": {}, "outputs": []}
    ipynb = _make_ipynb(tmp_path, [cell])

    result = extract_notebook_cells(ipynb)

    assert "line1" in result[0]["text"]
    assert "line2" in result[0]["text"]


def test_extract_notebook_cells_skips_empty_cells(tmp_path):
    ipynb = _make_ipynb(tmp_path, [_make_code_cell(""), _make_code_cell("x = 1")])

    result = extract_notebook_cells(ipynb)

    assert len(result) == 1
    assert "x = 1" in result[0]["text"]


# --- load_notebook_frames ---

def test_load_notebook_frames_filters_to_notebook_classification(tmp_path):
    entries = [
        {"frame": "frame_0001.jpg", "frame_path": "/f/frame_0001.jpg", "classification": "notebook"},
        {"frame": "frame_0002.jpg", "frame_path": "/f/frame_0002.jpg", "classification": "slide"},
        {"frame": "frame_0003.jpg", "frame_path": "/f/frame_0003.jpg", "classification": "notebook"},
    ]
    frames_dir = _make_classifications(tmp_path, entries)

    result = load_notebook_frames(str(frames_dir))

    assert len(result) == 2
    assert all(r["classification"] == "notebook" for r in result)


def test_load_notebook_frames_raises_when_no_classifications_file(tmp_path):
    empty_dir = tmp_path / "noframes"
    empty_dir.mkdir()

    with pytest.raises(FileNotFoundError):
        load_notebook_frames(str(empty_dir))


def test_load_notebook_frames_returns_empty_when_no_notebook_frames(tmp_path):
    entries = [
        {"frame": "frame_0001.jpg", "frame_path": "/f/frame_0001.jpg", "classification": "slide"},
    ]
    frames_dir = _make_classifications(tmp_path, entries)

    result = load_notebook_frames(str(frames_dir))

    assert result == []


# --- ocr_frame ---

def test_ocr_frame_returns_string(tmp_path):
    frame = tmp_path / "frame.jpg"
    frame.touch()
    mock_reader = MagicMock()
    mock_reader.readtext.return_value = [
        (None, "hello", 0.99),
        (None, "world", 0.95),
    ]

    result = ocr_frame(str(frame), mock_reader)

    assert isinstance(result, str)
    assert "hello" in result
    assert "world" in result


def test_ocr_frame_calls_reader_with_frame_path(tmp_path):
    frame = tmp_path / "frame.jpg"
    frame.touch()
    mock_reader = MagicMock()
    mock_reader.readtext.return_value = []

    ocr_frame(str(frame), mock_reader)

    mock_reader.readtext.assert_called_once_with(str(frame), detail=1)


def test_ocr_frame_returns_empty_string_when_no_text(tmp_path):
    frame = tmp_path / "frame.jpg"
    frame.touch()
    mock_reader = MagicMock()
    mock_reader.readtext.return_value = []

    result = ocr_frame(str(frame), mock_reader)

    assert result == ""


# --- match_cells_to_frames ---

def test_match_cells_to_frames_returns_best_match_per_cell(tmp_path):
    cells = [{"cell_index": 0, "cell_type": "code", "text": "import numpy as np"}]
    frames = [
        {"frame": "frame_0005.jpg", "frame_path": "/f/frame_0005.jpg", "classification": "notebook"},
        {"frame": "frame_0010.jpg", "frame_path": "/f/frame_0010.jpg", "classification": "notebook"},
    ]
    mock_reader = MagicMock()
    # frame 0005 has text that overlaps with cell, frame 0010 does not
    mock_reader.readtext.side_effect = [
        [(None, "import numpy as np", 0.99)],  # frame_0005
        [(None, "something else entirely", 0.99)],  # frame_0010
    ]

    result = match_cells_to_frames(cells, frames, mock_reader, interval=5)

    assert len(result) == 1
    assert result[0]["cell_index"] == 0
    assert "frame_0005" in result[0]["frame_path"]
    assert "start_time" in result[0]
    assert "overlap" in result[0]


def test_match_cells_to_frames_skips_cells_with_no_overlap(tmp_path):
    cells = [{"cell_index": 0, "cell_type": "code", "text": "very unique content xyz"}]
    frames = [
        {"frame": "frame_0001.jpg", "frame_path": "/f/frame_0001.jpg", "classification": "notebook"},
    ]
    mock_reader = MagicMock()
    mock_reader.readtext.return_value = [(None, "completely different text", 0.99)]

    result = match_cells_to_frames(cells, frames, mock_reader, interval=5)

    assert result == []


def test_match_cells_to_frames_computes_start_time_from_frame_name():
    cells = [{"cell_index": 0, "cell_type": "code", "text": "x = 1"}]
    frames = [
        {"frame": "frame_0011.jpg", "frame_path": "/f/frame_0011.jpg", "classification": "notebook"},
    ]
    mock_reader = MagicMock()
    mock_reader.readtext.return_value = [(None, "x = 1", 0.99)]

    result = match_cells_to_frames(cells, frames, mock_reader, interval=5)

    assert result[0]["start_time"] == 50  # (11 - 1) * 5
