"""Phase 9c tests — Bayesian twin, counterfactual, entropy handoff,
CRDT graph, bioacoustic, LLM grounding."""

from __future__ import annotations

import numpy as np
import pytest

from triage4.core.models import CasualtyNode, CasualtySignature, GeoPose, TraumaHypothesis
from triage4.evaluation import (
    CounterfactualReport,
    evaluate_counterfactuals,
    score_counterfactuals,
)
from triage4.signatures import AcousticSignature, AcousticSignatureExtractor
from triage4.state_graph import CRDTCasualtyGraph
from triage4.triage_reasoning import (
    PatientTwinFilter,
    TemplateGroundingBackend,
    TwinPosterior,
    UncertaintyModel,
    build_prompt,
    explain,
)
from triage4.triage_temporal import EntropyHandoffTrigger


# ============================================================================
# Bayesian twin
# ============================================================================


def _immediate_sig() -> CasualtySignature:
    return CasualtySignature(
        breathing_curve=[0.01] * 6,
        chest_motion_fd=0.05,
        perfusion_drop_score=0.85,
        bleeding_visual_score=0.9,
        posture_instability_score=0.8,
    )


def _minimal_sig() -> CasualtySignature:
    return CasualtySignature(
        breathing_curve=[0.25] * 6,
        chest_motion_fd=0.35,
        perfusion_drop_score=0.10,
        bleeding_visual_score=0.05,
        posture_instability_score=0.05,
    )


def test_bayesian_twin_posterior_shape():
    tw = PatientTwinFilter(n_particles=100, seed=0)
    post = tw.posterior()
    assert isinstance(post, TwinPosterior)
    assert set(post.priority_probs) == {"immediate", "delayed", "minimal"}
    assert sum(post.priority_probs.values()) == pytest.approx(1.0, abs=1e-3)


def test_bayesian_twin_converges_on_immediate_signature():
    tw = PatientTwinFilter(n_particles=300, seed=0)
    for _ in range(6):
        post = tw.update(_immediate_sig())
    assert post.most_likely_priority == "immediate"
    assert post.most_likely_probability > 0.6


def test_bayesian_twin_converges_on_minimal_signature():
    tw = PatientTwinFilter(n_particles=300, seed=0)
    for _ in range(6):
        post = tw.update(_minimal_sig())
    assert post.most_likely_priority == "minimal"


def test_bayesian_twin_validation():
    with pytest.raises(ValueError):
        PatientTwinFilter(n_particles=1)
    with pytest.raises(ValueError):
        PatientTwinFilter(observation_sigma=0.0)


def test_bayesian_twin_effective_sample_size_tracked():
    tw = PatientTwinFilter(n_particles=200, seed=0)
    post = tw.update(_immediate_sig())
    assert 0.0 < post.effective_sample_size <= 200.0


# ============================================================================
# Counterfactual
# ============================================================================


def test_counterfactual_case_structure():
    c = score_counterfactuals(
        casualty_id="C1",
        true_severity="critical",
        actual_priority="delayed",
        actual_outcome=0.40,
    )
    assert c.casualty_id == "C1"
    assert set(c.counterfactuals) == {"immediate", "delayed", "minimal"}
    assert c.best_alternative == "immediate"
    assert c.regret > 0.0


def test_counterfactual_no_regret_when_optimal():
    c = score_counterfactuals(
        casualty_id="C1",
        true_severity="critical",
        actual_priority="immediate",
        actual_outcome=0.85,
    )
    assert c.regret == 0.0


def test_counterfactual_report_aggregates():
    records = [
        ("C1", "critical", "delayed", 0.40),
        ("C2", "light", "minimal", 0.95),
        ("C3", "serious", "minimal", 0.60),
    ]
    r = evaluate_counterfactuals(records)
    assert isinstance(r, CounterfactualReport)
    assert r.n_total == 3
    assert 0.0 <= r.mean_regret <= 1.0


def test_counterfactual_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        score_counterfactuals("C1", "unknown", "immediate", 0.5)
    with pytest.raises(ValueError):
        score_counterfactuals("C1", "critical", "bogus", 0.5)
    with pytest.raises(ValueError):
        score_counterfactuals("C1", "critical", "immediate", 2.0)
    with pytest.raises(ValueError):
        evaluate_counterfactuals([], regret_threshold=-0.1)


def test_counterfactual_empty_list_returns_zero_report():
    r = evaluate_counterfactuals([])
    assert r.n_total == 0
    assert r.mean_regret == 0.0


