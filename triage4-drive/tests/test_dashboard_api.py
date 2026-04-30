"""Tests for triage4_drive.ui.dashboard_api."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from triage4_drive.ui.dashboard_api import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["service"] == "triage4-drive"
    assert body["window_count"] >= 1


def test_report(client: TestClient) -> None:
    body = client.get("/report").json()
    for level in ("ok", "caution", "critical"):
        assert level in body["level_counts"]


def test_windows_list(client: TestClient) -> None:
    rows = client.get("/windows").json()
    assert rows
    for key in ("session_id", "alert_level", "overall", "index"):
        assert key in rows[0]


def test_window_by_index(client: TestClient) -> None:
    res = client.get("/windows/0")
    assert res.status_code == 200
    assert res.json()["index"] == 0


def test_window_404(client: TestClient) -> None:
    assert client.get("/windows/99999").status_code == 404


def test_alerts(client: TestClient) -> None:
    assert isinstance(client.get("/alerts").json(), list)


def test_demo_reload(client: TestClient) -> None:
    assert client.post("/demo/reload").json()["reloaded"] is True


def test_export_html(client: TestClient) -> None:
    res = client.get("/export.html")
    assert res.status_code == 200 and "triage4-drive" in res.text


def test_cors(client: TestClient) -> None:
    res = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"
