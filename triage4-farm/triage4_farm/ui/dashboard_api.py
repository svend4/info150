"""FastAPI dashboard for triage4-farm — farmer/stockperson dashboard.

Note: farm uses ``flag`` (well/concern/urgent) instead of the
``alert_level`` (ok/watch/urgent) used by the other siblings.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from ..sim.synthetic_herd import demo_herd, generate_observation
from ..welfare_check.welfare_engine import WelfareCheckEngine

app = FastAPI(title="triage4-farm API", version="0.1.0")

_ALLOWED_ORIGINS = [
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:4173", "http://127.0.0.1:4173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_FARM_ID = "DEMO_FARM"
_engine = WelfareCheckEngine()
_herd = demo_herd(n_animals=6, n_lame=2)
_report = _engine.review(farm_id=_FARM_ID, observations=_herd)


def _seed() -> None:
    global _herd, _report
    _herd = demo_herd(n_animals=6, n_lame=2)
    _report = _engine.review(farm_id=_FARM_ID, observations=_herd)


def _flag_counts() -> dict[str, int]:
    counts: dict[str, int] = {"well": 0, "concern": 0, "urgent": 0}
    for s in _report.scores:
        counts[s.flag] = counts.get(s.flag, 0) + 1
    return counts


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "service": "triage4-farm", "version": "0.1.0",
        "farm_id": _report.farm_id,
        "animal_count": len(_report.scores),
        "alert_count": len(_report.alerts),
    }


@app.get("/report")
def report() -> dict[str, Any]:
    return {
        "farm_id": _report.farm_id,
        "animal_count": len(_report.scores),
        "herd_overall": _report.herd_overall,
        "flag_counts": _flag_counts(),
        "scores": [asdict(s) for s in _report.scores],
        "alerts": [asdict(a) for a in _report.alerts],
    }


@app.get("/animals")
def animals() -> list[dict[str, Any]]:
    return [asdict(s) for s in _report.scores]


@app.get("/animals/{animal_id}")
def animal_by_id(animal_id: str) -> dict[str, Any]:
    for s in _report.scores:
        if s.animal_id == animal_id:
            return {
                **asdict(s),
                "alerts": [asdict(a) for a in _report.alerts if a.animal_id == animal_id],
            }
    raise HTTPException(404, f"animal {animal_id!r} not found")


@app.get("/alerts")
def alerts() -> list[dict[str, Any]]:
    return [asdict(a) for a in _report.alerts]


@app.post("/demo/reload")
def demo_reload() -> dict[str, Any]:
    _seed()
    return {"reloaded": True, "animal_count": len(_report.scores),
            "alert_count": len(_report.alerts)}





class CameraRunRequest(BaseModel):
    """Camera-driven welfare check on a single animal. Mean motion →
    activity proxy. Lameness, respiratory elevation, thermal hotspot
    need pose / IR sensors → manual sliders.
    """

    animal_id: str = Field("WEBCAM_ANIMAL", min_length=1, max_length=64)
    species: str = "cow"
    activity_proxy: float = Field(0.0, ge=0.0, le=1.0)
    lameness_severity: float = Field(0.0, ge=0.0, le=1.0)
    respiratory_elevation: float = Field(0.0, ge=0.0, le=1.0)
    thermal_hotspot: float | None = None


@app.post("/camera/run")
def camera_run(req: CameraRunRequest) -> dict[str, Any]:
    """Replace the dashboard with a single camera-derived animal."""
    global _herd, _report
    obs = generate_observation(
        animal_id=req.animal_id,
        species=req.species,  # type: ignore[arg-type]
        lameness_severity=req.lameness_severity,
        respiratory_elevation=req.respiratory_elevation,
        thermal_hotspot=req.thermal_hotspot,
        seed=42,
    )
    _herd = [obs]
    _report = _engine.review(farm_id="WEBCAM_FARM", observations=_herd)
    return {"animal_id": req.animal_id, "activity_proxy": req.activity_proxy,
            "score_count": len(_report.scores), "alert_count": len(_report.alerts)}


@app.get("/export.html", response_class=HTMLResponse)
def export_html() -> str:
    rows: list[str] = []
    for s in _report.scores:
        cls = {"urgent": "u", "concern": "w", "well": "s"}.get(s.flag, "")
        rows.append(
            f"<tr><td>{s.animal_id}</td>"
            f"<td class='{cls}'><b>{s.flag}</b></td>"
            f"<td>{s.overall:.2f}</td>"
            f"<td>{s.gait:.2f}</td>"
            f"<td>{s.respiratory:.2f}</td>"
            f"<td>{s.thermal:.2f}</td></tr>"
        )
    rows_html = "\n".join(rows)
    alerts_html = "\n".join(
        f"<li>[{a.kind}] {a.animal_id}: {a.text}</li>" for a in _report.alerts
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8">
<title>triage4-farm — farm {_report.farm_id}</title>
<style>
body{{font:14px/1.5 system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem;
color:#1a1a2e;background:#f5faf2;}}
h1,h2{{margin-top:1.5em;}}table{{border-collapse:collapse;width:100%;}}
th,td{{padding:6px 10px;text-align:left;border-bottom:1px solid #d6dce6;}}
th{{background:#e2efd9;}}tr:hover td{{background:#fffceb;}}
td.u{{color:#a4262c;}}td.w{{color:#a86b00;}}td.s{{color:#107c10;}}
ul{{padding-left:1.2rem;}}
</style></head><body>
<h1>triage4-farm</h1>
<p>Farm <code>{_report.farm_id}</code> · {len(_report.scores)} animals reviewed · herd overall {_report.herd_overall:.2f}.</p>
<table><thead><tr><th>Animal</th><th>Flag</th><th>Overall</th>
<th>Gait</th><th>Respiratory</th><th>Thermal</th></tr></thead>
<tbody>{rows_html}</tbody></table>
<h2>Alerts</h2><ul>{alerts_html or "<li><i>none</i></li>"}</ul>
</body></html>"""
