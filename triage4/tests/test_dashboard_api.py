"""Endpoint tests for the FastAPI dashboard.

Exercises every endpoint added since Phase 10:

- Tier 1: /mission/status, /casualties/{id}/twin, /forecast/*,
  /evaluation/scorecard
- Tier 2: /casualties/{id}/second-opinion, /uncertainty, /conflict
- Tier 3: /overview, /casualties/{id}/marker
- Final: /casualties/{id}/skeletal, /sensing/ranked

Each endpoint is tested for:
- happy-path 200 + shape of the response
- 404 on unknown casualty (where applicable)
- key invariants that the UI depends on (probability sum ≈ 1 for the
  Bayesian twin, mission priority ∈ {escalate, sustain, wind_down},
  etc.)

Shared TestClient fixture runs on_startup once per test so the
seeded graph, mission graph, skeletal graphs, and evidence memory
are all populated.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from triage4.ui.dashboard_api import app


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Mission (Tier 1)
# ---------------------------------------------------------------------------


def test_mission_status_returns_all_keys(client: TestClient) -> None:
    r = client.get("/mission/status")
    assert r.status_code == 200
    body = r.json()
    assert set(body) >= {
        "signature",
        "priority",
        "score",
        "contributions",
        "reasons",
        "medic_assignments",
        "unresolved_regions",
    }


def test_mission_status_priority_band(client: TestClient) -> None:
    r = client.get("/mission/status")
    body = r.json()
    assert body["priority"] in {"escalate", "sustain", "wind_down"}
    assert 0.0 <= body["score"] <= 1.0


def test_mission_status_signature_channels_in_unit(client: TestClient) -> None:
    body = client.get("/mission/status").json()
    for channel in (
        "casualty_density",
        "immediate_fraction",
        "unresolved_sector_fraction",
        "medic_utilisation",
        "time_budget_burn",
    ):
        v = body["signature"][channel]
        assert 0.0 <= v <= 1.0


# ---------------------------------------------------------------------------
# Bayesian twin (Tier 1)
# ---------------------------------------------------------------------------


def test_twin_returns_posterior_probs(client: TestClient) -> None:
    r = client.get("/casualties/C1/twin")
    assert r.status_code == 200
    body = r.json()
    assert body["casualty_id"] == "C1"
    assert set(body["priority_probs"]) == {"immediate", "delayed", "minimal"}


def test_twin_posterior_sums_to_one(client: TestClient) -> None:
    body = client.get("/casualties/C1/twin").json()
    total = sum(body["priority_probs"].values())
    assert abs(total - 1.0) < 1e-3


def test_twin_most_likely_matches_probs(client: TestClient) -> None:
    body = client.get("/casualties/C1/twin").json()
    max_band = max(body["priority_probs"], key=lambda k: body["priority_probs"][k])
    assert body["most_likely_priority"] == max_band
    assert body["most_likely_probability"] == pytest.approx(
        body["priority_probs"][max_band], abs=1e-3,
    )


def test_twin_ess_flags_degeneracy(client: TestClient) -> None:
    body = client.get("/casualties/C1/twin").json()
    assert 0.0 <= body["effective_sample_size"] <= 200.0
    assert body["is_degenerate"] == (body["effective_sample_size"] < 5.0)


def test_twin_unknown_casualty_returns_404(client: TestClient) -> None:
    r = client.get("/casualties/UNKNOWN/twin")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Forecast (Tier 1)
# ---------------------------------------------------------------------------


def test_forecast_casualty_returns_projection(client: TestClient) -> None:
    r = client.get("/forecast/casualty/C1?minutes=5")
    assert r.status_code == 200
    body = r.json()
    assert body["casualty_id"] == "C1"
    assert body["minutes_ahead"] == 5.0
    assert body["projected_priority"] in {"immediate", "delayed", "minimal"}
    assert 0.0 <= body["projected_score"] <= 1.0
    assert 0.0 <= body["confidence"] <= 1.0


def test_forecast_casualty_returns_score_history(client: TestClient) -> None:
    body = client.get("/forecast/casualty/C1?minutes=3").json()
    assert isinstance(body["score_history"], list)
    assert len(body["score_history"]) >= 2


def test_forecast_casualty_404(client: TestClient) -> None:
    assert client.get("/forecast/casualty/UNKNOWN?minutes=5").status_code == 404


def test_forecast_mission_returns_projected_signature(client: TestClient) -> None:
    r = client.get("/forecast/mission?minutes=5")
    assert r.status_code == 200
    body = r.json()
    assert body["minutes_ahead"] == 5.0
    assert body["projected_priority"] in {"escalate", "sustain", "wind_down"}
    sig = body["projected_signature"]
    for channel in (
        "casualty_density",
        "immediate_fraction",
        "unresolved_sector_fraction",
        "medic_utilisation",
        "time_budget_burn",
    ):
        assert 0.0 <= sig[channel] <= 1.0
    assert set(body["per_channel_slope"]) == set(sig)


# ---------------------------------------------------------------------------
# Scorecard (Tier 1)
# ---------------------------------------------------------------------------


def test_scorecard_returns_gate2_and_counterfactuals(client: TestClient) -> None:
    r = client.get("/evaluation/scorecard")
    assert r.status_code == 200
    body = r.json()
    assert set(body) >= {"gate2", "counterfactuals", "summary"}


def test_scorecard_gate2_metrics_in_unit(client: TestClient) -> None:
    gate2 = client.get("/evaluation/scorecard").json()["gate2"]
    assert 0.0 <= gate2["accuracy"] <= 1.0
    assert 0.0 <= gate2["macro_f1"] <= 1.0
    assert 0.0 <= gate2["critical_miss_rate"] <= 1.0


def test_scorecard_confusion_is_square(client: TestClient) -> None:
    gate2 = client.get("/evaluation/scorecard").json()["gate2"]
    cm = gate2["confusion_matrix"]
    labels = gate2["class_labels"]
    assert len(cm) == len(labels)
    for row in cm:
        assert len(row) == len(labels)


def test_scorecard_counterfactual_mean_regret_in_unit(client: TestClient) -> None:
    cf = client.get("/evaluation/scorecard").json()["counterfactuals"]
    assert 0.0 <= cf["mean_regret"] <= 1.0
    assert cf["n"] == len(cf["cases"])


# ---------------------------------------------------------------------------
# Second-opinion (Tier 2)
# ---------------------------------------------------------------------------


def test_second_opinion_returns_three_classifiers(client: TestClient) -> None:
    r = client.get("/casualties/C1/second-opinion")
    assert r.status_code == 200
    body = r.json()
    names = [c["name"] for c in body["classifiers"]]
    assert names == [
        "RapidTriageEngine",
        "LarreyBaselineTriage",
        "CelegansTriageNet",
    ]


def test_second_opinion_agreement_flag_consistent(client: TestClient) -> None:
    body = client.get("/casualties/C1/second-opinion").json()
    priorities = {c["priority"] for c in body["classifiers"]}
    assert body["agreement"] == (len(priorities) == 1)
    assert set(body["distinct_priorities"]) == priorities


def test_second_opinion_404(client: TestClient) -> None:
    assert client.get("/casualties/UNKNOWN/second-opinion").status_code == 404


# ---------------------------------------------------------------------------
# Uncertainty (Tier 2)
# ---------------------------------------------------------------------------


def test_uncertainty_returns_report_shape(client: TestClient) -> None:
    r = client.get("/casualties/C1/uncertainty")
    assert r.status_code == 200
    body = r.json()
    assert set(body) >= {
        "casualty_id",
        "base_score",
        "overall_confidence",
        "overall_uncertainty",
        "adjusted_score",
        "per_channel_confidence",
    }


def test_uncertainty_unit_range(client: TestClient) -> None:
    body = client.get("/casualties/C1/uncertainty").json()
    for key in ("base_score", "overall_confidence", "overall_uncertainty", "adjusted_score"):
        assert 0.0 <= body[key] <= 1.0
    assert abs(body["overall_confidence"] + body["overall_uncertainty"] - 1.0) < 1e-3


def test_uncertainty_adjusted_leq_base(client: TestClient) -> None:
    body = client.get("/casualties/C1/uncertainty").json()
    # adjusted = base × overall_confidence ≤ base.
    assert body["adjusted_score"] <= body["base_score"] + 1e-6


def test_uncertainty_404(client: TestClient) -> None:
    assert client.get("/casualties/UNKNOWN/uncertainty").status_code == 404


# ---------------------------------------------------------------------------
# Conflict resolver (Tier 2)
# ---------------------------------------------------------------------------


def test_conflict_returns_evidence_and_ranking(client: TestClient) -> None:
    r = client.get("/casualties/C1/conflict")
    assert r.status_code == 200
    body = r.json()
    assert set(body) >= {
        "casualty_id",
        "evidence_tokens",
        "raw_scores",
        "ranked",
        "groups",
    }


def test_conflict_ranked_has_stable_fields(client: TestClient) -> None:
    body = client.get("/casualties/C1/conflict").json()
    for entry in body["ranked"]:
        assert set(entry) >= {
            "name",
            "raw_score",
            "adjusted_score",
            "suppressed",
            "reasons",
        }
        assert 0.0 <= entry["raw_score"] <= 1.0
        assert 0.0 <= entry["adjusted_score"] <= 1.0


def test_conflict_404(client: TestClient) -> None:
    assert client.get("/casualties/UNKNOWN/conflict").status_code == 404


# ---------------------------------------------------------------------------
# Overview (Tier 3)
# ---------------------------------------------------------------------------


def test_overview_returns_counts(client: TestClient) -> None:
    r = client.get("/overview")
    assert r.status_code == 200
    body = r.json()
    assert body["total_casualties"] >= 0
    assert isinstance(body["by_priority"], dict)
    assert 0.0 <= body["avg_confidence"] <= 1.0
    assert body["mission_priority"] in {"escalate", "sustain", "wind_down"}
    assert body["n_medic_assignments"] >= 0
    assert body["n_unresolved_regions"] >= 0


def test_overview_by_priority_sums_to_total(client: TestClient) -> None:
    body = client.get("/overview").json()
    assert sum(body["by_priority"].values()) == body["total_casualties"]


# ---------------------------------------------------------------------------
# Marker codec (Tier 3)
# ---------------------------------------------------------------------------


def test_marker_returns_qr_payload(client: TestClient) -> None:
    r = client.get("/casualties/C1/marker")
    assert r.status_code == 200
    body = r.json()
    assert body["casualty_id"] == "C1"
    assert len(body["qr_payload"]) == body["qr_chars"]
    assert body["envelope_bytes"] > 0
    # QR-safe base64 is a subset of [A-Za-z0-9-_=].
    assert all(c.isalnum() or c in "-_=" for c in body["qr_payload"])


def test_marker_404(client: TestClient) -> None:
    assert client.get("/casualties/UNKNOWN/marker").status_code == 404


# ---------------------------------------------------------------------------
# Skeletal graph (Final)
# ---------------------------------------------------------------------------


def test_skeletal_returns_topology_plus_latest(client: TestClient) -> None:
    r = client.get("/casualties/C1/skeletal")
    assert r.status_code == 200
    body = r.json()
    assert body["casualty_id"] == "C1"
    assert len(body["joints"]) == 13
    assert len(body["bones"]) == 12
    assert len(body["mirror_pairs"]) == 5
    assert body["latest"] is not None
    assert "t" in body["latest"]
    assert "joints" in body["latest"]
    assert "wounds" in body["latest"]


def test_skeletal_trends_cover_all_joints(client: TestClient) -> None:
    body = client.get("/casualties/C1/skeletal").json()
    assert set(body["trends"]) == set(body["joints"])
    for joint_name, trend in body["trends"].items():
        assert trend["joint"] == joint_name
        assert 0.0 <= trend["motion_score"] <= 1.0
        assert 0.0 <= trend["wound_mean"] <= 1.0


def test_skeletal_immediate_has_asymmetry(client: TestClient) -> None:
    """The seed biases the 'immediate' casualty toward L/R asymmetry
    (right side moves, left side still). Assert the asymmetry
    detection picks up on at least one mirror pair."""
    body = client.get("/casualties/C1/skeletal").json()
    motion_asymmetries = [r["motion_asymmetry"] for r in body["asymmetries"]]
    assert any(a > 0.2 for a in motion_asymmetries), (
        f"expected L/R motion asymmetry on at least one pair, got "
        f"{motion_asymmetries}"
    )


def test_skeletal_404(client: TestClient) -> None:
    assert client.get("/casualties/UNKNOWN/skeletal").status_code == 404


# ---------------------------------------------------------------------------
# Active sensing (Final)
# ---------------------------------------------------------------------------


def test_sensing_ranked_returns_list(client: TestClient) -> None:
    r = client.get("/sensing/ranked")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["recommendations"], list)
    assert body["total"] == len(body["recommendations"])


def test_sensing_ranked_sorted_by_info_gain(client: TestClient) -> None:
    body = client.get("/sensing/ranked").json()
    gains = [r["expected_info_gain"] for r in body["recommendations"]]
    assert gains == sorted(gains, reverse=True)


def test_sensing_top_k_limits_recommendations(client: TestClient) -> None:
    body = client.get("/sensing/ranked?top_k=2").json()
    assert len(body["recommendations"]) <= 2


def test_sensing_top_recommendation_matches_first(client: TestClient) -> None:
    body = client.get("/sensing/ranked").json()
    if body["recommendations"]:
        assert body["top_recommendation"] == body["recommendations"][0]
    else:
        assert body["top_recommendation"] is None


def test_sensing_recommendation_has_factorised_score(client: TestClient) -> None:
    """info_gain = uncertainty × priority_weight × novelty."""
    body = client.get("/sensing/ranked").json()
    for rec in body["recommendations"]:
        expected = rec["uncertainty"] * rec["priority_weight"] * rec["novelty"]
        assert rec["expected_info_gain"] == pytest.approx(expected, abs=5e-3)
