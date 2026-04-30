"""Tests for triage4_sport.ui.dashboard_api."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from triage4_sport.ui.dashboard_api import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["service"] == "triage4-sport"
    assert body["session_count"] >= 1


def test_report(client: TestClient) -> None:
    body = client.get("/report").json()
    for b in ("steady", "monitor", "hold"):
        assert b in body["band_counts"]


def test_sessions_list(client: TestClient) -> None:
    rows = client.get("/sessions").json()
    assert rows
    for key in ("athlete_token", "assessment", "coach_message_count"):
        assert key in rows[0]


def test_session_by_token(client: TestClient) -> None:
    target = client.get("/sessions").json()[0]["athlete_token"]
    res = client.get(f"/sessions/{target}")
    assert res.status_code == 200
    body = res.json()
    assert body["athlete_token"] == target
    assert isinstance(body["coach_messages"], list)


def test_session_404(client: TestClient) -> None:
    assert client.get("/sessions/NEVER").status_code == 404


def test_demo_reload(client: TestClient) -> None:
    assert client.post("/demo/reload").json()["reloaded"] is True


def test_export_html(client: TestClient) -> None:
    res = client.get("/export.html")
    assert res.status_code == 200 and "triage4-sport" in res.text


def test_cors(client: TestClient) -> None:
    res = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"
