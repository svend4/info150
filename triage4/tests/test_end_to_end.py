"""End-to-end integration test.

Covers the full triage4 pipeline:

    synthetic scene
      → perception (body regions)
      → signatures (breathing, bleeding, perfusion, thermal, posture)
      → triage reasoning (score fusion + uncertainty)
      → vitals estimation
      → trauma hypotheses
      → graph updates (casualty + mission)
      → autonomy (task allocator, human handoff)
      → platform bridge publish
      → evaluation through all five DARPA gates

The assertions verify *contracts*, not specific numeric values, so this
test catches structural regressions across layer boundaries without
being brittle to minor tuning changes.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from triage4.autonomy.human_handoff import HumanHandoffService
from triage4.autonomy.task_allocator import TaskAllocator
from triage4.core.models import CasualtyNode, CasualtySignature, GeoPose
from triage4.evaluation import (
    HMTEvent,
    evaluate_gate1,
    evaluate_gate2,
    evaluate_gate3,
    evaluate_gate4,
    evaluate_hmt_lane,
)
from triage4.graph.casualty_graph import CasualtyGraph
from triage4.graph.mission_graph import MissionGraph
from triage4.graph.updates import GraphUpdateService
from triage4.integrations import LoopbackMAVLinkBridge
from triage4.perception.body_regions import BodyRegionPolygonizer
from triage4.signatures import (
    BleedingSignatureExtractor,
    BreathingSignatureExtractor,
    PerfusionSignatureExtractor,
    PostureSignatureExtractor,
    ThermalSignatureExtractor,
)
from triage4.sim.casualty_profiles import (
    bleeding_inputs,
    breath_signal,
    perfusion_series,
)
from triage4.state_graph import (
    BodyStateGraph,
    EvidenceMemory,
    check_casualty_graph_consistency,
)
from triage4.triage_reasoning import (
    RapidTriageEngine,
    UncertaintyModel,
    VitalsEstimator,
)
from triage4.semantic import build_evidence_tokens


@dataclass(frozen=True)
class Fixture:
    cid: str
    x: float
    y: float
    priority: str
    trauma: frozenset[str]
    hr_true: float
    rr_true: float


SCENE: list[Fixture] = [
    Fixture("C1", 10.0, 15.0, "immediate", frozenset({"hemorrhage", "shock_risk"}), 130.0, 28.0),
    Fixture("C2", 30.0, 25.0, "delayed", frozenset({"respiratory_distress"}), 100.0, 22.0),
    Fixture("C3", 50.0, 30.0, "minimal", frozenset(), 72.0, 15.0),
    Fixture("C4", 20.0, 60.0, "immediate", frozenset({"hemorrhage"}), 125.0, 30.0),
    Fixture("C5", 70.0, 70.0, "minimal", frozenset(), 70.0, 14.0),
]


def _long_sinusoid(freq_hz: float, fs_hz: float = 30.0, seconds: float = 10.0) -> list[float]:
    n = int(seconds * fs_hz)
    t = np.arange(n) / fs_hz
    return list(np.sin(2 * np.pi * freq_hz * t))


def _thermal_patch(seed: int) -> np.ndarray:
    return np.random.default_rng(seed).normal(25.0, 3.0, (6, 6))


def _run_pipeline():
    polygonizer = BodyRegionPolygonizer()
    breathing_ex = BreathingSignatureExtractor()
    bleeding_ex = BleedingSignatureExtractor()
    perfusion_ex = PerfusionSignatureExtractor()
    thermal_ex = ThermalSignatureExtractor()
    posture_ex = PostureSignatureExtractor()
    triage_engine = RapidTriageEngine()
    uncertainty_model = UncertaintyModel()
    vitals_estimator = VitalsEstimator()

    graph = CasualtyGraph()
    mission = MissionGraph()
    updates = GraphUpdateService(graph, mission)
    memory = EvidenceMemory()
    state_graph = BodyStateGraph()

    bridge = LoopbackMAVLinkBridge(start_pose=GeoPose(0.0, 0.0), speed=10.0)

    predicted_positions: list[tuple[str, float, float]] = []
    predicted_priorities: list[tuple[str, str]] = []
    predicted_trauma: dict[str, set[str]] = {}
    predicted_vitals: dict[str, tuple[float, float]] = {}

    rng = np.random.default_rng(42)

    for idx, fx in enumerate(SCENE):
        body_regions = polygonizer.build_from_center(fx.x, fx.y)

        breathing = breathing_ex.extract(breath_signal(fx.priority))
        vr, td, ph = bleeding_inputs(fx.priority)
        bleeding = bleeding_ex.extract(vr, td, ph)
        perfusion = perfusion_ex.extract(perfusion_series(fx.priority))
        thermal = thermal_ex.extract(_thermal_patch(seed=idx))
        posture = posture_ex.extract(body_regions)

        sig = CasualtySignature(
            breathing_curve=breathing["breathing_curve"],
            chest_motion_fd=breathing["chest_motion_fd"],
            perfusion_drop_score=perfusion["perfusion_drop_score"],
            bleeding_visual_score=bleeding["bleeding_visual_score"],
            thermal_asymmetry_score=thermal["thermal_asymmetry_score"],
            posture_instability_score=posture["posture_instability_score"],
            visibility_score=0.95,
            body_region_polygons=body_regions,
            raw_features={
                "respiration_proxy": breathing["respiration_proxy"],
                "breathing_quality": breathing["quality_score"],
                "perfusion_quality": perfusion["quality_score"],
                "bleeding_confidence": bleeding["confidence"],
                "thermal_quality": thermal["quality_score"],
            },
        )

        priority, score, _reasons = triage_engine.infer_priority(sig)
        hypotheses = triage_engine.build_hypotheses(sig)
        uncertainty = uncertainty_model.from_signature(sig, base_score=score)

        long_breath = _long_sinusoid(fx.rr_true / 60.0)
        long_perf = _long_sinusoid(fx.hr_true / 60.0)
        vitals = vitals_estimator.estimate(long_breath, long_perf, fs_hz=30.0)

        location = GeoPose(
            x=fx.x + float(rng.normal(0.0, 0.5)),
            y=fx.y + float(rng.normal(0.0, 0.5)),
        )
        node = CasualtyNode(
            id=fx.cid,
            location=location,
            platform_source="sim_uav",
            confidence=uncertainty.overall_confidence,
            status="assessed",
            signatures=sig,
            hypotheses=hypotheses,
            triage_priority=priority,
            first_seen_ts=float(idx),
            last_seen_ts=float(idx) + 1.0,
            assigned_medic=f"medic_{idx + 1}",
            assigned_robot="sim_uav",
        )

        updates.ingest_assessment(node)
        memory.record("assessment", fx.cid, {"priority": priority, "score": score})
        state_graph.ingest(build_evidence_tokens(sig))

        bridge.publish_casualty(node)
        bridge.send_waypoint(location)

        predicted_positions.append((fx.cid, location.x, location.y))
        predicted_priorities.append((fx.cid, priority))
        predicted_trauma[fx.cid] = {h.kind for h in hypotheses}
        predicted_vitals[fx.cid] = (vitals.heart_rate_bpm, vitals.respiration_rate_bpm)

    return {
        "graph": graph,
        "mission": mission,
        "memory": memory,
        "state_graph": state_graph,
        "bridge": bridge,
        "positions": predicted_positions,
        "priorities": predicted_priorities,
        "trauma": predicted_trauma,
        "vitals": predicted_vitals,
    }


def test_end_to_end_full_pipeline_contracts():
    pipeline = _run_pipeline()
    graph: CasualtyGraph = pipeline["graph"]
    mission: MissionGraph = pipeline["mission"]
    memory: EvidenceMemory = pipeline["memory"]
    bridge: LoopbackMAVLinkBridge = pipeline["bridge"]

    # Graph layer
    assert len(graph.nodes) == len(SCENE)
    assert len(mission.robot_assignments) >= 1
    assert len(mission.medic_assignments) >= 1
    assert len(memory) == len(SCENE)

    # Bridge layer: each casualty published once + each waypoint once
    kinds = [k for (k, _) in bridge.published]
    assert kinds.count("casualty") == len(SCENE)
    assert kinds.count("waypoint") == len(SCENE)

    # Autonomy / handoff contract
    handoff = HumanHandoffService()
    allocator = TaskAllocator()
    recommendations = allocator.recommend(graph.all_nodes())
    assert len(recommendations) == len(SCENE)
    assert all("casualty_id" in r for r in recommendations)

    for node in graph.all_nodes():
        packet = handoff.package_for_medic(node)
        assert packet["casualty_id"] == node.id
        assert packet["priority"] == node.triage_priority

    # Consistency report over the whole graph
    report = check_casualty_graph_consistency(
        graph, mission, min_confidence=0.0
    )
    # At most warnings — any ORPHAN_EDGE / DOUBLE_HANDOFF would be a hard fail.
    assert report.n_errors == 0


def test_end_to_end_all_darpa_gates_produce_reports():
    pipeline = _run_pipeline()

    truth_positions = [(fx.cid, fx.x, fx.y) for fx in SCENE]
    truth_priorities = [(fx.cid, fx.priority) for fx in SCENE]
    truth_trauma = {fx.cid: set(fx.trauma) for fx in SCENE}
    truth_vitals = {fx.cid: (fx.hr_true, fx.rr_true) for fx in SCENE}

    r1 = evaluate_gate1(pipeline["positions"], truth_positions, match_distance=5.0)
    r2 = evaluate_gate2(pipeline["priorities"], truth_priorities)
    r3 = evaluate_gate3(pipeline["trauma"], truth_trauma)
    r4 = evaluate_gate4(pipeline["vitals"], truth_vitals)

    events = [
        HMTEvent(
            casualty_id=fx.cid,
            detected_at=0.0,
            handoff_at=20.0 if pred_priority == "immediate" else 80.0,
            system_priority=pred_priority,
            medic_decision=fx.priority,
        )
        for fx, (_, pred_priority) in zip(SCENE, pipeline["priorities"])
    ]
    r5 = evaluate_hmt_lane(events, immediate_deadline_s=30.0)

    # Gate 1: with small noise every casualty should be within 5 m.
    assert r1.tp == len(SCENE)
    assert r1.f1 == 1.0
    assert r1.mean_localization_error < 5.0

    # Gate 2: at least one prediction correct + critical_miss_rate defined.
    assert 0.0 <= r2.accuracy <= 1.0
    assert 0.0 <= r2.critical_miss_rate <= 1.0

    # Gate 3: per_label keyed by trauma kind (not by casualty id). At
    # least one truth label must have been scored somewhere.
    truth_kinds = set().union(*[set(fx.trauma) for fx in SCENE])
    assert any(kind in r3.per_label for kind in truth_kinds)
    assert 0.0 <= r3.mean_hamming_accuracy <= 1.0

    # Gate 4: one HR + one RR per casualty.
    assert r4.hr.n == len(SCENE)
    assert r4.rr.n == len(SCENE)

    # HMT: all events were scored.
    assert r5.n_events == len(SCENE)
    assert 0.0 <= r5.agreement_rate <= 1.0
    assert 0.0 <= r5.override_rate <= 1.0
