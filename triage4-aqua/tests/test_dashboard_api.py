"""Tests for triage4_aqua.ui.dashboard_api."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from triage4_aqua.ui.dashboard_api import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_returns_service_metadata(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["service"] == "triage4-aqua"
    assert body["pool_id"]
    assert body["swimmer_count"] >= 1


def test_report_endpoint(client: TestClient) -> None:
    body = client.get("/report").json()
    assert body["pool_id"]
    assert isinstance(body["scores"], list)
    assert isinstance(body["alerts"], list)
    for level in ("ok", "watch", "urgent"):
        assert level in body["level_counts"]


def test_swimmers_list(client: TestClient) -> None:
    rows = client.get("/swimmers").json()
    assert isinstance(rows, list) and rows
    for key in ("swimmer_token", "alert_level", "overall"):
        assert key in rows[0]


def test_swimmer_by_token_returns_detail(client: TestClient) -> None:
    rows = client.get("/swimmers").json()
    target = rows[0]["swimmer_token"]
    res = client.get(f"/swimmers/{target}")
    assert res.status_code == 200
    assert res.json()["swimmer_token"] == target
    assert isinstance(res.json()["alerts"], list)


def test_swimmer_by_token_404(client: TestClient) -> None:
    assert client.get("/swimmers/NEVER").status_code == 404


def test_alerts_endpoint(client: TestClient) -> None:
    assert isinstance(client.get("/alerts").json(), list)


def test_demo_reload(client: TestClient) -> None:
    body = client.post("/demo/reload").json()
    assert body["reloaded"] is True
    assert body["swimmer_count"] >= 1


def test_export_html(client: TestClient) -> None:
    res = client.get("/export.html")
    assert res.status_code == 200
    assert "<table>" in res.text
    assert "triage4-aqua" in res.text


def test_cors_for_vite_origin(client: TestClient) -> None:
    res = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"
