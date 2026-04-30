"""Tests for triage4_fit.ui.dashboard_api."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from triage4_fit.ui.dashboard_api import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["service"] == "triage4-fit"
    assert body["rep_count"] >= 1


def test_report(client: TestClient) -> None:
    body = client.get("/report").json()
    assert body["exercise"]
    for sev in ("ok", "minor", "severe"):
        assert sev in body["severity_counts"]


def test_reps_list(client: TestClient) -> None:
    rows = client.get("/reps").json()
    assert rows
    for key in ("rep_index", "overall", "symmetry"):
        assert key in rows[0]


def test_rep_by_index(client: TestClient) -> None:
    target = client.get("/reps").json()[0]["rep_index"]
    res = client.get(f"/reps/{target}")
    assert res.status_code == 200
    assert res.json()["rep_index"] == target


def test_rep_404(client: TestClient) -> None:
    assert client.get("/reps/999").status_code == 404


def test_cues(client: TestClient) -> None:
    assert isinstance(client.get("/cues").json(), list)


def test_demo_reload(client: TestClient) -> None:
    assert client.post("/demo/reload").json()["reloaded"] is True


def test_export_html(client: TestClient) -> None:
    res = client.get("/export.html")
    assert res.status_code == 200 and "triage4-fit" in res.text


def test_cors(client: TestClient) -> None:
    res = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"
