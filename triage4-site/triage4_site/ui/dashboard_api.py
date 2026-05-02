"""FastAPI dashboard for triage4-site — safety-officer dashboard."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from ..sim.synthetic_shift import demo_shift, generate_observation
from ..site_monitor.monitoring_engine import SiteSafetyEngine

app = FastAPI(title="triage4-site API", version="0.1.0")

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

_SITE_ID = "DEMO_SITE"
_engine = SiteSafetyEngine()
_observations = demo_shift()
_report = _engine.review(site_id=_SITE_ID, observations=_observations)


def _seed() -> None:
    global _observations, _report
    _observations = demo_shift()
    _report = _engine.review(site_id=_SITE_ID, observations=_observations)


def _level_counts() -> dict[str, int]:
    counts: dict[str, int] = {"ok": 0, "watch": 0, "urgent": 0}
    for s in _report.scores:
        counts[s.alert_level] = counts.get(s.alert_level, 0) + 1
    return counts


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "service": "triage4-site", "version": "0.1.0",
        "site_id": _report.site_id,
        "worker_count": len(_report.scores),
        "alert_count": len(_report.alerts),
    }


@app.get("/report")
def report() -> dict[str, Any]:
    return {
        "site_id": _report.site_id,
        "worker_count": len(_report.scores),
        "level_counts": _level_counts(),
        "scores": [asdict(s) for s in _report.scores],
        "alerts": [asdict(a) for a in _report.alerts],
    }


@app.get("/workers")
def workers() -> list[dict[str, Any]]:
    return [asdict(s) for s in _report.scores]


@app.get("/workers/{token}")
def worker_by_token(token: str) -> dict[str, Any]:
    for s in _report.scores:
        if s.worker_token == token:
            return {
                **asdict(s),
                "alerts": [asdict(a) for a in _report.alerts if a.worker_token == token],
            }
    raise HTTPException(404, f"worker {token!r} not found")


@app.get("/alerts")
def alerts() -> list[dict[str, Any]]:
    return [asdict(a) for a in _report.alerts]


@app.post("/demo/reload")
def demo_reload() -> dict[str, Any]:
    _seed()
    return {"reloaded": True, "worker_count": len(_report.scores),
            "alert_count": len(_report.alerts)}





class CameraRunRequest(BaseModel):
    """Camera-driven worker observation. Low motion → fatigue (worker
    inactive); luminance variance → site condition. PPE compliance,
    unsafe lifting, heat stress need classifiers / sensors → sliders.
    """

    worker_token: str = Field("WEBCAM_WORKER", min_length=1, max_length=64)
    fatigue: float = Field(0.0, ge=0.0, le=1.0)
    ppe_compliance: float = Field(1.0, ge=0.0, le=1.0)
    unsafe_lifting: float = Field(0.0, ge=0.0, le=1.0)
    heat_stress: float = Field(0.0, ge=0.0, le=1.0)


@app.post("/camera/run")
def camera_run(req: CameraRunRequest) -> dict[str, Any]:
    """Replace the dashboard with a single camera-derived worker."""
    global _observations, _report
    obs = generate_observation(
        worker_token=req.worker_token,
        ppe_compliance=req.ppe_compliance,
        unsafe_lifting=req.unsafe_lifting,
        heat_stress=req.heat_stress,
        fatigue=req.fatigue,
        seed=42,
    )
    _observations = [obs]
    _report = _engine.review(site_id="WEBCAM_SITE", observations=_observations)
    return {"worker_token": req.worker_token, "fatigue": req.fatigue,
            "score_count": len(_report.scores), "alert_count": len(_report.alerts)}


@app.get("/export.html", response_class=HTMLResponse)
def export_html() -> str:
    rows: list[str] = []
    for s in _report.scores:
        cls = {"urgent": "u", "watch": "w", "ok": "s"}.get(s.alert_level, "")
        rows.append(
            f"<tr><td>{s.worker_token}</td>"
            f"<td class='{cls}'><b>{s.alert_level}</b></td>"
            f"<td>{s.overall:.2f}</td>"
            f"<td>{s.ppe_compliance:.2f}</td>"
            f"<td>{s.lifting_safety:.2f}</td>"
            f"<td>{s.heat_safety:.2f}</td>"
            f"<td>{s.fatigue_safety:.2f}</td></tr>"
        )
    rows_html = "\n".join(rows)
    alerts_html = "\n".join(
        f"<li>[{a.kind}] {a.worker_token}: {a.text}</li>" for a in _report.alerts
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8">
<title>triage4-site — site {_report.site_id}</title>
<style>
body{{font:14px/1.5 system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem;
color:#1a1a2e;background:#fbf8f0;}}
h1,h2{{margin-top:1.5em;}}table{{border-collapse:collapse;width:100%;}}
th,td{{padding:6px 10px;text-align:left;border-bottom:1px solid #d6dce6;}}
th{{background:#f3eee0;}}tr:hover td{{background:#fffceb;}}
td.u{{color:#a4262c;}}td.w{{color:#a86b00;}}td.s{{color:#107c10;}}
ul{{padding-left:1.2rem;}}
</style></head><body>
<h1>triage4-site</h1>
<p>Site <code>{_report.site_id}</code> · {len(_report.scores)} workers reviewed.</p>
<table><thead><tr><th>Worker</th><th>Level</th><th>Overall</th>
<th>PPE</th><th>Lifting</th><th>Heat</th><th>Fatigue</th></tr></thead>
<tbody>{rows_html}</tbody></table>
<h2>Alerts</h2><ul>{alerts_html or "<li><i>none</i></li>"}</ul>
</body></html>"""
