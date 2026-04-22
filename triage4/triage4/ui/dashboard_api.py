from __future__ import annotations

import tempfile
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse

from triage4.autonomy.human_handoff import HumanHandoffService
from triage4.autonomy.task_allocator import TaskAllocator
from triage4.core.models import CasualtyNode
from triage4.evaluation.counterfactual import score_counterfactuals
from triage4.evaluation.gate2_rapid_triage import evaluate_gate2
from triage4.graph.casualty_graph import CasualtyGraph
from triage4.graph.mission_graph import MissionGraph
from triage4.mission_coordination.mission_triage import triage_mission
from triage4.state_graph.body_state_graph import BodyStateGraph
from triage4.state_graph.conflict_resolver import ConflictResolver
from triage4.semantic.evidence_tokens import build_evidence_tokens
from triage4.triage_reasoning.bayesian_twin import PatientTwinFilter
from triage4.triage_reasoning.celegans_net import CelegansTriageNet
from triage4.triage_reasoning.explainability import ExplainabilityBuilder
from triage4.triage_reasoning.larrey_baseline import LarreyBaselineTriage
from triage4.triage_reasoning.rapid_triage import RapidTriageEngine
from triage4.triage_reasoning.uncertainty import UncertaintyModel
from triage4.ui.html_export import render_html
from triage4.ui.metrics import default_registry, render_metrics
from triage4.ui.seed import seed_demo_data
from triage4.world_replay.forecast_layer import ForecastLayer


app = FastAPI(title="triage4 API", version="0.3.0")

# CORS — permissive for local dev (Vite at :5173 by default) but
# deliberately NOT using ``allow_credentials=True`` with wildcard
# origins, because that combination is rejected by browser CORS
# preflight per the spec. The Vite proxy in ``web_ui/vite.config.ts``
# makes this irrelevant in the standard dev setup; the CORS block
# stays as a fallback for callers that hit the backend directly.
_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",      # vite preview
    "http://127.0.0.1:4173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

graph = CasualtyGraph()
mission_graph = MissionGraph()
triage_engine = RapidTriageEngine()
handoff = HumanHandoffService()
allocator = TaskAllocator()
explainer = ExplainabilityBuilder()
uncertainty_model = UncertaintyModel()
forecast_layer = ForecastLayer()
larrey_classifier = LarreyBaselineTriage()
celegans_classifier = CelegansTriageNet()
conflict_resolver = ConflictResolver()


# Per-casualty synthetic severity for counterfactual scoring.
# Maps the seeded ``priority_hint`` to the severity bucket the
# counterfactual evaluator expects.
_SEVERITY_FROM_PRIORITY = {
    "immediate": "critical",
    "delayed": "serious",
    "minimal": "light",
}


def _node_or_404(casualty_id: str) -> CasualtyNode:
    if casualty_id not in graph.nodes:
        raise HTTPException(status_code=404, detail="unknown casualty")
    return graph.nodes[casualty_id]


def _synth_history(score: float, steps: int, drift: float) -> list[float]:
    """Small deterministic score-series seeded on the current score.

    The forecast layer needs ≥ 2 points to have a non-trivial slope;
    we synthesise ``steps`` equally-spaced samples around ``score``
    with a light ``drift`` that biases the forecast in the obvious
    direction (immediate → rising, minimal → flat, delayed → mixed).
    """
    if steps < 2:
        steps = 2
    base = max(0.0, min(1.0, float(score)))
    out = []
    for i in range(steps):
        x = base + drift * (i - (steps - 1) / 2) / max(1, steps - 1)
        out.append(max(0.0, min(1.0, x)))
    return out


@app.on_event("startup")
def on_startup() -> None:
    seed_demo_data(graph, triage_engine)
    for node in graph.all_nodes():
        default_registry.incr_casualty(node.triage_priority)
    # Seed a minimal mission graph so mission triage has something
    # to reason over. Matches the simulated 2-medic / UAV setup.
    if not mission_graph.medic_assignments and graph.nodes:
        immediate = [
            n for n in graph.all_nodes() if n.triage_priority == "immediate"
        ][:2]
        for i, node in enumerate(immediate):
            mission_graph.assign_medic(f"medic_{i + 1}", node.id)
        mission_graph.assign_robot("demo_uav", next(iter(graph.nodes)))


