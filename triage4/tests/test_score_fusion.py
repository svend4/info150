from triage4.core.models import CasualtySignature
from triage4.triage_reasoning.rapid_triage import RapidTriageEngine
from triage4.triage_reasoning.score_fusion import (
    DEFAULT_WEIGHTS,
    fuse_triage_score,
    priority_from_score,
    signature_to_score_vector,
)


def _critical_signature() -> CasualtySignature:
    return CasualtySignature(
        breathing_curve=[0.01, 0.02, 0.01, 0.02],
        chest_motion_fd=0.08,
        perfusion_drop_score=0.82,
        bleeding_visual_score=0.91,
        posture_instability_score=0.75,
    )


def test_signature_to_score_vector_keys():
    sv = signature_to_score_vector(_critical_signature())
    assert set(sv.scores) == {"bleeding", "chest_motion", "perfusion", "posture"}
    for v in sv.scores.values():
        assert 0.0 <= v <= 1.0


def test_fused_score_for_critical_is_high():
    cs = fuse_triage_score(_critical_signature())
    assert cs.score >= 0.65
    assert priority_from_score(cs.score) == "immediate"
    assert set(cs.contributions) == {"bleeding", "chest_motion", "perfusion", "posture"}


def test_fused_score_for_benign_is_low():
    sig = CasualtySignature(
        breathing_curve=[0.30, 0.32, 0.31, 0.29],
        chest_motion_fd=0.33,
        perfusion_drop_score=0.10,
        bleeding_visual_score=0.05,
    )
    cs = fuse_triage_score(sig)
    assert cs.score < 0.35
    assert priority_from_score(cs.score) == "minimal"


def test_rapid_triage_engine_uses_fusion():
    engine = RapidTriageEngine()
    priority, score, reasons = engine.infer_priority(_critical_signature())
    assert priority == "immediate"
    assert score >= 0.65
    assert "possible severe hemorrhage" in reasons


def test_custom_weights_change_outcome():
    # If we weight posture very heavily and zero bleeding, a bleeding-only case
    # should become delayed instead of immediate.
    sig = CasualtySignature(
        breathing_curve=[0.30] * 4,
        chest_motion_fd=0.30,
        perfusion_drop_score=0.10,
        bleeding_visual_score=0.95,
        posture_instability_score=0.05,
    )
    cs = fuse_triage_score(
        sig,
        weights={"bleeding": 0.0, "chest_motion": 0.0, "perfusion": 0.0, "posture": 1.0},
    )
    assert cs.score == 0.05
    assert priority_from_score(cs.score) == "minimal"


def test_default_weights_sum_is_positive():
    assert sum(DEFAULT_WEIGHTS.values()) > 0.0
