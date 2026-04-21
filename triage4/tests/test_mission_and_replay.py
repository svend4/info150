from triage4.autonomy.task_allocator import TaskAllocator
from triage4.autonomy.human_handoff import HumanHandoffService
from triage4.core.models import CasualtyNode, GeoPose, TraumaHypothesis
from triage4.mission_coordination.assignment_engine import AssignmentEngine
from triage4.mission_coordination.task_queue import Task, TaskQueue
from triage4.world_replay.replay_engine import ReplayEngine
from triage4.world_replay.timeline_store import TimelineStore


def _node(cid: str, priority: str, x: float = 10.0, y: float = 10.0) -> CasualtyNode:
    return CasualtyNode(
        id=cid,
        location=GeoPose(x=x, y=y),
        platform_source="uav",
        confidence=0.8,
        status="assessed",
        triage_priority=priority,
        hypotheses=[TraumaHypothesis(kind="hemorrhage", score=0.9, explanation="test")],
    )


def test_task_allocator_orders_immediate_first():
    alloc = TaskAllocator()
    recs = alloc.recommend([_node("a", "delayed"), _node("b", "immediate"), _node("c", "minimal")])
    assert recs[0]["casualty_id"] == "b"


def test_human_handoff_payload_shape():
    handoff = HumanHandoffService()
    payload = handoff.package_for_medic(_node("a", "immediate"))
    assert payload["priority"] == "immediate"
    assert payload["recommended_action"] == "mediate_immediate_access"
    assert payload["top_hypotheses"]


def test_task_queue_dedup():
    q = TaskQueue()
    q.push(Task(casualty_id="a", kind="revisit", priority="immediate", confidence=0.8))
    q.push(Task(casualty_id="a", kind="revisit", priority="immediate", confidence=0.8))
    assert len(q) == 1


def test_assignment_engine_picks_nearest():
    engine = AssignmentEngine()
    casualties = [_node("a", "immediate", x=0.0, y=0.0)]
    agents = [
        {"id": "uav_far", "kind": "uav", "x": 100.0, "y": 100.0},
        {"id": "uav_near", "kind": "uav", "x": 1.0, "y": 1.0},
    ]
    assignments = engine.assign(casualties, agents)
    assert assignments[0]["agent_id"] == "uav_near"


def test_replay_engine_cycles_through_frames():
    store = TimelineStore()
    store.record(0.0, {"casualties": []})
    store.record(1.0, {"casualties": [{"id": "a"}]})
    engine = ReplayEngine(store)
    assert engine.next_frame()["t"] == 0.0
    assert engine.next_frame()["t"] == 1.0
    assert engine.next_frame()["t"] == 0.0  # wraps
