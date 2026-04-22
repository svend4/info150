"""Tests for Phase 9e speculative trio.

Covers:
- ``integrations.marker_codec`` — encode / decode / tamper / replay;
- ``triage_reasoning.celegans_net`` — priority correctness on synthetic
  scenarios, auditability (small, fixed weight count);
- ``mission_coordination.mission_triage`` — signature derivation from
  graph state and priority-band boundaries.
"""

from __future__ import annotations

import time

import pytest

from triage4.core.models import (
    CasualtyNode,
    CasualtySignature,
    GeoPose,
    TraumaHypothesis,
)
from triage4.graph.casualty_graph import CasualtyGraph
from triage4.graph.mission_graph import MissionGraph
from triage4.integrations import (
    InvalidMarker,
    MarkerPayload,
    decode_marker,
    encode_marker,
    from_qr_string,
    marker_to_node,
    to_qr_string,
)
from triage4.mission_coordination import (
    MissionSignature,
    classify_mission,
    compute_mission_signature,
    triage_mission,
)
from triage4.triage_reasoning import CelegansTriageNet


# ---------------------------------------------------------------------------
# marker_codec
# ---------------------------------------------------------------------------


def _sample_node() -> CasualtyNode:
    return CasualtyNode(
        id="C7",
        location=GeoPose(x=5.5, y=-2.1, z=0.3),
        platform_source="uav:alpha",
        confidence=0.77,
        status="assessed",
        hypotheses=[
            TraumaHypothesis(kind="hemorrhage_major", score=0.91),
            TraumaHypothesis(kind="shock", score=0.52),
        ],
        triage_priority="immediate",
        first_seen_ts=100.0,
        last_seen_ts=120.5,
    )


def test_marker_roundtrip_preserves_core_fields():
    secret = b"mission_key_2026"
    node = _sample_node()

    marker = encode_marker(node, secret=secret, medic="alpha", now_ts=200.0)
    payload = decode_marker(marker, secret=secret, now_ts=200.0)

    assert payload.casualty_id == "C7"
    assert payload.priority == "immediate"
    assert payload.confidence == pytest.approx(0.77, abs=1e-3)
    assert payload.x == pytest.approx(5.5, abs=1e-2)
    assert payload.y == pytest.approx(-2.1, abs=1e-2)
    assert payload.medic == "alpha"
    assert len(payload.hypotheses) == 2
    assert payload.hypotheses[0]["kind"] == "hemorrhage_major"


def test_marker_qr_string_roundtrip():
    secret = b"mission_key_2026"
    marker = encode_marker(_sample_node(), secret=secret, now_ts=200.0)
    qr = to_qr_string(marker)
    assert qr == qr.strip()
    assert "=" not in qr.rstrip("=")  # urlsafe, minimal padding
    assert from_qr_string(qr) == marker


def test_marker_rejects_tampered_payload():
    secret = b"mission_key_2026"
    marker = bytearray(encode_marker(_sample_node(), secret=secret, now_ts=200.0))
    # Flip a byte inside the JSON envelope to trigger HMAC mismatch.
    marker[30] ^= 0x01
    with pytest.raises(InvalidMarker):
        decode_marker(bytes(marker), secret=secret, now_ts=200.0)


def test_marker_rejects_wrong_secret():
    marker = encode_marker(_sample_node(), secret=b"key_A_12345", now_ts=200.0)
    with pytest.raises(InvalidMarker):
        decode_marker(marker, secret=b"key_B_12345", now_ts=200.0)


def test_marker_rejects_stale_marker():
    secret = b"mission_key_2026"
    marker = encode_marker(_sample_node(), secret=secret, now_ts=100.0)
    # A day and a half later — over the default 24 h window.
    with pytest.raises(InvalidMarker):
        decode_marker(
            marker, secret=secret, now_ts=100.0 + 36 * 3600.0, max_age_s=24 * 3600.0,
        )


def test_marker_accepts_fresh_marker_in_window():
    secret = b"mission_key_2026"
    marker = encode_marker(_sample_node(), secret=secret, now_ts=100.0)
    # 10 minutes later — well within the window.
    payload = decode_marker(marker, secret=secret, now_ts=700.0)
    assert payload.casualty_id == "C7"


def test_marker_disables_age_check_when_max_age_zero():
    secret = b"mission_key_2026"
    marker = encode_marker(_sample_node(), secret=secret, now_ts=100.0)
    payload = decode_marker(
        marker, secret=secret, now_ts=100.0 + 10 * 24 * 3600.0, max_age_s=0.0,
    )
    assert payload.casualty_id == "C7"


def test_marker_rejects_short_secret():
    with pytest.raises(ValueError):
        encode_marker(_sample_node(), secret=b"short")


