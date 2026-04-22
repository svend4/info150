import pytest

from triage4.core.models import CasualtySignature
from triage4.evaluation import evaluate_gate2
from triage4.triage_reasoning import LarreyBaselineTriage, RapidTriageEngine


def test_larrey_validates_thresholds():
    with pytest.raises(ValueError):
        LarreyBaselineTriage(heavy_bleeding=1.5)
    with pytest.raises(ValueError):
        LarreyBaselineTriage(absent_motion=-0.1)


def test_larrey_heavy_bleeding_is_immediate():
    sig = CasualtySignature(bleeding_visual_score=0.9)
    assert LarreyBaselineTriage().classify(sig) == "immediate"


def test_larrey_unresponsive_posture_is_immediate():
    sig = CasualtySignature(posture_instability_score=0.85)
    assert LarreyBaselineTriage().classify(sig) == "immediate"


def test_larrey_absent_chest_motion_is_immediate():
    sig = CasualtySignature(
        breathing_curve=[0.01, 0.01, 0.01, 0.01],
        chest_motion_fd=0.03,
    )
    assert LarreyBaselineTriage().classify(sig) == "immediate"


def test_larrey_short_breathing_curve_does_not_trigger_mortal():
    # Only 2 samples → insufficient observation, Larrey would wait.
    sig = CasualtySignature(
        breathing_curve=[0.01, 0.01],
        chest_motion_fd=0.03,
    )
    # No mortal signs without enough breathing observation, no serious
    # signs either → minimal.
    assert LarreyBaselineTriage().classify(sig) == "minimal"


def test_larrey_moderate_bleeding_is_delayed():
    sig = CasualtySignature(bleeding_visual_score=0.45)
    assert LarreyBaselineTriage().classify(sig) == "delayed"


def test_larrey_pale_and_upright_is_delayed():
    sig = CasualtySignature(
        bleeding_visual_score=0.0,
        perfusion_drop_score=0.6,
        posture_instability_score=0.4,
    )
    assert LarreyBaselineTriage().classify(sig) == "delayed"


def test_larrey_no_signs_is_minimal():
    sig = CasualtySignature()
    assert LarreyBaselineTriage().classify(sig) == "minimal"


def test_classify_with_reasons_returns_signs():
    sig = CasualtySignature(
        bleeding_visual_score=0.9,
        posture_instability_score=0.85,
    )
    priority, reasons = LarreyBaselineTriage().classify_with_reasons(sig)
    assert priority == "immediate"
    assert any("bleeding" in r for r in reasons)
    assert any("collapsed" in r or "unresponsive" in r for r in reasons)


def test_minimal_with_reasons_gives_null_statement():
    priority, reasons = LarreyBaselineTriage().classify_with_reasons(
        CasualtySignature()
    )
    assert priority == "minimal"
    assert reasons == ["no visible distress"]


def test_larrey_vs_rapid_triage_critical_gap_closed():
    """Phase 9a's critical gap — isolated mortal signs — is now closed.

    Phase 9a documented that isolated heavy bleeding slipped through
    ``RapidTriageEngine`` as ``delayed`` because the weighted-fusion
    score (0.9 × 0.45 ≈ 0.4) never crossed the 0.65 immediate threshold.
    Phase 9b adds a mortal-sign override in
    ``score_fusion.priority_from_score`` that forces ``immediate`` when
    any single channel crosses its mortal threshold — the Larrey
    decision principle translated into the modern engine.

    This test verifies the critical-miss case only. Minor per-class
    disagreements on the delayed/minimal boundary are out of scope and
    tracked separately (they are not life-threatening).
    """
    scene = [
        ("C1", CasualtySignature(bleeding_visual_score=0.9), "immediate"),
        ("C2", CasualtySignature(chest_motion_fd=0.05,
                                 breathing_curve=[0.01] * 6), "immediate"),
        ("C3", CasualtySignature(posture_instability_score=0.9), "immediate"),
        ("C4", CasualtySignature(), "minimal"),
    ]
    larrey = LarreyBaselineTriage()
    rapid = RapidTriageEngine()

    larrey_preds = [(cid, larrey.classify(sig)) for cid, sig, _ in scene]
    rapid_preds = [
        (cid, rapid.infer_priority(sig)[0]) for cid, sig, _ in scene
    ]
    truths = [(cid, p) for cid, _, p in scene]

    r_larrey = evaluate_gate2(larrey_preds, truths)
    r_rapid = evaluate_gate2(rapid_preds, truths)

    # Both must hit zero critical misses — that's the life-vs-death metric.
    assert r_larrey.critical_miss_rate == 0.0
    assert r_rapid.critical_miss_rate == 0.0
    # And both must correctly spot every isolated-mortal-sign case as immediate.
    for cid, label in rapid_preds[:3]:
        assert label == "immediate", (
            f"{cid} should be immediate by mortal-sign override, got {label}"
        )


def test_mortal_sign_override_reason_surfaced():
    """The operator must see why priority jumped above the fused score."""
    rapid = RapidTriageEngine()
    sig = CasualtySignature(bleeding_visual_score=0.9)
    priority, score, reasons = rapid.infer_priority(sig)
    assert priority == "immediate"
    # Fused score is only ~0.4 — so the jump must be annotated.
    assert score < 0.65
    assert any("mortal-sign override" in r for r in reasons)
