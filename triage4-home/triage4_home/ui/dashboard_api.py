"""FastAPI dashboard for triage4-home — caregiver-facing dashboard.

The home engine is per-window (returns ``tuple[WellnessScore,
list[CaregiverAlert]]``); this dashboard loops over the demo day
series and accumulates a single HomeReport.

AlertLevel for home is ok / check_in / urgent (slightly different
from the rest of the catalog's ok/watch/urgent).
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from ..core.models import HomeReport
from ..home_monitor.monitoring_engine import HomeMonitoringEngine
from ..sim.synthetic_day import demo_baseline, demo_day_series, generate_observation

app = FastAPI(title="triage4-home API", version="0.1.0")

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

_RESIDENCE_ID = "DEMO_RESIDENCE"
_engine = HomeMonitoringEngine()


def _build_report() -> tuple[list, HomeReport]:
    windows = demo_day_series()
    baseline = demo_baseline()
    aggregate = HomeReport(residence_id=_RESIDENCE_ID)
    for w in windows:
        score, alerts = _engine.review(w, baseline=baseline)
        aggregate.scores.append(score)
        aggregate.alerts.extend(alerts)
    return windows, aggregate


_windows, _report = _build_report()


def _seed() -> None:
    global _windows, _report
    _windows, _report = _build_report()


def _level_counts() -> dict[str, int]:
    counts: dict[str, int] = {"ok": 0, "check_in": 0, "urgent": 0}
    for s in _report.scores:
        counts[s.alert_level] = counts.get(s.alert_level, 0) + 1
    return counts


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "service": "triage4-home", "version": "0.1.0",
        "residence_id": _report.residence_id,
        "window_count": _report.window_count,
        "alert_count": len(_report.alerts),
    }


@app.get("/report")
def report() -> dict[str, Any]:
    return {
        "residence_id": _report.residence_id,
        "window_count": _report.window_count,
        "level_counts": _level_counts(),
        "scores": [asdict(s) for s in _report.scores],
        "alerts": [asdict(a) for a in _report.alerts],
    }


@app.get("/windows")
def windows() -> list[dict[str, Any]]:
    return [asdict(s) for s in _report.scores]


@app.get("/windows/{window_id}")
def window_by_id(window_id: str) -> dict[str, Any]:
    for s in _report.scores:
        if s.window_id == window_id:
            return {
                **asdict(s),
                "alerts": [asdict(a) for a in _report.alerts if a.window_id == window_id],
            }
    raise HTTPException(404, f"window {window_id!r} not found")


@app.get("/alerts")
def alerts() -> list[dict[str, Any]]:
    return [asdict(a) for a in _report.alerts]


@app.post("/demo/reload")
def demo_reload() -> dict[str, Any]:
    _seed()
    return {"reloaded": True, "window_count": _report.window_count,
            "alert_count": len(_report.alerts)}





class CameraRunRequest(BaseModel):
    """Camera-driven home-resident observation. Low motion → activity
    deviation. Fall events need a dedicated detector → bool toggle.
    Mobility decline tracked longitudinally → manual slider.

    PRIVACY: in-home cameras are PII-adjacent. Developer-test only.
    """

    window_id: str = Field("WEBCAM_DAY", min_length=1, max_length=64)
    activity_deviation: float = Field(0.0, ge=0.0, le=1.0)
    mobility_decline: float = Field(0.0, ge=0.0, le=1.0)
    fall_event: bool = False


@app.post("/camera/run")
def camera_run(req: CameraRunRequest) -> dict[str, Any]:
    """Replace the dashboard with a single camera-derived home-day observation."""
    global _windows, _report
    obs = generate_observation(
        window_id=req.window_id,
        activity_deviation=req.activity_deviation,
        mobility_decline=req.mobility_decline,
        fall_event=req.fall_event,
        seed=42,
    )
    obs_list = [obs]
    baseline = demo_baseline()
    aggregate = HomeReport(residence_id="WEBCAM_HOME")
    for w in obs_list:
        score, alerts = _engine.review(w, baseline=baseline)
        aggregate.scores.append(score)
        aggregate.alerts.extend(alerts)
    _windows = obs_list
    _report = aggregate
    return {"window_id": req.window_id, "activity_deviation": req.activity_deviation,
            "score_count": len(_report.scores), "alert_count": len(_report.alerts)}


@app.get("/export.html", response_class=HTMLResponse)
def export_html() -> str:
    rows: list[str] = []
    for s in _report.scores:
        cls = {"urgent": "u", "check_in": "w", "ok": "s"}.get(s.alert_level, "")
        rows.append(
            f"<tr><td>{s.window_id}</td>"
            f"<td class='{cls}'><b>{s.alert_level}</b></td>"
            f"<td>{s.overall:.2f}</td>"
            f"<td>{s.fall_risk:.2f}</td>"
            f"<td>{s.activity_alignment:.2f}</td>"
            f"<td>{s.mobility_trend:.2f}</td></tr>"
        )
    rows_html = "\n".join(rows)
    alerts_html = "\n".join(
        f"<li>[{a.kind}] {a.window_id}: {a.text}</li>" for a in _report.alerts
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8">
<title>triage4-home — residence {_report.residence_id}</title>
<style>
body{{font:14px/1.5 system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem;
color:#1a1a2e;background:#f6f3f1;}}
h1,h2{{margin-top:1.5em;}}table{{border-collapse:collapse;width:100%;}}
th,td{{padding:6px 10px;text-align:left;border-bottom:1px solid #d6dce6;}}
th{{background:#ece4dd;}}tr:hover td{{background:#fffceb;}}
td.u{{color:#a4262c;}}td.w{{color:#a86b00;}}td.s{{color:#107c10;}}
ul{{padding-left:1.2rem;}}
</style></head><body>
<h1>triage4-home</h1>
<p>Residence <code>{_report.residence_id}</code> · {_report.window_count} windows.</p>
<table><thead><tr><th>Window</th><th>Level</th><th>Overall</th>
<th>Fall risk</th><th>Activity</th><th>Mobility trend</th></tr></thead>
<tbody>{rows_html}</tbody></table>
<h2>Alerts</h2><ul>{alerts_html or "<li><i>none</i></li>"}</ul>
</body></html>"""