def test_marker_reconstructs_casualty_node():
    secret = b"mission_key_2026"
    marker = encode_marker(_sample_node(), secret=secret, medic="bravo", now_ts=200.0)
    payload = decode_marker(marker, secret=secret, now_ts=200.0)
    node = marker_to_node(payload)

    assert isinstance(node, CasualtyNode)
    assert node.id == "C7"
    assert node.triage_priority == "immediate"
    assert node.location.x == pytest.approx(5.5, abs=1e-2)
    assert node.assigned_medic == "bravo"
    assert [h.kind for h in node.hypotheses] == ["hemorrhage_major", "shock"]
    assert node.platform_source.startswith("marker:")


def test_marker_invalid_version_raises():
    with pytest.raises(InvalidMarker):
        MarkerPayload(
            casualty_id="C1", priority="immediate", confidence=0.5,
            x=0.0, y=0.0, z=0.0, version=999,
        )


def test_marker_fits_qr_budget():
    """A realistic 3-hypothesis node must fit comfortably in QR version 10."""
    secret = b"mission_key_2026"
    node = _sample_node()
    node.hypotheses.append(TraumaHypothesis(kind="pain", score=0.44))
    marker = encode_marker(node, secret=secret, medic="alpha", now_ts=200.0)
    qr = to_qr_string(marker)
    assert len(qr) < 800  # QR v10 medium ≈ 2 KB; we leave plenty of slack.


# ---------------------------------------------------------------------------
# celegans_net
# ---------------------------------------------------------------------------


def test_celegans_classifies_heavy_bleeding_as_immediate():
    sig = CasualtySignature(
        bleeding_visual_score=0.9,
        breathing_curve=[0.2] * 6,
        chest_motion_fd=0.7,
    )
    assert CelegansTriageNet().classify(sig) == "immediate"


def test_celegans_classifies_weak_chest_motion_as_immediate():
    sig = CasualtySignature(
        breathing_curve=[0.01] * 6,
        chest_motion_fd=0.05,
    )
    assert CelegansTriageNet().classify(sig) == "immediate"


def test_celegans_classifies_quiet_casualty_as_minimal():
    sig = CasualtySignature(
        bleeding_visual_score=0.0,
        breathing_curve=[0.3] * 6,
        chest_motion_fd=0.8,
        perfusion_drop_score=0.0,
        posture_instability_score=0.0,
    )
    assert CelegansTriageNet().classify(sig) == "minimal"


def test_celegans_activate_returns_all_layers():
    sig = CasualtySignature(bleeding_visual_score=0.9)
    act = CelegansTriageNet().activate(sig)

    assert set(act.sensory) == {"bleeding", "motion_risk", "perfusion", "posture"}
    assert len(act.interneuron) == 6
    assert set(act.motor) == {"immediate", "delayed", "minimal"}
    # Softmax sums to 1 and stays in [0, 1].
    assert abs(sum(act.motor.values()) - 1.0) < 1e-9
    for v in act.motor.values():
        assert 0.0 <= v <= 1.0


def test_celegans_is_auditable_small():
    """The whole point of the C.elegans pattern: few, inspectable parameters."""
    n = CelegansTriageNet.n_parameters()
    # 4 sensory × 6 interneurons + 6 interneurons × 3 motor + 3 motor biases
    # = 24 + 18 + 3 = 45.
    assert n == 45


def test_celegans_deterministic():
    sig = CasualtySignature(bleeding_visual_score=0.6, perfusion_drop_score=0.5)
    net = CelegansTriageNet()
    a = net.activate(sig)
    b = net.activate(sig)
    assert a.priority == b.priority
    assert a.motor == b.motor


# ---------------------------------------------------------------------------
# mission_triage
# ---------------------------------------------------------------------------


def _node_with_priority(node_id: str, priority: str) -> CasualtyNode:
    return CasualtyNode(
        id=node_id,
        location=GeoPose(x=0.0, y=0.0),
        platform_source="test",
        confidence=0.8,
        status="assessed",
        triage_priority=priority,
    )


def test_mission_signature_validates_channels():
    with pytest.raises(ValueError):
        MissionSignature(
            casualty_density=1.5,
            immediate_fraction=0.3,
            unresolved_sector_fraction=0.1,
            medic_utilisation=0.5,
            time_budget_burn=0.2,
        )


def test_compute_mission_signature_from_graphs():
    cg = CasualtyGraph()
    cg.upsert(_node_with_priority("C1", "immediate"))
    cg.upsert(_node_with_priority("C2", "immediate"))
    cg.upsert(_node_with_priority("C3", "delayed"))
    cg.upsert(_node_with_priority("C4", "minimal"))

    mg = MissionGraph()
    mg.assign_medic("m1", "C1")
    mg.assign_medic("m2", "C2")
    mg.mark_unresolved("sector-north")

    sig = compute_mission_signature(
        cg, mg,
        platform_capacity=10,
        n_medics=3,
        elapsed_minutes=30.0,
        mission_window_minutes=60.0,
    )
    assert sig.casualty_density == pytest.approx(0.4, abs=1e-3)
    assert sig.immediate_fraction == pytest.approx(0.5, abs=1e-3)
    assert sig.medic_utilisation == pytest.approx(2 / 3, abs=1e-3)
    assert sig.time_budget_burn == pytest.approx(0.5, abs=1e-3)
    assert 0.0 < sig.unresolved_sector_fraction <= 1.0


