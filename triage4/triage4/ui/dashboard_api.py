from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse

from triage4.autonomy.human_handoff import HumanHandoffService
from triage4.autonomy.task_allocator import TaskAllocator
from triage4.graph.casualty_graph import CasualtyGraph
from triage4.triage_reasoning.explainability import ExplainabilityBuilder
from triage4.triage_reasoning.rapid_triage import RapidTriageEngine
from triage4.ui.html_export import render_html
from triage4.ui.metrics import default_registry, render_metrics
from triage4.ui.seed import seed_demo_data


app = FastAPI(title="triage4 API", version="0.2.0")

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
triage_engine = RapidTriageEngine()
handoff = HumanHandoffService()
allocator = TaskAllocator()
explainer = ExplainabilityBuilder()


@app.on_event("startup")
def on_startup() -> None:
    seed_demo_data(graph, triage_engine)
    for node in graph.all_nodes():
        default_registry.incr_casualty(node.triage_priority)


@app.get("/health")
def health() -> dict:
    return {"ok": True, "nodes": len(graph.nodes)}


@app.get("/metrics", response_class=PlainTextResponse)
def metrics() -> PlainTextResponse:
    body, content_type = render_metrics()
    return PlainTextResponse(body, media_type=content_type)


@app.get("/casualties")
def casualties() -> list[dict]:
    return [n.to_dict() for n in graph.all_nodes()]


@app.get("/casualties/{casualty_id}")
def casualty_detail(casualty_id: str) -> dict:
    if casualty_id not in graph.nodes:
        raise HTTPException(status_code=404, detail="unknown casualty")
    return graph.nodes[casualty_id].to_dict()


@app.get("/casualties/{casualty_id}/explain")
def casualty_explain(casualty_id: str) -> dict:
    if casualty_id not in graph.nodes:
        raise HTTPException(status_code=404, detail="unknown casualty")
    return explainer.summarize(graph.nodes[casualty_id])


@app.get("/casualties/{casualty_id}/handoff")
def casualty_handoff(casualty_id: str) -> dict:
    if casualty_id not in graph.nodes:
        raise HTTPException(status_code=404, detail="unknown casualty")
    return handoff.package_for_medic(graph.nodes[casualty_id])


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


@app.get("/export.html", response_class=HTMLResponse)
def export_html() -> FileResponse:
    """Self-contained HTML snapshot of the casualty graph.

    Uses the infom-inspired ``render_html`` so the result is a single file
    that works offline without the backend.
    """
    out_path = Path(tempfile.gettempdir()) / "triage4_export.html"
    render_html(graph, out_path=out_path)
    return FileResponse(out_path, media_type="text/html", filename="triage4_export.html")
