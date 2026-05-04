"""FastAPI dashboard for triage4-desk — desk-worker advisory.

The desk engine is per-session (returns a single ``DeskAdvisory``).
POST /demo/reload regenerates with the default synthetic session.
POST /camera/run accepts browser-derived signals and rebuilds the
advisory.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from ..core.enums import WorkMode
from ..desk_assistant.desk_assistant import DeskAssistant
from ..sim.synthetic_desk import demo_session, generate_session

app = FastAPI(title="triage4-desk API", version="0.1.0")

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

_engine = DeskAssistant()


def _build() -> Any:
    return _engine.review(demo_session())


_advisory = _build()


def _seed() -> None:
    global _advisory
    _advisory = _build()


def _severity_counts() -> dict[str, int]:
    counts: dict[str, int] = {"ok": 0, "minor": 0, "severe": 0}
    for c in _advisory.cues:
        counts[c.severity] = counts.get(c.severity, 0) + 1
    return counts


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "service": "triage4-desk", "version": "0.1.0",
        "worker_id": _advisory.session.worker_id,
        "work_mode": _advisory.session.work_mode,
        "cue_count": len(_advisory.cues),
    }


@app.get("/report")
def report() -> dict[str, Any]:
    s = _advisory.session
    return {
        "worker_id": s.worker_id,
        "work_mode": s.work_mode,
        "session_min": s.session_min,
        "minutes_since_break": s.minutes_since_break,
        "minutes_since_stretch": s.minutes_since_stretch,
        "fatigue_index": _advisory.fatigue_index,
        "hydration_due": _advisory.hydration_due,
        "eye_break_due": _advisory.eye_break_due,
        "microbreak_due": _advisory.microbreak_due,
        "stretch_due": _advisory.stretch_due,
        "posture_advisory": _advisory.posture_advisory,
        "drowsiness_alert": _advisory.drowsiness_alert,
        "distraction_alert": _advisory.distraction_alert,
        "overall_safety": _advisory.overall_safety,
        "severity_counts": _severity_counts(),
        "cues": [asdict(c) for c in _advisory.cues],
    }


@app.get("/cues")
def cues() -> list[dict[str, Any]]:
    return [asdict(c) for c in _advisory.cues]


@app.post("/demo/reload")
def demo_reload() -> dict[str, Any]:
    _seed()
    return {
        "reloaded": True,
        "worker_id": _advisory.session.worker_id,
        "cue_count": len(_advisory.cues),
    }


class CameraRunRequest(BaseModel):
    """Camera-driven session review.

    The browser collects ~30 frames, computes inter-frame motion
    (typing-rhythm proxy) and mean luminance (ambient light), then
    posts these together with operator-supplied session/break
    timings, posture self-rating, and optional HR.
    """

    worker_id: str = Field("WEBCAM_W", min_length=1, max_length=64)
    work_mode: WorkMode = "office"
    session_min: float = Field(35.0, ge=0.0, le=24 * 60)
    minutes_since_break: float = Field(15.0, ge=0.0, le=24 * 60)
    minutes_since_stretch: float = Field(60.0, ge=0.0, le=24 * 60)
    typing_intensity: float = Field(0.4, ge=0.0, le=1.0)
    screen_motion_proxy: float = Field(0.3, ge=0.0, le=1.0)
    ambient_light_proxy: float = Field(0.5, ge=0.0, le=1.0)
    posture_quality: float = Field(0.85, ge=0.0, le=1.0)
    drowsiness_signal: float = Field(0.0, ge=0.0, le=1.0)
    distraction_signal: float = Field(0.0, ge=0.0, le=1.0)
    air_temp_c: float | None = Field(None, ge=-10.0, le=50.0)
    hr_bpm: float | None = Field(None, ge=30.0, le=220.0)


@app.post("/camera/run")
def camera_run(req: CameraRunRequest) -> dict[str, Any]:
    """Replace the dashboard with a camera-derived advisory."""
    global _advisory
    s = generate_session(
        worker_id=req.worker_id,
        work_mode=req.work_mode,
        session_min=req.session_min,
        minutes_since_break=req.minutes_since_break,
        minutes_since_stretch=req.minutes_since_stretch,
        typing_intensity=req.typing_intensity,
        screen_motion_proxy=req.screen_motion_proxy,
        ambient_light_proxy=req.ambient_light_proxy,
        posture_quality=req.posture_quality,
        drowsiness_signal=req.drowsiness_signal,
        distraction_signal=req.distraction_signal,
        air_temp_c=req.air_temp_c,
        hr_bpm=req.hr_bpm,
    )
    _advisory = _engine.review(s)
    return {
        "worker_id": s.worker_id,
        "work_mode": s.work_mode,
        "fatigue_index": _advisory.fatigue_index,
        "posture_advisory": _advisory.posture_advisory,
        "overall_safety": _advisory.overall_safety,
        "cue_count": len(_advisory.cues),
    }


@app.get("/export.html", response_class=HTMLResponse)
def export_html() -> str:
    s = _advisory.session
    cues_html = "\n".join(
        f"<li><b>{c.severity}</b> [{c.kind}] {c.text}</li>"
        for c in _advisory.cues
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8">
<title>triage4-desk — worker {s.worker_id}</title>
<style>
body{{font:14px/1.5 system-ui;max-width:900px;margin:2rem auto;padding:0 1rem;
color:#1a2630;background:#f6f7fa;}}
h1,h2{{margin-top:1.5em;}}table{{border-collapse:collapse;width:100%;}}
th,td{{padding:6px 10px;text-align:left;border-bottom:1px solid #d6dce6;}}
th{{background:#e6ecf3;}}ul{{padding-left:1.2rem;}}
</style></head><body>
<h1>triage4-desk</h1>
<p>Worker <b>{s.worker_id}</b> · {s.work_mode} · session {s.session_min:.0f} min · break {s.minutes_since_break:.0f} min ago</p>
<table>
<tr><th>Channel</th><th>Value</th></tr>
<tr><td>fatigue_index</td><td>{_advisory.fatigue_index:.2f}</td></tr>
<tr><td>hydration_due</td><td>{_advisory.hydration_due}</td></tr>
<tr><td>eye_break_due</td><td>{_advisory.eye_break_due}</td></tr>
<tr><td>microbreak_due</td><td>{_advisory.microbreak_due}</td></tr>
<tr><td>stretch_due</td><td>{_advisory.stretch_due}</td></tr>
<tr><td>posture_advisory</td><td>{_advisory.posture_advisory}</td></tr>
<tr><td>drowsiness_alert</td><td>{_advisory.drowsiness_alert}</td></tr>
<tr><td>distraction_alert</td><td>{_advisory.distraction_alert}</td></tr>
<tr><td>overall_safety</td><td>{_advisory.overall_safety:.2f}</td></tr>
</table>
<h2>Coaching cues ({len(_advisory.cues)})</h2>
<ul>{cues_html or "<li><i>none</i></li>"}</ul>
</body></html>"""
