"""triage4 — end-to-end synthetic benchmark (Phase 9d revision).

Run from the project root:

    python examples/full_pipeline_benchmark.py                # text scorecard
    python examples/full_pipeline_benchmark.py --json         # machine-readable
    python examples/full_pipeline_benchmark.py --json out.json

Generates a deterministic synthetic scene, runs the whole triage4
pipeline (perception → signatures → triage → Bayesian twin →
graph → autonomy → platform bridge → counterfactual re-score) and
scores it through all five DARPA gates.

Phase 9d additions over the original benchmark:
- Bayesian patient twin (``PatientTwinFilter``) per casualty with
  posterior probabilities and ESS in the scorecard.
- Eulerian video-magnification HR extraction from a synthetic video
  stack — demonstrates the stand-off vitals path.
- Retrospective counterfactual re-scoring against synthetic
  ground-truth outcomes, with mean regret in the scorecard.
- Optional JSON output so CI jobs can diff the whole scorecard over
  time.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import numpy as np  # noqa: E402

from triage4.autonomy.human_handoff import HumanHandoffService  # noqa: E402
from triage4.autonomy.task_allocator import TaskAllocator  # noqa: E402
from triage4.core.models import CasualtyNode, CasualtySignature, GeoPose  # noqa: E402
from triage4.evaluation import (  # noqa: E402
    HMTEvent,
    evaluate_counterfactuals,
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
    EulerianVitalsExtractor,
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
    PatientTwinFilter,
    RapidTriageEngine,
    TemplateGroundingBackend,
    UncertaintyModel,
    VitalsEstimator,
    explain,
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
    severity: str                 # Phase 9d: for counterfactual scoring
    actual_outcome: float         # simulated post-mission outcome


SCENE: list[Fixture] = [
    Fixture("C1", 10.0, 15.0, "immediate", frozenset({"hemorrhage", "shock_risk"}), 130.0, 28.0, "critical", 0.80),
    Fixture("C2", 30.0, 25.0, "delayed",   frozenset({"respiratory_distress"}),     100.0, 22.0, "serious",  0.88),
    Fixture("C3", 50.0, 30.0, "minimal",   frozenset(),                              72.0, 15.0, "light",    0.96),
    Fixture("C4", 20.0, 60.0, "immediate", frozenset({"hemorrhage"}),               125.0, 30.0, "critical", 0.75),
    Fixture("C5", 70.0, 70.0, "minimal",   frozenset(),                              70.0, 14.0, "light",    0.98),
    Fixture("C6", 45.0, 80.0, "delayed",   frozenset({"shock_risk"}),               110.0, 20.0, "serious",  0.85),
    Fixture("C7", 85.0, 45.0, "immediate", frozenset({"hemorrhage", "respiratory_distress"}), 135.0, 32.0, "critical", 0.70),
    Fixture("C8", 15.0, 40.0, "minimal",   frozenset(),                              75.0, 16.0, "light",    0.97),
]


def _sinusoid(freq_hz: float, fs_hz: float = 30.0, seconds: float = 10.0) -> list[float]:
    n = int(seconds * fs_hz)
    t = np.arange(n) / fs_hz
    return list(np.sin(2 * np.pi * freq_hz * t))


def _synthetic_video_stack(hr_hz: float, fs_hz: float = 30.0, seconds: float = 10.0,
                           h: int = 8, w: int = 8, seed: int = 0) -> np.ndarray:
    """Build an RGB stack whose mean luminance oscillates at hr_hz."""
    n = int(seconds * fs_hz)
    t = np.arange(n) / fs_hz
    base = 128.0 + 10.0 * np.sin(2 * np.pi * hr_hz * t)
    rng = np.random.default_rng(seed)
    stack = np.empty((n, h, w, 3), dtype=np.float64)
    for i, b in enumerate(base):
        frame = np.full((h, w), b) + rng.normal(0.0, 1.0, (h, w))
        stack[i, ..., 0] = frame
        stack[i, ..., 1] = frame
        stack[i, ..., 2] = frame
    return stack


def run_benchmark(seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)

    polygonizer = BodyRegionPolygonizer()
    breathing_ex = BreathingSignatureExtractor()
    bleeding_ex = BleedingSignatureExtractor()
    perfusion_ex = PerfusionSignatureExtractor()
    thermal_ex = ThermalSignatureExtractor()
    posture_ex = PostureSignatureExtractor()
    eulerian = EulerianVitalsExtractor()
    triage_engine = RapidTriageEngine()
    uncertainty_model = UncertaintyModel()
    vitals_estimator = VitalsEstimator()

    graph = CasualtyGraph()
    mission = MissionGraph()
    updates = GraphUpdateService(graph, mission)
    bridge = LoopbackMAVLinkBridge(start_pose=GeoPose(0.0, 0.0), speed=15.0)

    # Phase 9d: one particle filter per casualty.
    twins: dict[str, PatientTwinFilter] = {}
    twin_posteriors: dict[str, dict] = {}

    # Phase 9d: Eulerian-recovered HR per casualty.
    eulerian_hr: dict[str, float] = {}

    positions: list[tuple[str, float, float]] = []
    priorities: list[tuple[str, str]] = []
    trauma: dict[str, set[str]] = {}
    vitals: dict[str, tuple[float, float]] = {}
    explanations: dict[str, str] = {}

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

        priority, score, reasons = triage_engine.infer_priority(sig)
        hypotheses = triage_engine.build_hypotheses(sig)
        uncertainty = uncertainty_model.from_signature(sig, base_score=score)

        # Classical vitals estimator via contact-style sinusoids.
        v = vitals_estimator.estimate(
            _sinusoid(fx.rr_true / 60.0),
            _sinusoid(fx.hr_true / 60.0),
            fs_hz=30.0,
        )

        # Phase 9d: stand-off HR via Eulerian on a synthetic video stack.
        video_stack = _synthetic_video_stack(
            hr_hz=fx.hr_true / 60.0, seed=idx * 17 + 1
        )
        eulerian_pulse = eulerian.extract_pulse(video_stack, fs_hz=30.0)
        eul_bpm = (
            vitals_estimator.estimate([], eulerian_pulse.tolist(), fs_hz=30.0)
            .heart_rate_bpm
        )
        eulerian_hr[fx.cid] = eul_bpm

        # Phase 9d: Bayesian twin posterior per casualty.
        twin = PatientTwinFilter(n_particles=200, seed=idx * 31 + 1)
        for _ in range(5):  # five observation ticks
            twin.update(sig)
        twins[fx.cid] = twin
        posterior = twin.posterior()
        twin_posteriors[fx.cid] = {
            "priority_probs": posterior.priority_probs,
            "most_likely": posterior.most_likely_priority,
            "probability": posterior.most_likely_probability,
            "ess": posterior.effective_sample_size,
        }

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

        # LLM grounding (template backend — no external LLM needed).
        expl = explain(node, reasons, uncertainty=uncertainty,
                       backend=TemplateGroundingBackend())
        explanations[fx.cid] = expl.sentence

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

    # Phase 9d: counterfactual re-scoring against synthetic outcomes.
    counterfactual = evaluate_counterfactuals(
        [(fx.cid, fx.severity, pp, fx.actual_outcome)
         for fx, (_, pp) in zip(SCENE, priorities)]
    )

    handoff = HumanHandoffService()
    allocator = TaskAllocator()
    handoffs = [handoff.package_for_medic(n) for n in graph.all_nodes()]
    recs = allocator.recommend(graph.all_nodes())

    return {
        "gates": {"g1": g1, "g2": g2, "g3": g3, "g4": g4, "g5": g5},
        "counterfactual": counterfactual,
        "twin_posteriors": twin_posteriors,
        "eulerian_hr": eulerian_hr,
        "explanations": explanations,
        "graph": graph,
        "mission": mission,
        "bridge": bridge,
        "handoffs": handoffs,
        "recommendations": recs,
    }


def _print_scorecard(result: dict) -> None:
    g = result["gates"]
    g1, g2, g3, g4, g5 = g["g1"], g["g2"], g["g3"], g["g4"], g["g5"]
    graph = result["graph"]
    mission = result["mission"]
    bridge = result["bridge"]

    print("triage4 end-to-end synthetic benchmark (Phase 9d)")
    print("=" * 60)
    print(f"casualties: {len(graph.nodes)}   "
          f"robot assignments: {len(mission.robot_assignments)}   "
          f"medic handoffs: {len(mission.medic_assignments)}   "
          f"bridge publishes: {len(bridge.published)}")
    print()

    print("Gate 1 — find & locate")
    print(f"   precision={g1.precision:.3f}  recall={g1.recall:.3f}  F1={g1.f1:.3f}")
    print(f"   mean error = {g1.mean_localization_error:.2f} m  "
          f"max error = {g1.max_localization_error:.2f} m")

    print("Gate 2 — rapid triage")
    print(f"   accuracy={g2.accuracy:.3f}  macro_f1={g2.macro_f1:.3f}  "
          f"critical_miss_rate={g2.critical_miss_rate:.3f}")
    for label, m in g2.per_class.items():
        if (m.tp + m.fp + m.fn) == 0:
            continue
        print(f"     {label:<10s} tp={m.tp:>2d} fp={m.fp:>2d} fn={m.fn:>2d} "
              f"p={m.precision:.2f} r={m.recall:.2f} f1={m.f1:.2f}")

    print("Gate 3 — trauma hypotheses")
    print(f"   macro_f1={g3.macro_f1:.3f}  micro_f1={g3.micro_f1:.3f}  "
          f"mean_hamming={g3.mean_hamming_accuracy:.3f}")

    print("Gate 4 — vitals accuracy (classical)")
    print(f"   HR  MAE={g4.hr.mae:.1f}  hit_rate@±10bpm={g4.hr.tolerance_hit_rate:.2f}")
    print(f"   RR  MAE={g4.rr.mae:.1f}  hit_rate@±3bpm={g4.rr.tolerance_hit_rate:.2f}")

    print("Gate 4 — vitals accuracy (Eulerian stand-off HR)")
    eul = result["eulerian_hr"]
    truth_hr = {fx.cid: fx.hr_true for fx in SCENE}
    errors = [abs(eul[c] - truth_hr[c]) for c in eul]
    if errors:
        print(f"   n={len(errors)}  MAE={sum(errors) / len(errors):.1f}  "
              f"max_err={max(errors):.1f} bpm")

    print("HMT lane")
    print(f"   events={g5.n_events}  mean_time={g5.mean_time_to_handoff_s:.1f} s  "
          f"agreement={g5.agreement_rate:.3f}  override={g5.override_rate:.3f}")

    print()
    print("Bayesian patient twins:")
    for cid, post in list(result["twin_posteriors"].items())[:4]:
        probs = post["priority_probs"]
        print(f"   {cid}: P(immediate)={probs['immediate']:.2f}  "
              f"P(delayed)={probs['delayed']:.2f}  "
              f"P(minimal)={probs['minimal']:.2f}  "
              f"ESS={post['ess']}")

    print()
    cf = result["counterfactual"]
    print(f"Counterfactual: mean regret = {cf.mean_regret:.3f}  "
          f"cases above threshold = {cf.n_cases_with_regret}/{cf.n_total}")
    for case in cf.cases[:3]:
        print(f"   {case.casualty_id}: actual={case.actual_priority} → "
              f"best={case.best_alternative} (regret={case.regret})")

    print()
    print("Top 3 grounded explanations (template backend):")
    for cid in ["C1", "C4", "C7"]:
        print(f"   • {result['explanations'].get(cid, '(skip)')}")


def _to_json(result: dict) -> dict:
    """Serialise selected scorecard fields for CI / diff use."""
    g = result["gates"]
    cf = result["counterfactual"]
    return {
        "gate1": {
            "precision": g["g1"].precision,
            "recall": g["g1"].recall,
            "f1": g["g1"].f1,
            "mean_error_m": g["g1"].mean_localization_error,
        },
        "gate2": {
            "accuracy": g["g2"].accuracy,
            "macro_f1": g["g2"].macro_f1,
            "critical_miss_rate": g["g2"].critical_miss_rate,
        },
        "gate3": {
            "macro_f1": g["g3"].macro_f1,
            "micro_f1": g["g3"].micro_f1,
            "mean_hamming": g["g3"].mean_hamming_accuracy,
        },
        "gate4": {
            "hr_mae": g["g4"].hr.mae,
            "rr_mae": g["g4"].rr.mae,
            "hr_hit_rate": g["g4"].hr.tolerance_hit_rate,
            "rr_hit_rate": g["g4"].rr.tolerance_hit_rate,
        },
        "hmt": {
            "agreement": g["g5"].agreement_rate,
            "override": g["g5"].override_rate,
            "immediate_timeliness": g["g5"].immediate_timeliness_rate,
        },
        "counterfactual": {
            "mean_regret": cf.mean_regret,
            "cases_with_regret": cf.n_cases_with_regret,
            "n_total": cf.n_total,
        },
        "twin_posteriors": result["twin_posteriors"],
        "eulerian_hr": result["eulerian_hr"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--json",
        nargs="?",
        const="-",
        default=None,
        help=(
            "Emit JSON scorecard. --json on its own writes to stdout; "
            "--json PATH writes to the file."
        ),
    )
    args = parser.parse_args()

    result = run_benchmark()

    if args.json is None:
        _print_scorecard(result)
        return

    payload = _to_json(result)
    if args.json == "-":
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        Path(args.json).write_text(
            json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
        )
        print(f"wrote {args.json}")


if __name__ == "__main__":
    main()
