"""Tests for triage4_home.ui.dashboard_api."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from triage4_home.ui.dashboard_api import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["service"] == "triage4-home"
    assert body["window_count"] >= 1


def test_report(client: TestClient) -> None:
    body = client.get("/report").json()
    assert body["residence_id"]
    for level in ("ok", "check_in", "urgent"):
        assert level in body["level_counts"]


def test_windows_list(client: TestClient) -> None:
    rows = client.get("/windows").json()
    assert rows
    for key in ("window_id", "alert_level", "overall"):
        assert key in rows[0]


def test_window_by_id(client: TestClient) -> None:
    target = client.get("/windows").json()[0]["window_id"]
    res = client.get(f"/windows/{target}")
    assert res.status_code == 200
    assert res.json()["window_id"] == target


def test_window_404(client: TestClient) -> None:
    assert client.get("/windows/NEVER").status_code == 404


def test_alerts(client: TestClient) -> None:
    assert isinstance(client.get("/alerts").json(), list)


def test_demo_reload(client: TestClient) -> None:
    assert client.post("/demo/reload").json()["reloaded"] is True


def test_export_html(client: TestClient) -> None:
    res = client.get("/export.html")
    assert res.status_code == 200 and "triage4-home" in res.text


def test_cors(client: TestClient) -> None:
    res = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"
