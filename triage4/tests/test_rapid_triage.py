from triage4.core.models import CasualtySignature
from triage4.triage_reasoning.rapid_triage import RapidTriageEngine


def test_immediate_priority():
    engine = RapidTriageEngine()
    sig = CasualtySignature(
        breathing_curve=[0.01, 0.02, 0.01, 0.02],
        chest_motion_fd=0.08,
        perfusion_drop_score=0.82,
        bleeding_visual_score=0.91,
    )
    priority, score, reasons = engine.infer_priority(sig)

    assert priority == "immediate"
    assert score >= 0.65
    assert reasons


def test_minimal_priority():
    engine = RapidTriageEngine()
    sig = CasualtySignature(
        breathing_curve=[0.30, 0.32, 0.31, 0.29],
        chest_motion_fd=0.33,
        perfusion_drop_score=0.20,
        bleeding_visual_score=0.05,
    )
    priority, score, _ = engine.infer_priority(sig)

    assert priority == "minimal"
    assert score < 0.35


def test_hypotheses_include_hemorrhage_when_bleeding_strong():
    engine = RapidTriageEngine()
    sig = CasualtySignature(
        breathing_curve=[0.3, 0.3, 0.3, 0.3],
        chest_motion_fd=0.3,
        perfusion_drop_score=0.2,
        bleeding_visual_score=0.9,
    )
    hypotheses = engine.build_hypotheses(sig)
    kinds = [h.kind for h in hypotheses]
    assert "hemorrhage" in kinds