# ============================================================================
# Entropy handoff
# ============================================================================


def test_entropy_trigger_stable_priority_fires():
    trig = EntropyHandoffTrigger(
        window=6, min_observations=3, entropy_threshold=0.3
    )
    for _ in range(5):
        trig.observe("C1", "immediate")
    assert trig.should_handoff("C1") is True


def test_entropy_trigger_oscillating_priority_does_not_fire():
    trig = EntropyHandoffTrigger(window=6, min_observations=3, entropy_threshold=0.5)
    for i in range(6):
        trig.observe("C1", "immediate" if i % 2 == 0 else "delayed")
    assert trig.should_handoff("C1") is False


def test_entropy_trigger_needs_min_observations():
    trig = EntropyHandoffTrigger(min_observations=5)
    trig.observe("C1", "immediate")
    trig.observe("C1", "immediate")
    assert trig.should_handoff("C1") is False


def test_entropy_trigger_validates():
    with pytest.raises(ValueError):
        EntropyHandoffTrigger(window=1)
    with pytest.raises(ValueError):
        EntropyHandoffTrigger(min_observations=0)


def test_entropy_trigger_rejects_unknown_band():
    trig = EntropyHandoffTrigger()
    with pytest.raises(ValueError):
        trig.observe("C1", "bogus_band")


def test_entropy_signal_shape():
    trig = EntropyHandoffTrigger()
    sig = trig.observe("C1", "immediate")
    assert sig.casualty_id == "C1"
    assert 0.0 <= sig.entropy <= 3.0
    assert sig.n_observations == 1


# ============================================================================
# CRDT graph
# ============================================================================


def test_crdt_add_remove_orset():
    g = CRDTCasualtyGraph(replica_id="A")
    g.add_casualty("C1")
    g.add_casualty("C2")
    g.remove_casualty("C1")
    assert g.casualty_ids == {"C2"}


def test_crdt_merge_commutative():
    a = CRDTCasualtyGraph(replica_id="A")
    b = CRDTCasualtyGraph(replica_id="B")
    a.add_casualty("C1")
    b.add_casualty("C2")

    a_merged = CRDTCasualtyGraph(replica_id="A-merged")
    a_merged.merge(a)
    a_merged.merge(b)

    b_merged = CRDTCasualtyGraph(replica_id="B-merged")
    b_merged.merge(b)
    b_merged.merge(a)

    assert a_merged.casualty_ids == b_merged.casualty_ids == {"C1", "C2"}


def test_crdt_priority_lww_wins_by_timestamp():
    g = CRDTCasualtyGraph(replica_id="A")
    g.add_casualty("C1")
    g.set_priority("C1", "delayed", ts=100.0)

    other = CRDTCasualtyGraph(replica_id="B")
    other.add_casualty("C1")
    other.set_priority("C1", "immediate", ts=150.0)

    g.merge(other)
    assert g.get_priority("C1") == "immediate"


def test_crdt_observation_count_is_sum_across_replicas():
    a = CRDTCasualtyGraph(replica_id="A")
    b = CRDTCasualtyGraph(replica_id="B")
    a.add_casualty("C1")
    b.add_casualty("C1")
    for _ in range(3):
        a.increment_observation("C1")
    for _ in range(5):
        b.increment_observation("C1")
    a.merge(b)
    assert a.observation_count("C1") == 8


def test_crdt_snapshot_serialisable():
    g = CRDTCasualtyGraph(replica_id="A")
    g.add_casualty("C1")
    g.set_priority("C1", "immediate", ts=1.0)
    g.increment_observation("C1")
    snap = g.snapshot()
    assert snap["replica_id"] == "A"
    assert "C1" in snap["adds"]
    assert snap["priority"]["C1"]["value"] == "immediate"


# ============================================================================
# Bioacoustic
# ============================================================================


