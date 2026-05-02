"""FastAPI dashboard for triage4-fit — coaching-session dashboard.

The fit engine is per-session (returns a single ``CoachBriefing``);
the dashboard exposes one session at a time. POST /demo/reload
regenerates with optional adjustments to the synthetic asymmetry
severity.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from ..core.enums import ExerciseKind
from ..form_check.rapid_form_engine import RapidFormEngine
from ..sim.synthetic_session import demo_session

app = FastAPI(title="triage4-fit API", version="0.1.0")

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

_engine = RapidFormEngine()
_DEFAULT_EXERCISE: ExerciseKind = "squat"
_DEFAULT_REPS = 5
_DEFAULT_ASYMMETRY = 0.35


def _build() -> Any:
    session = demo_session(
        _DEFAULT_EXERCISE,
        rep_count=_DEFAULT_REPS,
        asymmetry_severity=_DEFAULT_ASYMMETRY,
    )
    return _engine.review(session)


_briefing = _build()


def _seed() -> None:
    global _briefing
    _briefing = _build()


def _severity_counts() -> dict[str, int]:
    counts: dict[str, int] = {"ok": 0, "minor": 0, "severe": 0}
    for c in _briefing.cues:
        counts[c.severity] = counts.get(c.severity, 0) + 1
    return counts


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "service": "triage4-fit", "version": "0.1.0",
        "exercise": _briefing.session.exercise,
        "rep_count": _briefing.session.rep_count,
        "cue_count": len(_briefing.cues),
    }


@app.get("/report")
def report() -> dict[str, Any]:
    return {
        "exercise": _briefing.session.exercise,
        "rep_count": _briefing.session.rep_count,
        "session_overall": _briefing.session_overall,
        "recovery_quality": _briefing.recovery_quality,
        "severity_counts": _severity_counts(),
        "form_scores": [asdict(s) for s in _briefing.form_scores],
        "cues": [asdict(c) for c in _briefing.cues],
    }


@app.get("/reps")
def reps() -> list[dict[str, Any]]:
    return [asdict(s) for s in _briefing.form_scores]


@app.get("/reps/{rep_index}")
def rep_by_index(rep_index: int) -> dict[str, Any]:
    for s in _briefing.form_scores:
        if s.rep_index == rep_index:
            return {
                **asdict(s),
                "cues": [asdict(c) for c in _briefing.cues
                         if c.rep_index == rep_index],
            }
    raise HTTPException(404, f"rep {rep_index!r} not found")


@app.get("/cues")
def cues() -> list[dict[str, Any]]:
    return [asdict(c) for c in _briefing.cues]


@app.post("/demo/reload")
def demo_reload() -> dict[str, Any]:
    _seed()
    return {"reloaded": True, "rep_count": _briefing.session.rep_count,
            "cue_count": len(_briefing.cues)}


class CameraRunRequest(BaseModel):
    """Camera-driven session request.

    The browser computes ``asymmetry_severity`` from a captured webcam
    stream (left-vs-right luminance imbalance) and posts the scalar
    here. The server uses it as the asymmetry parameter for a fresh
    synthetic session and runs the engine.
    """

    asymmetry_severity: float = Field(0.35, ge=0.0, le=1.0)
    rep_count: int = Field(5, ge=1, le=20)
    exercise: ExerciseKind = "squat"


@app.post("/camera/run")
def camera_run(req: CameraRunRequest) -> dict[str, Any]:
    """Build a fresh briefing using the camera-derived asymmetry."""
    global _briefing
    session = demo_session(
        req.exercise,
        rep_count=req.rep_count,
        asymmetry_severity=req.asymmetry_severity,
    )
    _briefing = _engine.review(session)
    return {
        "asymmetry_severity": req.asymmetry_severity,
        "exercise": req.exercise,
        "rep_count": _briefing.session.rep_count,
        "session_overall": _briefing.session_overall,
        "cue_count": len(_briefing.cues),
    }


@app.get("/export.html", response_class=HTMLResponse)
def export_html() -> str:
    rows: list[str] = []
    for s in _briefing.form_scores:
        rows.append(
            f"<tr><td>#{s.rep_index}</td>"
            f"<td>{s.overall:.2f}</td>"
            f"<td>{s.symmetry:.2f}</td>"
            f"<td>{s.depth:.2f}</td>"
            f"<td>{s.tempo:.2f}</td></tr>"
        )
    rows_html = "\n".join(rows)
    cues_html = "\n".join(
        f"<li><b>{c.severity}</b> [{c.kind}] {c.text}</li>"
        for c in _briefing.cues
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8">
<title>triage4-fit — {_briefing.session.exercise} session</title>
<style>
body{{font:14px/1.5 system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem;
color:#1a1a2e;background:#f6f8f2;}}
h1,h2{{margin-top:1.5em;}}table{{border-collapse:collapse;width:100%;}}
th,td{{padding:6px 10px;text-align:left;border-bottom:1px solid #d6dce6;}}
th{{background:#e6ecd9;}}tr:hover td{{background:#fffceb;}}
ul{{padding-left:1.2rem;}}
</style></head><body>
<h1>triage4-fit</h1>
<p>Exercise <b>{_briefing.session.exercise}</b> · {_briefing.session.rep_count} reps · session overall {_briefing.session_overall:.2f}</p>
<table><thead><tr><th>Rep</th><th>Overall</th>
<th>Symmetry</th><th>Depth</th><th>Tempo</th></tr></thead>
<tbody>{rows_html}</tbody></table>
<h2>Coaching cues ({len(_briefing.cues)})</h2>
<ul>{cues_html or "<li><i>none</i></li>"}</ul>
</body></html>"""
