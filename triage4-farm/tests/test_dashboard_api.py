"""Tests for triage4_farm.ui.dashboard_api."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from triage4_farm.ui.dashboard_api import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["service"] == "triage4-farm"
    assert body["animal_count"] >= 1


def test_report(client: TestClient) -> None:
    body = client.get("/report").json()
    assert body["farm_id"]
    for f in ("well", "concern", "urgent"):
        assert f in body["flag_counts"]
    assert "herd_overall" in body


def test_animals_list(client: TestClient) -> None:
    rows = client.get("/animals").json()
    assert rows
    for key in ("animal_id", "flag", "overall"):
        assert key in rows[0]


def test_animal_by_id(client: TestClient) -> None:
    target = client.get("/animals").json()[0]["animal_id"]
    res = client.get(f"/animals/{target}")
    assert res.status_code == 200
    assert res.json()["animal_id"] == target


def test_animal_by_id_404(client: TestClient) -> None:
    assert client.get("/animals/NEVER").status_code == 404


def test_alerts(client: TestClient) -> None:
    assert isinstance(client.get("/alerts").json(), list)


def test_demo_reload(client: TestClient) -> None:
    assert client.post("/demo/reload").json()["reloaded"] is True


def test_export_html(client: TestClient) -> None:
    res = client.get("/export.html")
    assert res.status_code == 200 and "triage4-farm" in res.text


def test_cors(client: TestClient) -> None:
    res = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"
