"""triage4 — end-to-end synthetic benchmark.

Run from the project root:

    python examples/full_pipeline_benchmark.py

Generates a deterministic synthetic scene, runs the whole triage4
pipeline (perception → signatures → triage → graph → autonomy →
platform bridge), scores it through all five DARPA gates and prints a
readable scorecard.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

# Allow `python examples/full_pipeline_benchmark.py` from the project root
# without installing the package first.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import numpy as np  # noqa: E402

from triage4.autonomy.human_handoff import HumanHandoffService  # noqa: E402
from triage4.autonomy.task_allocator import TaskAllocator  # noqa: E402
from triage4.core.models import CasualtyNode, CasualtySignature, GeoPose  # noqa: E402
from triage4.evaluation import (  # noqa: E402
    HMTEvent,
    evaluate_gate1,
    evaluate_gate2,
    evaluate_gate3,
    evaluate_gate4,
    evaluate_hmt_lane,
)
from triage4.graph.casualty_graph import CasualtyGraph  # noqa: E402
from triage4.graph.mission_graph import MissionGraph  # noqa: E402
from triage4.graph.updates import GraphUpdateService  # noqa: E402
from triage4.integrations import LoopbackMAVLinkBridge  # noqa: E402
from triage4.perception.body_regions import BodyRegionPolygonizer  # noqa: E402
from triage4.signatures import (  # noqa: E402
    BleedingSignatureExtractor,
    BreathingSignatureExtractor,
    PerfusionSignatureExtractor,
    PostureSignatureExtractor,
    ThermalSignatureExtractor,
)
from triage4.sim.casualty_profiles import (  # noqa: E402
    bleeding_inputs,
    breath_signal,
    perfusion_series,
)
from triage4.triage_reasoning import (  # noqa: E402
    RapidTriageEngine,
    UncertaintyModel,
    VitalsEstimator,
)


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
    Fixture("C2", 30.0, 25.0, "delayed",   frozenset({"respiratory_distress"}),     100.0, 22.0),
    Fixture("C3", 50.0, 30.0, "minimal",   frozenset(),                              72.0, 15.0),
    Fixture("C4", 20.0, 60.0, "immediate", frozenset({"hemorrhage"}),               125.0, 30.0),
    Fixture("C5", 70.0, 70.0, "minimal",   frozenset(),                              70.0, 14.0),
    Fixture("C6", 45.0, 80.0, "delayed",   frozenset({"shock_risk"}),               110.0, 20.0),
    Fixture("C7", 85.0, 45.0, "immediate", frozenset({"hemorrhage", "respiratory_distress"}), 135.0, 32.0),
    Fixture("C8", 15.0, 40.0, "minimal",   frozenset(),                              75.0, 16.0),
]


def _sinusoid(freq_hz: float, fs_hz: float = 30.0, seconds: float = 10.0) -> list[float]:
    n = int(seconds * fs_hz)
    t = np.arange(n) / fs_hz
    return list(np.sin(2 * np.pi * freq_hz * t))


def run_benchmark(seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)

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
    bridge = LoopbackMAVLinkBridge(start_pose=GeoPose(0.0, 0.0), speed=15.0)

    positions: list[tuple[str, float, float]] = []
    priorities: list[tuple[str, str]] = []
    trauma: dict[str, set[str]] = {}
    vitals: dict[str, tuple[float, float]] = {}

    for idx, fx in enumerate(SCENE):
        body_regions = polygonizer.build_from_center(fx.x, fx.y)

        breathing = breathing_ex.extract(breath_signal(fx.priority))
        vr, td, ph = bleeding_inputs(fx.priority)
        bleeding = bleeding_ex.extract(vr, td, ph)
        perfusion = perfusion_ex.extract(perfusion_series(fx.priority))
        thermal_patch = rng.normal(25.0, 3.0, (6, 6))
        thermal = thermal_ex.extract(thermal_patch)
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
                "breathing_quality": breathing["quality_score"],
                "perfusion_quality": perfusion["quality_score"],
                "bleeding_confidence": bleeding["confidence"],
                "thermal_quality": thermal["quality_score"],
            },
        )

        priority, score, _ = triage_engine.infer_priority(sig)
        hypotheses = triage_engine.build_hypotheses(sig)
        uncertainty = uncertainty_model.from_signature(sig, base_score=score)

        v = vitals_estimator.estimate(
            _sinusoid(fx.rr_true / 60.0),
            _sinusoid(fx.hr_true / 60.0),
            fs_hz=30.0,
        )

        node = CasualtyNode(
            id=fx.cid,
            location=GeoPose(
                x=fx.x + float(rng.normal(0.0, 0.5)),
                y=fx.y + float(rng.normal(0.0, 0.5)),
            ),
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
        bridge.publish_casualty(node)

        positions.append((fx.cid, node.location.x, node.location.y))
        priorities.append((fx.cid, priority))
        trauma[fx.cid] = {h.kind for h in hypotheses}
        vitals[fx.cid] = (v.heart_rate_bpm, v.respiration_rate_bpm)

    truth_positions = [(fx.cid, fx.x, fx.y) for fx in SCENE]
    truth_priorities = [(fx.cid, fx.priority) for fx in SCENE]
    truth_trauma = {fx.cid: set(fx.trauma) for fx in SCENE}
    truth_vitals = {fx.cid: (fx.hr_true, fx.rr_true) for fx in SCENE}

    g1 = evaluate_gate1(positions, truth_positions, match_distance=5.0)
    g2 = evaluate_gate2(priorities, truth_priorities)
    g3 = evaluate_gate3(trauma, truth_trauma)
    g4 = evaluate_gate4(vitals, truth_vitals)

    events = [
        HMTEvent(
            casualty_id=fx.cid,
            detected_at=float(i),
            handoff_at=float(i) + (20.0 if pred_p == "immediate" else 80.0),
            system_priority=pred_p,
            medic_decision=fx.priority,
        )
        for i, (fx, (_, pred_p)) in enumerate(zip(SCENE, priorities))
    ]
    g5 = evaluate_hmt_lane(events, immediate_deadline_s=30.0)

    handoff = HumanHandoffService()
    allocator = TaskAllocator()
    handoffs = [handoff.package_for_medic(n) for n in graph.all_nodes()]
    recs = allocator.recommend(graph.all_nodes())

    return {
        "g1": g1, "g2": g2, "g3": g3, "g4": g4, "g5": g5,
        "graph": graph, "mission": mission, "bridge": bridge,
        "handoffs": handoffs, "recommendations": recs,
    }


def _print_scorecard(result: dict) -> None:
    g1, g2, g3, g4, g5 = result["g1"], result["g2"], result["g3"], result["g4"], result["g5"]
    graph = result["graph"]
    mission = result["mission"]
    bridge = result["bridge"]

    print("triage4 end-to-end synthetic benchmark")
    print("=" * 60)
    print(f"casualties: {len(graph.nodes)}   "
          f"robot assignments: {len(mission.robot_assignments)}   "
          f"medic handoffs: {len(mission.medic_assignments)}   "
          f"bridge publishes: {len(bridge.published)}")
    print()

    print(f"Gate 1 — find & locate")
    print(f"   precision={g1.precision:.3f}  recall={g1.recall:.3f}  F1={g1.f1:.3f}")
    print(f"   mean error = {g1.mean_localization_error:.2f} m  "
          f"max error = {g1.max_localization_error:.2f} m")

    print(f"Gate 2 — rapid triage")
    print(f"   accuracy={g2.accuracy:.3f}  macro_f1={g2.macro_f1:.3f}  "
          f"critical_miss_rate={g2.critical_miss_rate:.3f}")
    for label, m in g2.per_class.items():
        if (m.tp + m.fp + m.fn) == 0:
            continue
        print(f"     {label:<10s} tp={m.tp:>2d} fp={m.fp:>2d} fn={m.fn:>2d} "
              f"p={m.precision:.2f} r={m.recall:.2f} f1={m.f1:.2f}")

    print(f"Gate 3 — trauma hypotheses")
    print(f"   macro_f1={g3.macro_f1:.3f}  micro_f1={g3.micro_f1:.3f}  "
          f"mean_hamming={g3.mean_hamming_accuracy:.3f}")
    for label, m in g3.per_label.items():
        print(f"     {label:<22s} tp={m.tp:>2d} fp={m.fp:>2d} fn={m.fn:>2d} "
              f"f1={m.f1:.2f}")

    print(f"Gate 4 — vitals accuracy")
    print(f"   HR  n={g4.hr.n:>2d}  MAE={g4.hr.mae:.1f}  "
          f"RMSE={g4.hr.rmse:.1f}  hit_rate@±10bpm={g4.hr.tolerance_hit_rate:.2f}")
    print(f"   RR  n={g4.rr.n:>2d}  MAE={g4.rr.mae:.1f}  "
          f"RMSE={g4.rr.rmse:.1f}  hit_rate@±3bpm={g4.rr.tolerance_hit_rate:.2f}")

    print(f"HMT lane")
    print(f"   events={g5.n_events}  mean_time={g5.mean_time_to_handoff_s:.1f} s  "
          f"max_time={g5.max_time_to_handoff_s:.1f} s")
    print(f"   agreement={g5.agreement_rate:.3f}  "
          f"override={g5.override_rate:.3f}  "
          f"immediate_timeliness={g5.immediate_timeliness_rate:.3f}")

    print()
    print("Top 3 recommended handoffs:")
    for r in result["recommendations"][:3]:
        print(f"   {r['casualty_id']} priority={r['priority']} "
              f"confidence={r['confidence']:.2f} "
              f"location=({r['location']['x']:.1f}, {r['location']['y']:.1f})")


def main() -> None:
    result = run_benchmark()
    _print_scorecard(result)


if __name__ == "__main__":
    main()
