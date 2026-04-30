"""Tests for triage4_clinic.ui.dashboard_api."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from triage4_clinic.ui.dashboard_api import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["service"] == "triage4-clinic"
    assert body["submission_count"] >= 1


def test_report(client: TestClient) -> None:
    body = client.get("/report").json()
    for r in ("self_care", "schedule", "urgent_review"):
        assert r in body["recommendation_counts"]


def test_submissions_list(client: TestClient) -> None:
    rows = client.get("/submissions").json()
    assert rows
    for key in ("patient_token", "assessment", "alert_count"):
        assert key in rows[0]


def test_submission_by_token(client: TestClient) -> None:
    target = client.get("/submissions").json()[0]["patient_token"]
    res = client.get(f"/submissions/{target}")
    assert res.status_code == 200
    body = res.json()
    assert body["patient_token"] == target
    assert isinstance(body["alerts"], list)
    assert isinstance(body["reported_symptoms"], list)


def test_submission_404(client: TestClient) -> None:
    assert client.get("/submissions/NEVER").status_code == 404


def test_alerts(client: TestClient) -> None:
    assert isinstance(client.get("/alerts").json(), list)


def test_demo_reload(client: TestClient) -> None:
    assert client.post("/demo/reload").json()["reloaded"] is True


def test_export_html(client: TestClient) -> None:
    res = client.get("/export.html")
    assert res.status_code == 200 and "triage4-clinic" in res.text


def test_cors(client: TestClient) -> None:
    res = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"
