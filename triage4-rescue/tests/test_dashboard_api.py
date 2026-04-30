"""Tests for triage4_rescue.ui.dashboard_api.

Driven through fastapi.testclient.TestClient — runs the FastAPI app
in-process, no actual HTTP server. Covers each public endpoint at
the level of "does it return a 200 with the expected shape?".

These tests live behind the ``[ui]`` extra; if fastapi/httpx are
not installed, the whole module is skipped.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from triage4_rescue.ui.dashboard_api import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_returns_service_metadata(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["service"] == "triage4-rescue"
    assert body["version"]
    assert body["incident_id"]
    assert body["casualty_count"] >= 1


def test_incident_endpoint_returns_full_report(client: TestClient) -> None:
    res = client.get("/incident")
    assert res.status_code == 200
    body = res.json()
    assert body["incident_id"]
    assert isinstance(body["assessments"], list)
    assert isinstance(body["cues"], list)
    assert isinstance(body["counts"], dict)
    # Every START tag must appear in counts (zero allowed).
    for tag in ("immediate", "delayed", "minor", "deceased"):
        assert tag in body["counts"]


def test_casualties_list_endpoint(client: TestClient) -> None:
    res = client.get("/casualties")
    assert res.status_code == 200
    rows = res.json()
    assert isinstance(rows, list)
    assert len(rows) >= 1
    sample = rows[0]
    for key in ("casualty_id", "tag", "age_group", "reasoning",
                "flag_for_secondary_review"):
        assert key in sample


def test_casualty_by_id_returns_detail(client: TestClient) -> None:
    listing = client.get("/casualties").json()
    target = listing[0]["casualty_id"]
    res = client.get(f"/casualties/{target}")
    assert res.status_code == 200
    body = res.json()
    assert body["casualty_id"] == target
    assert isinstance(body["cues"], list)


def test_casualty_by_id_404_for_unknown(client: TestClient) -> None:
    res = client.get("/casualties/NEVER-EXISTED")
    assert res.status_code == 404


def test_alerts_endpoint(client: TestClient) -> None:
    res = client.get("/alerts")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_demo_reload_resets_state(client: TestClient) -> None:
    res = client.post("/demo/reload")
    assert res.status_code == 200
    body = res.json()
    assert body["reloaded"] is True
    assert body["casualty_count"] >= 1


def test_export_html_returns_html(client: TestClient) -> None:
    res = client.get("/export.html")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/html")
    body = res.text
    assert "<table>" in body
    assert "triage4-rescue" in body


def test_cors_headers_present_for_vite_origin(client: TestClient) -> None:
    res = client.get(
        "/health",
        headers={"Origin": "http://localhost:5173"},
    )
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"
