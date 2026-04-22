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


def test_larrey_vs_rapid_triage_scored_through_gate2_documents_gap():
    """Running both classifiers through Gate 2 surfaces a documented gap.

    Larrey (1797) flags isolated heavy bleeding as ``immediate`` because
    a single mortal sign is enough. The modern ``RapidTriageEngine``
    uses weighted fusion across all signatures — so isolated strong
    bleeding with zero chest-motion / perfusion channels only reaches
    the ``delayed`` band. This is exactly the kind of baseline
    comparison idea #4 was designed to surface; we preserve the
    finding here so regressions are visible.
    """
    scene = [
        ("C1", CasualtySignature(bleeding_visual_score=0.9), "immediate"),
        ("C2", CasualtySignature(bleeding_visual_score=0.45), "delayed"),
        ("C3", CasualtySignature(), "minimal"),
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

    # Larrey baseline: perfect on this simple scene — a mortal sign is enough.
    assert r_larrey.accuracy == 1.0
    assert r_larrey.critical_miss_rate == 0.0

    # Modern engine: misses isolated strong bleeding as an immediate
    # because its score-fusion weights (~0.45 for bleeding) cannot cross
    # the 0.65 immediate threshold without help from another channel.
    # This is a known calibration gap tracked via this test.
    assert r_rapid.critical_miss_rate == 1.0
    assert r_rapid.accuracy <= r_larrey.accuracy
