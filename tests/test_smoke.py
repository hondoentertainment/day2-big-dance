"""Smoke tests — no network (pipeline not called)."""

from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    c = TestClient(app)
    r = c.get("/api/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_picks_meta() -> None:
    c = TestClient(app)
    r = c.get("/api/picks/meta")
    assert r.status_code == 200
    body = r.json()
    assert "ttl_seconds" in body
