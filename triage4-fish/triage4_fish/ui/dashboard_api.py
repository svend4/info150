"""FastAPI dashboard for triage4-fish — sibling-level Web UI.

Mirrors the architectural pattern of the flagship's
``triage4.ui.dashboard_api`` but scoped to the aquaculture domain:
multi-modal pen welfare scoring (gill rate / school cohesion /
sea-lice / mortality floor / water chemistry).

Endpoints (all GET unless noted):
    GET  /health                  — service status + pen count
    GET  /report                  — current PenReport (JSON)
    GET  /pens                    — list of PenWelfareScore rows
    GET  /pens/{pen_id}           — one pen's score + its alerts
    GET  /alerts                  — list of FarmManagerAlerts
    POST /demo/reload             — re-seed with the demo observations
    GET  /export.html             — self-contained offline HTML

CORS is permissive for the standard Vite dev server origins.

This module is **opt-in**: the imports here pull in fastapi +
uvicorn, which live in the ``[ui]`` extra of ``pyproject.toml``.
The rest of triage4-fish does not depend on either.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from ..core.models import PenReport
from pydantic import BaseModel, Field

from ..pen_health.monitoring_engine import AquacultureHealthEngine
from ..sim.synthetic_pen import demo_observations, generate_observation

app = FastAPI(title="triage4-fish API", version="0.1.0")

_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_FARM_ID = "DEMO_FARM"
_engine = AquacultureHealthEngine()


def _build_report() -> tuple[list, PenReport]:
    obs = demo_observations()
    aggregate = PenReport(farm_id=_FARM_ID)
    for o in obs:
        single = _engine.review(o, farm_id=_FARM_ID)
        aggregate.scores.extend(single.scores)
        aggregate.alerts.extend(single.alerts)
    return obs, aggregate


_observations, _report = _build_report()


def _seed() -> None:
    """Re-build the in-memory state from the synthetic demo."""
    global _observations, _report
    _observations, _report = _build_report()


def _level_counts() -> dict[str, int]:
    counts: dict[str, int] = {"steady": 0, "watch": 0, "urgent": 0}
    for s in _report.scores:
        counts[s.welfare_level] = counts.get(s.welfare_level, 0) + 1
    return counts


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "service": "triage4-fish",
        "version": "0.1.0",
        "farm_id": _report.farm_id,
        "pen_count": len(_report.scores),
        "alert_count": len(_report.alerts),
    }


@app.get("/report")
def report() -> dict[str, Any]:
    """Full pen report — scores, alerts, level counts."""
    return {
        "farm_id": _report.farm_id,
        "pen_count": len(_report.scores),
        "level_counts": _level_counts(),
        "scores": [asdict(s) for s in _report.scores],
        "alerts": [asdict(a) for a in _report.alerts],
    }


@app.get("/pens")
def pens() -> list[dict[str, Any]]:
    """Per-pen welfare scores."""
    by_id = {o.pen_id: o for o in _observations}
    return [
        {
            **asdict(s),
            "species": getattr(by_id.get(s.pen_id), "species", None),
            "location_handle": getattr(by_id.get(s.pen_id), "location_handle", None),
        }
        for s in _report.scores
    ]


@app.get("/pens/{pen_id}")
def pen_by_id(pen_id: str) -> dict[str, Any]:
    for s in _report.scores:
        if s.pen_id == pen_id:
            obs = next((o for o in _observations if o.pen_id == pen_id), None)
            return {
                **asdict(s),
                "species": getattr(obs, "species", None),
                "location_handle": getattr(obs, "location_handle", None),
                "alerts": [
                    asdict(a) for a in _report.alerts
                    if a.pen_id == pen_id
                ],
            }
    raise HTTPException(
        status_code=404,
        detail=f"pen {pen_id!r} not found",
    )


@app.get("/alerts")
def alerts() -> list[dict[str, Any]]:
    """All farm-manager alerts across the farm."""
    return [asdict(a) for a in _report.alerts]


@app.post("/demo/reload")
def demo_reload() -> dict[str, Any]:
    """Re-seed with fresh synthetic observations."""
    _seed()
    return {
        "reloaded": True,
        "farm_id": _report.farm_id,
        "pen_count": len(_report.scores),
        "alert_count": len(_report.alerts),
    }





class CameraRunRequest(BaseModel):
    """Camera-driven pen observation. Mean motion → school disruption;
    contrast variance → water clarity. Sea-lice, mortality count, DO
    drop, temp anomaly need their own sensors → sliders.
    """

    pen_id: str = Field("WEBCAM_PEN", min_length=1, max_length=64)
    species: str = "salmon"
    school_disruption: float = Field(0.0, ge=0.0, le=1.0)
    turbidity_safety: float = Field(0.5, ge=0.0, le=1.0)
    gill_anomaly: float = Field(0.0, ge=0.0, le=1.0)
    sea_lice_burden: float = Field(0.0, ge=0.0, le=1.0)
    mortality_count: int = Field(0, ge=0, le=100)
    do_drop: float = Field(0.0, ge=0.0, le=1.0)
    temp_anomaly: float = Field(0.0, ge=0.0, le=1.0)


@app.post("/camera/run")
def camera_run(req: CameraRunRequest) -> dict[str, Any]:
    """Replace the dashboard with a single camera-derived pen observation."""
    global _observations, _report
    obs = generate_observation(
        pen_id=req.pen_id,
        species=req.species,  # type: ignore[arg-type]
        school_disruption=req.school_disruption,
        gill_anomaly=req.gill_anomaly,
        sea_lice_burden=req.sea_lice_burden,
        mortality_count=req.mortality_count,
        do_drop=req.do_drop,
        temp_anomaly=req.temp_anomaly,
        seed=42,
    )
    _observations = [obs]
    aggregate = PenReport(farm_id="WEBCAM_FARM")
    single = _engine.review(obs, farm_id="WEBCAM_FARM")
    aggregate.scores.extend(single.scores)
    aggregate.alerts.extend(single.alerts)
    _report = aggregate
    return {"pen_id": req.pen_id, "school_disruption": req.school_disruption,
            "turbidity_safety": req.turbidity_safety,
            "score_count": len(_report.scores), "alert_count": len(_report.alerts)}


@app.get("/export.html", response_class=HTMLResponse)
def export_html() -> str:
    """Self-contained offline HTML snapshot — no JS, no fetch."""
    rows: list[str] = []
    for s in _report.scores:
        cls = {"urgent": "u", "watch": "w", "steady": "s"}.get(s.welfare_level, "")
        rows.append(
            f"<tr><td>{s.pen_id}</td>"
            f"<td class='{cls}'><b>{s.welfare_level}</b></td>"
            f"<td>{s.overall:.2f}</td>"
            f"<td>{s.gill_rate_safety:.2f}</td>"
            f"<td>{s.school_cohesion_safety:.2f}</td>"
            f"<td>{s.sea_lice_safety:.2f}</td>"
            f"<td>{s.mortality_safety:.2f}</td>"
            f"<td>{s.water_chemistry_safety:.2f}</td></tr>"
        )
    rows_html = "\n".join(rows)
    alerts_html = "\n".join(
        f"<li><b>{a.level}</b> [{a.kind}] {a.pen_id}: {a.text}</li>"
        for a in _report.alerts
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8">
<title>triage4-fish — farm {_report.farm_id}</title>
<style>
body {{ font: 14px/1.5 system-ui; max-width: 1100px; margin: 2rem auto;
       padding: 0 1rem; color:#1a1a2e; background:#f4f8fb; }}
h1, h2 {{ margin-top: 1.5em; }} table {{ border-collapse: collapse; width:100%; }}
th, td {{ padding: 6px 10px; text-align:left; border-bottom: 1px solid #d6dce6; }}
th {{ background:#e9eff7; }} tr:hover td {{ background:#fffceb; }}
td.u {{ color:#a4262c; }} td.w {{ color:#a86b00; }} td.s {{ color:#107c10; }}
ul {{ padding-left: 1.2rem; }}
</style></head><body>
<h1>triage4-fish</h1>
<p>Farm <code>{_report.farm_id}</code> · {len(_report.scores)} pens reviewed.</p>
<table><thead><tr><th>Pen</th><th>Level</th><th>Overall</th>
<th>Gill</th><th>School</th><th>Lice</th><th>Mort.</th><th>Water</th></tr></thead>
<tbody>{rows_html}</tbody></table>
<h2>Alerts</h2>
<ul>{alerts_html or "<li><i>none</i></li>"}</ul>
</body></html>"""
