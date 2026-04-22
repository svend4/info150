import pytest

from triage4.autonomy import ActiveSensingPlanner, SensingRecommendation
from triage4.core.models import CasualtyNode, GeoPose
from triage4.state_graph import EvidenceMemory


def _node(cid: str, priority: str, confidence: float) -> CasualtyNode:
    return CasualtyNode(
        id=cid,
        location=GeoPose(x=0.0, y=0.0),
        platform_source="uav",
        confidence=confidence,
        status="assessed",
        triage_priority=priority,
    )


def test_empty_list_returns_empty_ranking():
    planner = ActiveSensingPlanner()
    assert planner.rank([]) == []
    assert planner.recommend_next([]) is None


def test_high_uncertainty_ranked_first():
    planner = ActiveSensingPlanner()
    nodes = [
        _node("C1", "immediate", confidence=0.95),  # low uncertainty
        _node("C2", "immediate", confidence=0.40),  # high uncertainty
    ]
    ranked = planner.rank(nodes)
    assert ranked[0].casualty_id == "C2"


def test_priority_weights_ranking():
    planner = ActiveSensingPlanner()
    nodes = [
        _node("C1", "minimal", confidence=0.5),
        _node("C2", "immediate", confidence=0.5),
    ]
    ranked = planner.rank(nodes)
    assert ranked[0].casualty_id == "C2"


def test_novelty_drops_with_observation_count():
    planner = ActiveSensingPlanner()
    memory = EvidenceMemory()
    # Record many observations of C1, zero of C2.
    for _ in range(10):
        memory.record("observation", "C1", {})
    nodes = [
        _node("C1", "immediate", confidence=0.5),
        _node("C2", "immediate", confidence=0.5),
    ]
    ranked = planner.rank(nodes, memory=memory)
    assert ranked[0].casualty_id == "C2"
    c2_rec = next(r for r in ranked if r.casualty_id == "C2")
    c1_rec = next(r for r in ranked if r.casualty_id == "C1")
    assert c2_rec.novelty > c1_rec.novelty


def test_recommend_next_returns_top():
    planner = ActiveSensingPlanner()
    nodes = [
        _node("C1", "minimal", confidence=0.9),
        _node("C2", "immediate", confidence=0.3),
    ]
    top = planner.recommend_next(nodes)
    assert isinstance(top, SensingRecommendation)
    assert top.casualty_id == "C2"


def test_top_k_caps_result():
    planner = ActiveSensingPlanner()
    nodes = [_node(f"C{i}", "delayed", confidence=0.5) for i in range(5)]
    top = planner.top_k(nodes, k=2)
    assert len(top) == 2


def test_top_k_invalid_k_raises():
    with pytest.raises(ValueError):
        ActiveSensingPlanner().top_k([], k=0)


def test_recommendation_exposes_reasons():
    planner = ActiveSensingPlanner()
    node = _node("C1", "immediate", confidence=0.2)
    rec = planner.recommend_next([node])
    assert rec is not None
    assert any("immediate" in r for r in rec.reasons)
    assert any("never observed" in r for r in rec.reasons)


def test_custom_priority_weights_override():
    # If we set minimal > immediate, minimal should rank higher.
    planner = ActiveSensingPlanner(
        priority_weights={
            "immediate": 0.1,
            "delayed": 0.5,
            "minimal": 1.0,
            "expectant": 0.1,
            "unknown": 0.5,
        }
    )
    nodes = [
        _node("C1", "immediate", confidence=0.5),
        _node("C2", "minimal", confidence=0.5),
    ]
    ranked = planner.rank(nodes)
    assert ranked[0].casualty_id == "C2"


def test_expected_info_gain_in_unit_range():
    planner = ActiveSensingPlanner()
    node = _node("C1", "immediate", confidence=0.2)
    rec = planner.recommend_next([node])
    assert rec is not None
    assert 0.0 <= rec.expected_info_gain <= 1.0