def test_compute_mission_signature_handles_empty_graphs():
    sig = compute_mission_signature(
        CasualtyGraph(), MissionGraph(),
        platform_capacity=5, n_medics=2,
        elapsed_minutes=0.0, mission_window_minutes=30.0,
    )
    assert sig.casualty_density == 0.0
    assert sig.immediate_fraction == 0.0
    assert sig.unresolved_sector_fraction == 0.0
    assert sig.medic_utilisation == 0.0
    assert sig.time_budget_burn == 0.0


def test_compute_mission_signature_rejects_bad_capacity():
    with pytest.raises(ValueError):
        compute_mission_signature(CasualtyGraph(), MissionGraph(), platform_capacity=0)
    with pytest.raises(ValueError):
        compute_mission_signature(CasualtyGraph(), MissionGraph(), n_medics=0)
    with pytest.raises(ValueError):
        compute_mission_signature(
            CasualtyGraph(), MissionGraph(), mission_window_minutes=0,
        )


def test_classify_mission_escalates_under_pressure():
    sig = MissionSignature(
        casualty_density=0.9,
        immediate_fraction=0.8,
        unresolved_sector_fraction=0.7,
        medic_utilisation=0.95,
        time_budget_burn=0.7,
    )
    result = classify_mission(sig)
    assert result.priority == "escalate"
    assert "immediate casualties dominate the queue" in result.reasons
    assert "medic team saturated" in result.reasons
    assert 0.0 <= result.score <= 1.0


def test_classify_mission_sustains_in_mid_band():
    sig = MissionSignature(
        casualty_density=0.4,
        immediate_fraction=0.3,
        unresolved_sector_fraction=0.3,
        medic_utilisation=0.4,
        time_budget_burn=0.4,
    )
    result = classify_mission(sig)
    assert result.priority == "sustain"


def test_classify_mission_winds_down_when_quiet():
    sig = MissionSignature(
        casualty_density=0.1,
        immediate_fraction=0.0,
        unresolved_sector_fraction=0.0,
        medic_utilisation=0.1,
        time_budget_burn=0.1,
    )
    result = classify_mission(sig)
    assert result.priority == "wind_down"
    assert result.reasons == []


def test_classify_mission_rejects_zero_weights():
    sig = MissionSignature(0.5, 0.5, 0.5, 0.5, 0.5)
    with pytest.raises(ValueError):
        classify_mission(sig, weights={k: 0.0 for k in (
            "casualty_density",
            "immediate_fraction",
            "unresolved_sector_fraction",
            "medic_utilisation",
            "time_budget_burn",
        )})


def test_classify_mission_contributions_sum_to_score():
    sig = MissionSignature(0.6, 0.4, 0.5, 0.3, 0.2)
    result = classify_mission(sig)
    # Contributions are normalised by total weight, so they sum to the score.
    assert abs(sum(result.contributions.values()) - result.score) < 1e-3


def test_triage_mission_one_call_helper():
    cg = CasualtyGraph()
    for i, prio in enumerate(["immediate", "immediate", "immediate", "delayed"]):
        cg.upsert(_node_with_priority(f"C{i}", prio))
    mg = MissionGraph()
    mg.assign_medic("m1", "C0")
    mg.assign_medic("m2", "C1")
    mg.assign_medic("m3", "C2")

    sig, result = triage_mission(
        cg, mg,
        platform_capacity=8, n_medics=3,
        elapsed_minutes=55.0, mission_window_minutes=60.0,
    )
    assert result.priority == "escalate"
    assert sig.time_budget_burn > 0.9
    assert sig.medic_utilisation == pytest.approx(1.0, abs=1e-3)


# ---------------------------------------------------------------------------
# cross-module smoke: marker from C.elegans-classified node
# ---------------------------------------------------------------------------


def test_marker_roundtrips_celegans_classified_node():
    sig = CasualtySignature(
        bleeding_visual_score=0.85,
        breathing_curve=[0.2] * 6,
        chest_motion_fd=0.6,
    )
    prio = CelegansTriageNet().classify(sig)
    node = CasualtyNode(
        id="C42",
        location=GeoPose(x=1.0, y=2.0),
        platform_source="uav:beta",
        confidence=0.72,
        status="assessed",
        triage_priority=prio,
    )
    secret = b"phase9e_test_secret"
    now = time.time()
    payload = decode_marker(
        encode_marker(node, secret=secret, now_ts=now),
        secret=secret, now_ts=now,
    )
    assert payload.priority == prio
