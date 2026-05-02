"""FastAPI dashboard for triage4-drive — dispatcher fleet dashboard.

The drive engine is per-window (returns ``tuple[FatigueScore,
list[DispatcherAlert]]``). The dashboard accumulates a single
DrivingSession aggregate. AlertLevel literal: ok / caution / critical.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from ..core.models import DrivingSession
from ..driver_monitor.monitoring_engine import DriverMonitoringEngine
from ..sim.synthetic_cab import demo_session, generate_observation

app = FastAPI(title="triage4-drive API", version="0.1.0")

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

_SESSION_ID = "DEMO_SESSION"
_engine = DriverMonitoringEngine()


def _build() -> tuple[list, DrivingSession]:
    windows = demo_session(session_id=_SESSION_ID)
    aggregate = DrivingSession(session_id=_SESSION_ID)
    for w in windows:
        score, alerts = _engine.review(w)
        aggregate.scores.append(score)
        aggregate.alerts.extend(alerts)
    return windows, aggregate


_windows, _report = _build()


def _seed() -> None:
    global _windows, _report
    _windows, _report = _build()


def _level_counts() -> dict[str, int]:
    counts: dict[str, int] = {"ok": 0, "caution": 0, "critical": 0}
    for s in _report.scores:
        counts[s.alert_level] = counts.get(s.alert_level, 0) + 1
    return counts


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "service": "triage4-drive", "version": "0.1.0",
        "session_id": _report.session_id,
        "window_count": _report.window_count,
        "alert_count": len(_report.alerts),
    }


@app.get("/report")
def report() -> dict[str, Any]:
    return {
        "session_id": _report.session_id,
        "window_count": _report.window_count,
        "level_counts": _level_counts(),
        "scores": [asdict(s) for s in _report.scores],
        "alerts": [asdict(a) for a in _report.alerts],
    }


@app.get("/windows")
def windows() -> list[dict[str, Any]]:
    """Per-window list. Note: indices used as identifier since
    FatigueScore.session_id is the cab session, not a window id."""
    return [{**asdict(s), "index": i} for i, s in enumerate(_report.scores)]


@app.get("/windows/{idx}")
def window_by_index(idx: int) -> dict[str, Any]:
    if idx < 0 or idx >= len(_report.scores):
        raise HTTPException(404, f"window index {idx} out of range")
    s = _report.scores[idx]
    # Drive alerts are per-session not per-window — surface all
    # alerts whose session_id matches the current cab session.
    return {
        **asdict(s),
        "index": idx,
        "alerts": [asdict(a) for a in _report.alerts if a.session_id == s.session_id],
    }


@app.get("/alerts")
def alerts() -> list[dict[str, Any]]:
    return [asdict(a) for a in _report.alerts]


@app.post("/demo/reload")
def demo_reload() -> dict[str, Any]:
    _seed()
    return {"reloaded": True, "window_count": _report.window_count,
            "alert_count": len(_report.alerts)}





class CameraRunRequest(BaseModel):
    """Camera-driven driver-monitor window. Low motion → drowsiness;
    erratic motion variance → distraction. Incapacitation needs slumped-
    pose detection → manual slider.
    """

    session_id: str = Field("WEBCAM_SESSION", min_length=1, max_length=64)
    drowsiness: float = Field(0.0, ge=0.0, le=1.0)
    distraction: float = Field(0.0, ge=0.0, le=1.0)
    incapacitation: float = Field(0.0, ge=0.0, le=1.0)


@app.post("/camera/run")
def camera_run(req: CameraRunRequest) -> dict[str, Any]:
    """Replace the dashboard with a single camera-derived driving window."""
    global _windows, _report
    obs = generate_observation(
        session_id=req.session_id,
        drowsiness=req.drowsiness,
        distraction=req.distraction,
        incapacitation=req.incapacitation,
        seed=42,
    )
    obs_list = [obs]
    aggregate = DrivingSession(session_id=req.session_id)
    for w in obs_list:
        score, alerts = _engine.review(w)
        aggregate.scores.append(score)
        aggregate.alerts.extend(alerts)
    _windows = obs_list
    _report = aggregate
    return {"session_id": req.session_id, "drowsiness": req.drowsiness,
            "score_count": len(_report.scores), "alert_count": len(_report.alerts)}


@app.get("/export.html", response_class=HTMLResponse)
def export_html() -> str:
    rows: list[str] = []
    for i, s in enumerate(_report.scores):
        cls = {"critical": "u", "caution": "w", "ok": "s"}.get(s.alert_level, "")
        rows.append(
            f"<tr><td>w{i:02d}</td>"
            f"<td class='{cls}'><b>{s.alert_level}</b></td>"
            f"<td>{s.overall:.2f}</td>"
            f"<td>{s.perclos:.2f}</td>"
            f"<td>{s.distraction:.2f}</td>"
            f"<td>{s.incapacitation:.2f}</td></tr>"
        )
    rows_html = "\n".join(rows)
    alerts_html = "\n".join(
        f"<li>[{a.kind}] {a.text}</li>" for a in _report.alerts
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8">
<title>triage4-drive — session {_report.session_id}</title>
<style>
body{{font:14px/1.5 system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem;
color:#1a1a2e;background:#f4f6fb;}}
h1,h2{{margin-top:1.5em;}}table{{border-collapse:collapse;width:100%;}}
th,td{{padding:6px 10px;text-align:left;border-bottom:1px solid #d6dce6;}}
th{{background:#dee5f3;}}tr:hover td{{background:#fffceb;}}
td.u{{color:#a4262c;}}td.w{{color:#a86b00;}}td.s{{color:#107c10;}}
ul{{padding-left:1.2rem;}}
</style></head><body>
<h1>triage4-drive</h1>
<p>Session <code>{_report.session_id}</code> · {_report.window_count} windows.</p>
<p><i>Note: channel scores are RISK scores — higher = worse (drowsiness, distraction).</i></p>
<table><thead><tr><th>Win</th><th>Level</th><th>Overall</th>
<th>PERCLOS</th><th>Distraction</th><th>Incapacitation</th></tr></thead>
<tbody>{rows_html}</tbody></table>
<h2>Alerts</h2><ul>{alerts_html or "<li><i>none</i></li>"}</ul>
</body></html>"""