def _cough_like_audio(fs_hz: float = 8000.0, n: int = 2000, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    # Cough ≈ broadband noise burst.
    audio = rng.normal(0.0, 1.0, n)
    return audio


def _wheeze_like_audio(fs_hz: float = 8000.0, n: int = 2000) -> np.ndarray:
    t = np.arange(n) / fs_hz
    # 700 Hz tone.
    return np.sin(2 * np.pi * 700 * t)


def _silence(fs_hz: float = 8000.0, n: int = 2000) -> np.ndarray:
    return np.zeros(n)


def test_acoustic_silence_high_silence_score():
    ex = AcousticSignatureExtractor()
    result = ex.extract(_silence(), fs_hz=8000.0)
    assert isinstance(result, AcousticSignature)
    assert result.has_silence >= 0.9
    assert result.has_cough < 0.2


def test_acoustic_cough_detected():
    ex = AcousticSignatureExtractor()
    result = ex.extract(_cough_like_audio(), fs_hz=8000.0)
    assert result.has_cough > 0.2
    assert result.has_silence < 0.5


def test_acoustic_wheeze_detected():
    ex = AcousticSignatureExtractor()
    result = ex.extract(_wheeze_like_audio(), fs_hz=8000.0)
    assert result.has_wheeze > 0.5


def test_acoustic_short_or_low_sample_rate_returns_silence():
    ex = AcousticSignatureExtractor()
    short = ex.extract(np.zeros(5), fs_hz=8000.0)
    assert short.has_silence == 1.0
    low_fs = ex.extract(_wheeze_like_audio(n=2000), fs_hz=1000.0)
    assert low_fs.has_silence == 1.0


def test_acoustic_all_values_in_unit_range():
    ex = AcousticSignatureExtractor()
    result = ex.extract(_cough_like_audio(), fs_hz=8000.0)
    for v in (
        result.has_cough,
        result.has_wheeze,
        result.has_groan,
        result.has_silence,
        result.quality_score,
    ):
        assert 0.0 <= v <= 1.0


# ============================================================================
# LLM grounding
# ============================================================================


def _demo_node() -> CasualtyNode:
    return CasualtyNode(
        id="C7",
        location=GeoPose(x=85.0, y=45.0),
        platform_source="sim_uav",
        confidence=0.76,
        status="assessed",
        signatures=CasualtySignature(
            bleeding_visual_score=0.91,
            perfusion_drop_score=0.62,
            chest_motion_fd=0.08,
            breathing_curve=[0.01, 0.02, 0.01, 0.02],
        ),
        hypotheses=[
            TraumaHypothesis(kind="hemorrhage", score=0.91, explanation="heavy bleeding"),
            TraumaHypothesis(kind="respiratory_distress", score=0.78, explanation="weak chest motion"),
        ],
        triage_priority="immediate",
    )


def test_build_prompt_grounds_every_fact():
    node = _demo_node()
    prompt = build_prompt(node, triage_reasons=["possible severe hemorrhage"])
    assert prompt.facts["casualty_id"] == "C7"
    assert prompt.facts["priority"] == "immediate"
    assert prompt.facts["signatures"]["bleeding"] == 0.91
    assert len(prompt.facts["hypotheses"]) == 2
    # System message must forbid hallucination.
    assert "Do NOT add" in prompt.system


def test_build_prompt_optional_uncertainty_fields():
    node = _demo_node()
    sig_for_unc = CasualtySignature(
        visibility_score=0.9,
        raw_features={"breathing_quality": 0.85},
    )
    unc = UncertaintyModel().from_signature(sig_for_unc, base_score=0.7)
    prompt = build_prompt(node, ["a", "b"], uncertainty=unc)
    assert "overall_confidence" in prompt.facts
    assert "per_channel_confidence" in prompt.facts


def test_template_grounding_returns_readable_text():
    node = _demo_node()
    explanation = explain(
        node,
        triage_reasons=["possible severe hemorrhage", "weak chest motion"],
        backend=TemplateGroundingBackend(),
    )
    assert explanation.backend == "template"
    assert "C7" in explanation.sentence
    assert "immediate" in explanation.sentence
    assert "hemorrhage" in explanation.sentence


def test_template_grounding_no_reasons_gracefully():
    node_empty = CasualtyNode(
        id="C1",
        location=GeoPose(x=0.0, y=0.0),
        platform_source="",
        confidence=0.5,
        status="assessed",
        triage_priority="minimal",
    )
    explanation = explain(node_empty, triage_reasons=[])
    assert "C1" in explanation.sentence
    assert "minimal" in explanation.sentence


def test_explain_pluggable_backend():
    class FakeBackend:
        name = "fake"

        def complete(self, prompt):
            return f"FAKE[{prompt.facts['casualty_id']}]"

    explanation = explain(_demo_node(), triage_reasons=[], backend=FakeBackend())
    assert explanation.backend == "fake"
    assert explanation.sentence == "FAKE[C7]"
