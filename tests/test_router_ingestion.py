import pytest
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.ingestion import router
import app.database as db


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


# GET /transcriptions/pending

def test_get_pending_returns_empty(client):
    response = client.get("/transcriptions/pending")

    assert response.status_code == 200
    assert response.json() == {"count": 0, "transcriptions": []}


def test_get_pending_returns_inserted_records(client):
    db.insert_transcription(file_path="/audio/aula01.mp3", text="Olá mundo")
    db.insert_transcription(file_path="/audio/aula02.mp3", text="Segunda aula")

    response = client.get("/transcriptions/pending")

    data = response.json()
    assert data["count"] == 2
    paths = [r["file_path"] for r in data["transcriptions"]]
    assert "/audio/aula01.mp3" in paths
    assert "/audio/aula02.mp3" in paths


def test_get_pending_excludes_sent_records(client):
    db.insert_transcription(file_path="/audio/aula01.mp3", text="sent one")
    row_id = db.get_pending()[0]["id"]
    db.set_status(row_id, "sent")
    db.insert_transcription(file_path="/audio/aula02.mp3", text="pending one")

    response = client.get("/transcriptions/pending")

    data = response.json()
    assert data["count"] == 1
    assert data["transcriptions"][0]["file_path"] == "/audio/aula02.mp3"


# PATCH /transcriptions/{id}/status

def test_patch_status_updates_record(client):
    db.insert_transcription(file_path="/audio/aula01.mp3", text="hello")
    row_id = db.get_pending()[0]["id"]

    response = client.patch(f"/transcriptions/{row_id}/status?status=sent")

    assert response.status_code == 200
    assert response.json() == {"id": row_id, "status": "sent"}
    assert db.get_transcription(row_id)["status"] == "sent"


def test_patch_status_rejects_invalid_status(client):
    db.insert_transcription(file_path="/audio/aula01.mp3", text="hello")
    row_id = db.get_pending()[0]["id"]

    response = client.patch(f"/transcriptions/{row_id}/status?status=invalid")

    assert response.status_code == 400


def test_patch_status_accepts_all_valid_transitions(client):
    for status in ("pending", "embedded", "sent"):
        db.insert_transcription(file_path=f"/audio/{status}.mp3", text="x")
        row_id = db.get_pending()[-1]["id"]

        response = client.patch(f"/transcriptions/{row_id}/status?status={status}")

        assert response.status_code == 200, f"failed for status={status}"


# POST /ingest/slides

def test_ingest_slides_returns_404_for_missing_pptx(client):
    response = client.post("/ingest/slides", json={
        "pptx_path": "/does/not/exist.pptx",
        "video_path": "/video/aula01.mp4",
        "frames_dir": "/frames",
    })

    assert response.status_code == 404


def test_ingest_slides_returns_404_for_missing_frames_dir(client, tmp_path):
    pptx = tmp_path / "aula.pptx"
    pptx.touch()

    response = client.post("/ingest/slides", json={
        "pptx_path": str(pptx),
        "video_path": "/video/aula01.mp4",
        "frames_dir": "/nonexistent/frames",
    })

    assert response.status_code == 404


def test_ingest_slides_calls_ingest_pptx_and_returns_result(client, tmp_path):
    pptx = tmp_path / "aula.pptx"
    pptx.touch()
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()

    with patch("app.routers.ingestion.ingest_pptx", return_value={"ingested": 3}) as mock_ingest:
        response = client.post("/ingest/slides", json={
            "pptx_path": str(pptx),
            "video_path": "/video/aula01.mp4",
            "frames_dir": str(frames_dir),
            "interval": 10,
        })

    assert response.status_code == 200
    assert response.json() == {"ingested": 3}
    mock_ingest.assert_called_once_with(
        pptx_path=str(pptx),
        video_path="/video/aula01.mp4",
        frames_dir=str(frames_dir),
        interval=10,
    )


# POST /ingest/notebook

def test_ingest_notebook_returns_404_for_missing_ipynb(client):
    response = client.post("/ingest/notebook", json={
        "ipynb_path": "/does/not/exist.ipynb",
        "video_path": "/video/aula01.mp4",
        "frames_dir": "/frames",
    })

    assert response.status_code == 404


def test_ingest_notebook_returns_404_for_missing_frames_dir(client, tmp_path):
    ipynb = tmp_path / "aula.ipynb"
    ipynb.touch()

    response = client.post("/ingest/notebook", json={
        "ipynb_path": str(ipynb),
        "video_path": "/video/aula01.mp4",
        "frames_dir": "/nonexistent/frames",
    })

    assert response.status_code == 404


def test_ingest_notebook_calls_ingest_notebook_and_returns_result(client, tmp_path):
    ipynb = tmp_path / "aula.ipynb"
    ipynb.touch()
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()

    with patch("app.routers.ingestion.ingest_notebook", return_value={"ingested": 5}) as mock_ingest:
        response = client.post("/ingest/notebook", json={
            "ipynb_path": str(ipynb),
            "video_path": "/video/aula01.mp4",
            "frames_dir": str(frames_dir),
            "interval": 10,
        })

    assert response.status_code == 200
    assert response.json() == {"ingested": 5}
    mock_ingest.assert_called_once_with(
        ipynb_path=str(ipynb),
        video_path="/video/aula01.mp4",
        frames_dir=str(frames_dir),
        interval=10,
    )


# POST /ingest/whiteboard

def test_ingest_whiteboard_returns_404_for_missing_frames_dir(client):
    response = client.post("/ingest/whiteboard", json={
        "video_path": "/video/aula01.mp4",
        "frames_dir": "/nonexistent/frames",
    })

    assert response.status_code == 404


def test_ingest_whiteboard_calls_ingest_whiteboard_and_returns_result(client, tmp_path):
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()

    with patch("app.routers.ingestion.ingest_whiteboard", return_value={"ingested": 4}) as mock_ingest:
        response = client.post("/ingest/whiteboard", json={
            "video_path": "/video/aula01.mp4",
            "frames_dir": str(frames_dir),
            "interval": 10,
        })

    assert response.status_code == 200
    assert response.json() == {"ingested": 4}
    mock_ingest.assert_called_once_with(
        video_path="/video/aula01.mp4",
        frames_dir=str(frames_dir),
        interval=10,
    )
