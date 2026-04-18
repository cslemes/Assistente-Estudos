import pytest
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.audio import router


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


# POST /transcribe

def test_transcribe_returns_404_for_missing_file(client):
    response = client.post("/transcribe", json={"file_path": "/does/not/exist.mp3"})

    assert response.status_code == 404


def test_transcribe_calls_transcribe_file_and_returns_output(client, tmp_path):
    audio = tmp_path / "aula01.mp3"
    audio.touch()
    output = tmp_path / "aula01.txt"

    with patch("app.routers.audio.transcribe_file") as mock_transcribe:
        mock_transcribe.side_effect = lambda path: output.write_text("transcript")
        response = client.post("/transcribe", json={"file_path": str(audio)})

    assert response.status_code == 200
    data = response.json()
    assert data["file_path"] == str(audio)
    assert data["output_file"] == str(output)
    assert data["exists"] is True
    mock_transcribe.assert_called_once_with(str(audio))


def test_transcribe_exists_false_when_transcription_produces_no_file(client, tmp_path):
    audio = tmp_path / "aula01.mp3"
    audio.touch()

    with patch("app.routers.audio.transcribe_file"):
        response = client.post("/transcribe", json={"file_path": str(audio)})

    assert response.status_code == 200
    assert response.json()["exists"] is False


# POST /extract-audio

def test_extract_audio_returns_404_for_missing_file(client):
    response = client.post("/extract-audio", json={"file_path": "/does/not/exist.mp4"})

    assert response.status_code == 404


def test_extract_audio_returns_500_when_ffmpeg_fails(client, tmp_path):
    video = tmp_path / "video" / "aula01.mp4"
    video.parent.mkdir()
    video.touch()

    with patch("app.routers.audio.extract_audio_from_video", return_value=None):
        response = client.post("/extract-audio", json={"file_path": str(video)})

    assert response.status_code == 500


def test_extract_audio_returns_audio_path_on_success(client, tmp_path):
    video = tmp_path / "video" / "aula01.mp4"
    video.parent.mkdir()
    video.touch()
    expected_audio = str(tmp_path / "ai_data" / "aula01.mp3")

    with patch("app.routers.audio.extract_audio_from_video", return_value=expected_audio):
        response = client.post("/extract-audio", json={"file_path": str(video)})

    assert response.status_code == 200
    assert response.json()["audio_path"] == expected_audio