# ---------------------------------------------------------------------------
# Basic
# ---------------------------------------------------------------------------


@app.get("/health")
def health() -> dict:
    return {"ok": True, "nodes": len(graph.nodes)}


@app.get("/metrics", response_class=PlainTextResponse)
def metrics() -> PlainTextResponse:
    body, content_type = render_metrics()
    return PlainTextResponse(body, media_type=content_type)


# ---------------------------------------------------------------------------
# Casualties
# ---------------------------------------------------------------------------


@app.get("/casualties")
def casualties() -> list[dict]:
    return [n.to_dict() for n in graph.all_nodes()]


@app.get("/casualties/{casualty_id}")
def casualty_detail(casualty_id: str) -> dict:
    return _node_or_404(casualty_id).to_dict()


@app.get("/casualties/{casualty_id}/explain")
def casualty_explain(casualty_id: str) -> dict:
    return explainer.summarize(_node_or_404(casualty_id))


@app.get("/casualties/{casualty_id}/handoff")
def casualty_handoff(casualty_id: str) -> dict:
    return handoff.package_for_medic(_node_or_404(casualty_id))


@app.get("/casualties/{casualty_id}/twin")
def casualty_twin(casualty_id: str) -> dict:
    """Bayesian patient twin — posterior over priority bands."""
    node = _node_or_404(casualty_id)
    filt = PatientTwinFilter(seed=42)
    # Repeat the observation a few times so the filter has something
    # to condense against (single-sample posterior would be too noisy).
    posterior = None
    for _ in range(5):
        posterior = filt.update(node.signatures, dt_s=1.0)
    assert posterior is not None
    return {
        "casualty_id": casualty_id,
        "priority_probs": posterior.priority_probs,
        "most_likely_priority": posterior.most_likely_priority,
        "most_likely_probability": posterior.most_likely_probability,
        "deterioration_rate": posterior.deterioration_rate,
        "effective_sample_size": posterior.effective_sample_size,
        "is_degenerate": posterior.is_degenerate,
    }


@app.get("/casualties/{casualty_id}/second-opinion")
def casualty_second_opinion(casualty_id: str) -> dict:
    """Three independent classifiers run against the same signature.

    Lets the operator see whether the primary RapidTriageEngine
    agrees with the Larrey 1797 baseline and the 45-weight C.elegans
    network. Disagreement is itself a decision-support signal.
    """
    node = _node_or_404(casualty_id)

    primary_priority, primary_score, primary_reasons = (
        triage_engine.infer_priority(node.signatures)
    )
    larrey_priority, larrey_reasons = larrey_classifier.classify_with_reasons(
        node.signatures,
    )
    celegans_activation = celegans_classifier.activate(node.signatures)
    celegans_priority = celegans_activation.priority

    results: list[dict[str, object]] = [
        {
            "name": "RapidTriageEngine",
            "description": "Default weighted-fusion engine with mortal-sign override.",
            "priority": primary_priority,
            "score": round(primary_score, 3),
            "reasons": primary_reasons,
        },
        {
            "name": "LarreyBaselineTriage",
            "description": "1797 Napoleonic battlefield-medicine rules.",
            "priority": larrey_priority,
            "score": None,
            "reasons": larrey_reasons,
        },
        {
            "name": "CelegansTriageNet",
            "description": "45-weight hand-wired fixed-topology network.",
            "priority": celegans_priority,
            "score": round(celegans_activation.motor[celegans_priority], 3),
            "reasons": [
                f"motor.{k} = {v:.2f}"
                for k, v in celegans_activation.motor.items()
            ],
        },
    ]

    priorities: list[str] = [str(r["priority"]) for r in results]
    all_agree = len(set(priorities)) == 1

    return {
        "casualty_id": casualty_id,
        "classifiers": results,
        "agreement": all_agree,
        "distinct_priorities": sorted(set(priorities)),
    }


