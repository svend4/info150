"""Tests for triage4_fish.ui.dashboard_api.

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

from triage4_fish.ui.dashboard_api import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_returns_service_metadata(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["service"] == "triage4-fish"
    assert body["version"]
    assert body["farm_id"]
    assert body["pen_count"] >= 1


def test_report_endpoint_returns_full_report(client: TestClient) -> None:
    res = client.get("/report")
    assert res.status_code == 200
    body = res.json()
    assert body["farm_id"]
    assert isinstance(body["scores"], list)
    assert isinstance(body["alerts"], list)
    assert isinstance(body["level_counts"], dict)
    for level in ("steady", "watch", "urgent"):
        assert level in body["level_counts"]


def test_pens_list_endpoint(client: TestClient) -> None:
    res = client.get("/pens")
    assert res.status_code == 200
    rows = res.json()
    assert isinstance(rows, list)
    assert len(rows) >= 1
    sample = rows[0]
    for key in (
        "pen_id",
        "gill_rate_safety",
        "school_cohesion_safety",
        "sea_lice_safety",
        "mortality_safety",
        "water_chemistry_safety",
        "overall",
        "welfare_level",
    ):
        assert key in sample


def test_pen_by_id_returns_detail_with_alerts(client: TestClient) -> None:
    listing = client.get("/pens").json()
    target = listing[0]["pen_id"]
    res = client.get(f"/pens/{target}")
    assert res.status_code == 200
    body = res.json()
    assert body["pen_id"] == target
    assert isinstance(body["alerts"], list)


def test_pen_by_id_404_for_unknown(client: TestClient) -> None:
    res = client.get("/pens/NEVER-EXISTED")
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
    assert body["pen_count"] >= 1


def test_export_html_returns_html(client: TestClient) -> None:
    res = client.get("/export.html")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/html")
    body = res.text
    assert "<table>" in body
    assert "triage4-fish" in body


def test_cors_headers_present_for_vite_origin(client: TestClient) -> None:
    res = client.get(
        "/health",
        headers={"Origin": "http://localhost:5173"},
    )
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_overall_scores_in_unit_interval(client: TestClient) -> None:
    """Sanity — every pen score must lie in [0, 1]."""
    pens = client.get("/pens").json()
    for p in pens:
        for k in (
            "gill_rate_safety",
            "school_cohesion_safety",
            "sea_lice_safety",
            "mortality_safety",
            "water_chemistry_safety",
            "overall",
        ):
            assert 0.0 <= p[k] <= 1.0, f"{p['pen_id']}.{k} out of [0, 1]"
