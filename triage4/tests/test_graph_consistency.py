from triage4.core.models import CasualtyNode, GeoPose
from triage4.graph.casualty_graph import CasualtyGraph
from triage4.graph.mission_graph import MissionGraph
from triage4.state_graph import check_casualty_graph_consistency


def _node(
    cid: str,
    priority: str = "immediate",
    confidence: float = 0.9,
) -> CasualtyNode:
    return CasualtyNode(
        id=cid,
        location=GeoPose(x=10.0, y=20.0),
        platform_source="uav",
        confidence=confidence,
        status="assessed",
        triage_priority=priority,
    )


def test_clean_graph_is_consistent():
    graph = CasualtyGraph()
    graph.upsert(_node("C1"))
    graph.link("uav", "observed", "C1")

    mission = MissionGraph()
    mission.assign_medic("medic_1", "C1")

    report = check_casualty_graph_consistency(graph, mission)
    assert report.is_consistent
    assert report.n_errors == 0


def test_immediate_without_handoff_is_error():
    graph = CasualtyGraph()
    graph.upsert(_node("C1", priority="immediate"))
    mission = MissionGraph()

    report = check_casualty_graph_consistency(graph, mission)
    codes = {i.code for i in report.issues}
    assert "IMMEDIATE_WITHOUT_HANDOFF" in codes
    assert report.n_errors >= 1


def test_low_confidence_is_warning():
    graph = CasualtyGraph()
    graph.upsert(_node("C1", priority="minimal", confidence=0.2))

    report = check_casualty_graph_consistency(graph, min_confidence=0.4)
    codes = {i.code for i in report.issues}
    assert "LOW_CONFIDENCE" in codes


def test_orphan_edge_is_warning():
    graph = CasualtyGraph()
    graph.upsert(_node("C1", priority="minimal"))
    # Edge pointing at unknown casualty C9 — should be flagged as orphan.
    graph.link("C1", "supports", "C9")

    report = check_casualty_graph_consistency(graph)
    codes = {i.code for i in report.issues}
    assert "ORPHAN_EDGE" in codes


def test_double_medic_assignment_is_error():
    graph = CasualtyGraph()
    graph.upsert(_node("C1", priority="immediate"))

    mission = MissionGraph()
    mission.assign_medic("medic_1", "C1")
    mission.assign_medic("medic_2", "C1")

    report = check_casualty_graph_consistency(graph, mission)
    codes = {i.code for i in report.issues}
    assert "DOUBLE_HANDOFF" in codes
    assert report.n_errors >= 1