@app.get("/casualties/{casualty_id}/uncertainty")
def casualty_uncertainty(casualty_id: str) -> dict:
    """Per-channel confidence + adjusted score."""
    node = _node_or_404(casualty_id)
    _, base_score, _ = triage_engine.infer_priority(node.signatures)
    report = uncertainty_model.from_signature(
        node.signatures, base_score=base_score,
    )
    return {
        "casualty_id": casualty_id,
        "base_score": report.base_score,
        "overall_confidence": report.overall_confidence,
        "overall_uncertainty": report.overall_uncertainty,
        "adjusted_score": report.adjusted_score,
        "per_channel_confidence": dict(report.per_channel_confidence),
    }


@app.get("/casualties/{casualty_id}/conflict")
def casualty_conflict(casualty_id: str) -> dict:
    """Reconcile raw hypothesis scores through the conflict resolver.

    Builds a ``BodyStateGraph`` from the casualty's evidence tokens,
    grabs its raw hypothesis map, and runs ``ConflictResolver`` so the
    UI can show support boosts, conflict suppressions, and the winning
    hypothesis in each conflict clique.
    """
    node = _node_or_404(casualty_id)
    tokens = build_evidence_tokens(node.signatures)
    bsg = BodyStateGraph()
    bsg.ingest(tokens)
    raw = bsg.hypothesis_scores
    resolved = conflict_resolver.resolve(raw)

    return {
        "casualty_id": casualty_id,
        "evidence_tokens": [t.to_dict() for t in tokens],
        "raw_scores": raw,
        "ranked": [
            {
                "name": r.name,
                "raw_score": r.raw_score,
                "adjusted_score": r.adjusted_score,
                "suppressed": r.suppressed,
                "reasons": r.reasons,
            }
            for r in resolved.ranked
        ],
        "groups": [
            {
                "members": g.members,
                "winner": g.winner,
                "winner_score": g.winner_score,
            }
            for g in resolved.groups
        ],
    }


# ---------------------------------------------------------------------------
# Mission
# ---------------------------------------------------------------------------


@app.get("/mission/status")
def mission_status() -> dict:
    """Fractal mission-level triage: escalate / sustain / wind_down."""
    signature, result = triage_mission(
        casualty_graph=graph,
        mission_graph=mission_graph,
        platform_capacity=10,
        n_medics=3,
        elapsed_minutes=30.0,
        mission_window_minutes=60.0,
    )
    return {
        "signature": asdict(signature),
        "priority": result.priority,
        "score": result.score,
        "contributions": result.contributions,
        "reasons": result.reasons,
        "medic_assignments": dict(mission_graph.medic_assignments),
        "unresolved_regions": sorted(mission_graph.unresolved_regions),
    }


# ---------------------------------------------------------------------------
# Forecast
# ---------------------------------------------------------------------------


@app.get("/forecast/casualty/{casualty_id}")
def forecast_casualty(casualty_id: str, minutes: float = 5.0) -> dict:
    """Project a casualty's urgency ``minutes`` minutes into the future."""
    node = _node_or_404(casualty_id)
    drift = {
        "immediate": 0.05,
        "delayed": 0.01,
        "minimal": -0.01,
        "unknown": 0.0,
    }.get(node.triage_priority, 0.0)
    score_history = _synth_history(node.confidence, steps=5, drift=drift)
    fc = forecast_layer.project_casualty(score_history, minutes_ahead=minutes)
    return {
        "casualty_id": casualty_id,
        "score_history": [round(s, 3) for s in score_history],
        "projected_score": fc.projected_score,
        "projected_priority": fc.projected_priority,
        "slope_per_minute": fc.slope_per_minute,
        "confidence": fc.confidence,
        "reasons": fc.reasons,
        "minutes_ahead": float(minutes),
    }


