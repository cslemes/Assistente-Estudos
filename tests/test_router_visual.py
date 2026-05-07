import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.database as db
from app.routers.visual import router


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _make_point(source_type, text, start_time, course="ML", topic="CNN", aula_number=1):
    p = MagicMock()
    p.payload = {
        "source_type": source_type,
        "text": text,
        "start_time": start_time,
        "video_url": f"https://youtu.be/abc?t={start_time}",
        "slide_thumb": None,
        "course": course,
        "topic": topic,
        "aula_number": aula_number,
    }
    return p


def test_visual_returns_404_for_unknown_lesson(client):
    response = client.get("/visual/9999")

    assert response.status_code == 404


def test_visual_returns_chunks_sorted_by_start_time(client):
    db.insert_transcription(
        file_path=r"D:\Downloads\ML\CNN\ai_data\Aula_01_CNN.mp3",
        text="t",
        video_url="https://youtu.be/abc",
    )
    lesson_id = db.get_all_transcriptions()[0]["id"]

    points = [
        _make_point("slide", "Slide B", 120),
        _make_point("notebook", "Cell A", 60),
        _make_point("whiteboard", "Board C", 180),
    ]
    mock_scroll = MagicMock(return_value=(points, None))

    with patch("app.routers.visual.QdrantRetriever") as MockRetriever:
        MockRetriever.return_value.scroll_visual.return_value = [
            {"source_type": "notebook", "text": "Cell A", "start_time": 60, "video_url": "https://youtu.be/abc?t=60", "slide_thumb": None},
            {"source_type": "slide",    "text": "Slide B", "start_time": 120, "video_url": "https://youtu.be/abc?t=120", "slide_thumb": None},
            {"source_type": "whiteboard","text": "Board C", "start_time": 180, "video_url": "https://youtu.be/abc?t=180", "slide_thumb": None},
        ]
        response = client.get(f"/visual/{lesson_id}")

    assert response.status_code == 200
    chunks = response.json()
    assert len(chunks) == 3
    assert chunks[0]["start_time"] == 60
    assert chunks[1]["start_time"] == 120
    assert chunks[2]["start_time"] == 180


def test_visual_excludes_transcript_chunks(client):
    db.insert_transcription(
        file_path=r"D:\Downloads\ML\CNN\ai_data\Aula_01_CNN.mp3",
        text="t",
        video_url="https://youtu.be/abc",
    )
    lesson_id = db.get_all_transcriptions()[0]["id"]

    with patch("app.routers.visual.QdrantRetriever") as MockRetriever:
        MockRetriever.return_value.scroll_visual.return_value = []
        response = client.get(f"/visual/{lesson_id}")

    assert response.status_code == 200
    assert response.json() == []


def test_visual_returns_all_source_types(client):
    db.insert_transcription(
        file_path=r"D:\Downloads\ML\CNN\ai_data\Aula_01_CNN.mp3",
        text="t",
        video_url="https://youtu.be/abc",
    )
    lesson_id = db.get_all_transcriptions()[0]["id"]

    with patch("app.routers.visual.QdrantRetriever") as MockRetriever:
        MockRetriever.return_value.scroll_visual.return_value = [
            {"source_type": "slide",     "text": "s", "start_time": 10, "video_url": None, "slide_thumb": None},
            {"source_type": "notebook",  "text": "n", "start_time": 20, "video_url": None, "slide_thumb": None},
            {"source_type": "whiteboard","text": "w", "start_time": 30, "video_url": None, "slide_thumb": None},
        ]
        response = client.get(f"/visual/{lesson_id}")

    types = {c["source_type"] for c in response.json()}
    assert types == {"slide", "notebook", "whiteboard"}
