import pytest
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
