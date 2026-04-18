import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.sync import router


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    app.get("/health")(lambda: {"status": "ok"})
    return TestClient(app)


# GET /health

def test_health_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# GET /status

def test_status_returns_initial_state(client):
    response = client.get("/status")

    assert response.status_code == 200
    data = response.json()
    assert data["running"] is False
    assert data["last_result"] is None
    assert data["last_error"] is None


# POST /sync

def test_sync_background_returns_started_message(client):
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("app.routers.sync._run_sync_job", lambda: None)
        response = client.post("/sync?background=false")

    assert response.status_code == 200
    assert "finished" in response.json()["message"]


def test_sync_returns_409_when_already_running(client):
    import app.routers.sync as sync_module

    sync_module._sync_status["running"] = True
    try:
        response = client.post("/sync")
        assert response.status_code == 409
    finally:
        sync_module._sync_status["running"] = False
