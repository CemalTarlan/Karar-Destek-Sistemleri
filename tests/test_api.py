"""FastAPI route tests using the TestClient (LM Studio mocked via conftest)."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


def test_health_endpoint(app: Any) -> None:
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    assert "version" in payload
    assert "disclaimer" in payload


def test_triage_start_creates_conversation(app: Any) -> None:
    client = TestClient(app)
    r = client.post("/triage/start")
    assert r.status_code == 200
    payload = r.json()
    assert "conversation_id" in payload
    assert payload["state"]["step"] == "INTAKE"


def test_triage_turn_red_flag_skips_to_decision(app: Any) -> None:
    client = TestClient(app)
    start = client.post("/triage/start").json()
    conv_id = start["conversation_id"]
    r = client.post(
        "/triage/turn",
        json={
            "conversation_id": conv_id,
            "message": "Göğsümde sıkışma var, ağrı sol koluma yayılıyor.",
        },
    )
    assert r.status_code == 200
    body = r.json()["response"]
    assert body["is_decided"] is True
    assert body["state"]["decision"]["color"] == "KIRMIZI"


def test_triage_turn_unknown_conversation(app: Any) -> None:
    client = TestClient(app)
    r = client.post(
        "/triage/turn",
        json={"conversation_id": "no-such-id", "message": "merhaba"},
    )
    assert r.status_code == 404


def test_lm_studio_health_when_unreachable(app: Any) -> None:
    client = TestClient(app)
    r = client.get("/lm-studio/health")
    assert r.status_code == 200
    body = r.json()
    assert "reachable" in body
    assert "base_url" in body