@app.get("/forecast/mission")
def forecast_mission(minutes: float = 5.0) -> dict:
    """Extrapolate the mission signature ``minutes`` into the future."""
    # Build a tiny history of mission signatures by rerunning triage
    # with slightly advancing time-budget burn. Enough for the
    # forecaster to compute a slope.
    history = []
    for t in (15.0, 20.0, 25.0, 30.0):
        sig, _ = triage_mission(
            casualty_graph=graph,
            mission_graph=mission_graph,
            platform_capacity=10,
            n_medics=3,
            elapsed_minutes=t,
            mission_window_minutes=60.0,
        )
        history.append(sig)

    fc = forecast_layer.project_mission(history, minutes_ahead=minutes)
    return {
        "projected_signature": asdict(fc.projected_signature),
        "projected_priority": fc.projected_result.priority,
        "projected_score": fc.projected_result.score,
        "contributions": fc.projected_result.contributions,
        "per_channel_slope": fc.per_channel_slope,
        "reasons": fc.reasons,
        "minutes_ahead": float(minutes),
    }


# ---------------------------------------------------------------------------
# Evaluation scorecard (Gate 2 + HMT + counterfactual regret)
# ---------------------------------------------------------------------------


@app.get("/evaluation/scorecard")
def evaluation_scorecard() -> dict:
    """Run DARPA-gate-style evaluation against the seeded ground truth.

    Only Gate 2 (rapid-triage classification) is derivable from the
    in-memory casualty graph — gates 1/3/4 need perception / trauma
    labels that the dashboard's seed doesn't carry. Counterfactual
    regret uses the priority-hint → severity mapping from the seed
    table.
    """
    from triage4.ui.seed import DEMO_ROWS

    # Predictions = engine decisions currently in the graph.
    predictions = [
        (n.id, n.triage_priority) for n in graph.all_nodes()
    ]
    # Truths come from the seed's priority_hint column.
    truths = [(row[0], row[1]) for row in DEMO_ROWS if row[0] in graph.nodes]

    gate2 = evaluate_gate2(predictions, truths)

    # Counterfactual regret — for each casualty with a known severity
    # (via the seed), compute actual vs. best-alternative outcome.
    regrets: list[dict] = []
    for cid, priority_hint, _x, _y in DEMO_ROWS:
        if cid not in graph.nodes:
            continue
        severity = _SEVERITY_FROM_PRIORITY.get(priority_hint)
        if severity is None:
            continue
        node = graph.nodes[cid]
        actual_priority = node.triage_priority
        if actual_priority not in {"immediate", "delayed", "minimal"}:
            continue
        # Synthetic outcome proxy: blend confidence with priority
        # weight. Not clinically meaningful — just enough for the
        # counterfactual to have non-constant inputs.
        actual_outcome = min(1.0, max(0.0, 0.5 + 0.4 * node.confidence))
        case = score_counterfactuals(
            cid, severity, actual_priority, actual_outcome,
        )
        regrets.append({
            "casualty_id": case.casualty_id,
            "severity": case.true_severity,
            "actual_priority": case.actual_priority,
            "actual_outcome": case.actual_outcome,
            "counterfactuals": case.counterfactuals,
            "best_alternative": case.best_alternative,
            "regret": case.regret,
        })

    mean_regret = (
        sum(r["regret"] for r in regrets) / len(regrets) if regrets else 0.0
    )

    return {
        "gate2": {
            "accuracy": gate2.accuracy,
            "macro_f1": gate2.macro_f1,
            "critical_miss_rate": gate2.critical_miss_rate,
            "per_class": {
                label: {
                    "precision": round(stats.precision, 3),
                    "recall": round(stats.recall, 3),
                    "f1": round(stats.f1, 3),
                    "tp": stats.tp,
                    "fp": stats.fp,
                    "fn": stats.fn,
                }
                for label, stats in gate2.per_class.items()
            },
            "confusion_matrix": gate2.confusion.tolist(),
            "class_labels": list(gate2.class_labels),
        },
        "counterfactuals": {
            "cases": regrets,
            "mean_regret": round(mean_regret, 3),
            "n": len(regrets),
        },
        "summary": {
            "total_casualties": len(graph.nodes),
            "critical_miss_rate": gate2.critical_miss_rate,
            "accuracy": gate2.accuracy,
        },
    }


