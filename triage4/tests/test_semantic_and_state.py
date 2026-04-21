from triage4.core.models import CasualtySignature
from triage4.semantic.evidence_tokens import build_evidence_tokens
from triage4.state_graph.body_state_graph import BodyStateGraph
from triage4.triage_temporal.deterioration_model import DeteriorationModel
from triage4.triage_temporal.temporal_memory import TemporalMemory


def test_evidence_tokens_for_critical_signature():
    sig = CasualtySignature(
        breathing_curve=[0.01, 0.02, 0.01, 0.02],
        chest_motion_fd=0.08,
        perfusion_drop_score=0.82,
        bleeding_visual_score=0.91,
        posture_instability_score=0.75,
    )
    tokens = build_evidence_tokens(sig)
    names = {t.name for t in tokens}
    assert "possible_external_bleeding" in names
    assert "low_chest_motion" in names
    assert "poor_perfusion_pattern" in names
    assert "abnormal_body_posture" in names


def test_body_state_graph_aggregates_hypotheses():
    sig = CasualtySignature(
        chest_motion_fd=0.05,
        perfusion_drop_score=0.80,
        bleeding_visual_score=0.85,
    )
    tokens = build_evidence_tokens(sig)
    graph = BodyStateGraph()
    graph.ingest(tokens)

    ranked = dict(graph.ranked_hypotheses())
    assert "hemorrhage_risk" in ranked
    assert "respiratory_distress" in ranked
    assert ranked["hemorrhage_risk"] > 0.0


def test_temporal_memory_and_deterioration():
    memory = TemporalMemory(window=4)
    for s in [0.2, 0.3, 0.4, 0.5]:
        memory.push("C1", s)
    history = memory.history("C1")
    assert history == [0.2, 0.3, 0.4, 0.5]

    det = DeteriorationModel()
    assert det.trend(history) > 0
    assert det.revisit_recommended(history) is True
