"""Tests for triage4_crowd.ui.dashboard_api."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from triage4_crowd.ui.dashboard_api import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["service"] == "triage4-crowd"
    assert body["zone_count"] >= 1


def test_report(client: TestClient) -> None:
    body = client.get("/report").json()
    assert body["venue_id"]
    assert isinstance(body["scores"], list)
    for level in ("ok", "watch", "urgent"):
        assert level in body["level_counts"]


def test_zones_list(client: TestClient) -> None:
    rows = client.get("/zones").json()
    assert rows
    for key in ("zone_id", "alert_level", "overall"):
        assert key in rows[0]


def test_zone_by_id(client: TestClient) -> None:
    target = client.get("/zones").json()[0]["zone_id"]
    res = client.get(f"/zones/{target}")
    assert res.status_code == 200
    assert res.json()["zone_id"] == target


def test_zone_by_id_404(client: TestClient) -> None:
    assert client.get("/zones/NEVER").status_code == 404


def test_alerts(client: TestClient) -> None:
    assert isinstance(client.get("/alerts").json(), list)


def test_demo_reload(client: TestClient) -> None:
    assert client.post("/demo/reload").json()["reloaded"] is True


def test_export_html(client: TestClient) -> None:
    res = client.get("/export.html")
    assert res.status_code == 200 and "triage4-crowd" in res.text


def test_cors(client: TestClient) -> None:
    res = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"
