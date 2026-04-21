from triage4.core.models import CasualtyNode, GeoPose
from triage4.graph.casualty_graph import CasualtyGraph
from triage4.graph.mission_graph import MissionGraph
from triage4.graph.updates import GraphUpdateService


def _node(casualty_id: str, priority: str, confidence: float = 0.8) -> CasualtyNode:
    return CasualtyNode(
        id=casualty_id,
        location=GeoPose(x=1.0, y=2.0),
        platform_source="uav",
        confidence=confidence,
        status="assessed",
        triage_priority=priority,
        assigned_robot="uav",
    )


def test_casualty_graph_upsert_and_immediate_sort():
    g = CasualtyGraph()
    g.upsert(_node("A", "delayed"))
    g.upsert(_node("B", "immediate", confidence=0.6))
    g.upsert(_node("C", "immediate", confidence=0.9))

    immediate = g.immediate_nodes()
    assert [n.id for n in immediate] == ["C", "B"]


def test_graph_update_service_links_robot_and_mission():
    cg = CasualtyGraph()
    mg = MissionGraph()
    service = GraphUpdateService(cg, mg)

    node = _node("A", "immediate")
    service.ingest_assessment(node)

    assert ("uav", "observed", "A") in cg.edges
    assert mg.robot_assignments["uav"] == "A"