# ---------------------------------------------------------------------------
# Graph / map / replay / tasks / export (existing)
# ---------------------------------------------------------------------------


@app.get("/graph")
def graph_json() -> dict:
    return graph.as_json()


@app.get("/map")
def map_json() -> dict:
    return {
        "platforms": [
            {"id": "demo_uav", "x": 50, "y": 8, "kind": "uav"},
            {"id": "medic_1", "x": 15, "y": 90, "kind": "medic"},
        ],
        "casualties": [
            {
                "id": n.id,
                "x": n.location.x,
                "y": n.location.y,
                "priority": n.triage_priority,
                "confidence": n.confidence,
            }
            for n in graph.all_nodes()
        ],
    }


@app.get("/replay")
def replay_json() -> dict:
    frames = []
    casualties_snapshot = graph.all_nodes()

    for t in range(6):
        frames.append(
            {
                "t": t,
                "platforms": [
                    {"id": "demo_uav", "x": 15 + (t * 7), "y": 10 + (t * 5), "kind": "uav"},
                ],
                "casualties": [
                    {
                        "id": n.id,
                        "x": n.location.x,
                        "y": n.location.y,
                        "priority": n.triage_priority,
                    }
                    for n in casualties_snapshot
                ],
            }
        )
    return {"frames": frames}


@app.get("/tasks")
def tasks() -> list[dict]:
    return allocator.recommend(graph.all_nodes())


@app.get("/overview")
def overview() -> dict:
    """Executive summary — landing-page stats."""
    nodes = graph.all_nodes()
    by_priority: dict[str, int] = {}
    confidences = []
    oldest_unresponded: str | None = None
    oldest_ts: float | None = None
    for n in nodes:
        by_priority[n.triage_priority] = by_priority.get(n.triage_priority, 0) + 1
        confidences.append(n.confidence)
        if n.assigned_medic is None and n.triage_priority == "immediate":
            ts = n.first_seen_ts
            if oldest_ts is None or ts < oldest_ts:
                oldest_ts = ts
                oldest_unresponded = n.id

    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    # Mission status — cheap, reuses the mission triage pipeline.
    mission_sig, mission_result = triage_mission(
        casualty_graph=graph,
        mission_graph=mission_graph,
        platform_capacity=10,
        n_medics=3,
        elapsed_minutes=30.0,
        mission_window_minutes=60.0,
    )

    return {
        "total_casualties": len(nodes),
        "by_priority": by_priority,
        "avg_confidence": round(avg_confidence, 3),
        "oldest_unresponded_immediate": oldest_unresponded,
        "mission_priority": mission_result.priority,
        "mission_score": mission_result.score,
        "mission_reasons": mission_result.reasons,
        "n_medic_assignments": len(mission_graph.medic_assignments),
        "n_unresolved_regions": len(mission_graph.unresolved_regions),
    }


@app.get("/casualties/{casualty_id}/marker")
def casualty_marker(casualty_id: str) -> dict:
    """HMAC-signed offline handoff marker + QR-safe string.

    Uses a fixed demo secret for dashboard purposes. In a real
    deployment the secret MUST come from TRIAGE4_MARKER_SECRET.
    """
    from triage4.integrations.marker_codec import (
        encode_marker,
        to_qr_string,
    )

    node = _node_or_404(casualty_id)
    secret = b"demo-dashboard-secret-not-for-production"
    envelope = encode_marker(node, secret=secret, medic="dashboard")
    qr = to_qr_string(envelope)
    return {
        "casualty_id": casualty_id,
        "qr_payload": qr,
        "envelope_bytes": len(envelope),
        "qr_chars": len(qr),
    }


@app.get("/export.html", response_class=HTMLResponse)
def export_html() -> FileResponse:
    """Self-contained HTML snapshot of the casualty graph.

    Uses the infom-inspired ``render_html`` so the result is a single file
    that works offline without the backend.
    """
    out_path = Path(tempfile.gettempdir()) / "triage4_export.html"
    render_html(graph, out_path=out_path)
    return FileResponse(out_path, media_type="text/html", filename="triage4_export.html")
