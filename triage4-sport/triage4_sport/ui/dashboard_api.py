"""FastAPI dashboard for triage4-sport — coach/trainer/physician."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from ..sim.synthetic_session import demo_baseline, demo_sessions, generate_observation
from ..sport_engine.monitoring_engine import SportPerformanceEngine

app = FastAPI(title="triage4-sport API", version="0.1.0")

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

_engine = SportPerformanceEngine()


def _build() -> tuple[list, list]:
    sessions = demo_sessions()
    baseline = demo_baseline()
    reports = [_engine.review(s, baseline=baseline) for s in sessions]
    return sessions, reports


_sessions, _reports = _build()


def _seed() -> None:
    global _sessions, _reports
    _sessions, _reports = _build()


def _band_counts() -> dict[str, int]:
    counts: dict[str, int] = {"steady": 0, "monitor": 0, "hold": 0}
    for r in _reports:
        counts[r.assessment.risk_band] = counts.get(r.assessment.risk_band, 0) + 1
    return counts


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "service": "triage4-sport", "version": "0.1.0",
        "session_count": len(_reports),
    }


@app.get("/report")
def report() -> dict[str, Any]:
    return {
        "session_count": len(_reports),
        "band_counts": _band_counts(),
        "sessions": [_summary(r) for r in _reports],
    }


def _summary(r: Any) -> dict[str, Any]:
    return {
        "athlete_token": r.athlete_token,
        "assessment": asdict(r.assessment),
        "coach_message_count": len(r.coach_messages),
        "trainer_note_count": len(r.trainer_notes),
        "has_physician_alert": r.physician_alert is not None,
    }


@app.get("/sessions")
def sessions() -> list[dict[str, Any]]:
    return [_summary(r) for r in _reports]


@app.get("/sessions/{token}")
def session_by_token(token: str) -> dict[str, Any]:
    for r, obs in zip(_reports, _sessions):
        if r.athlete_token == token:
            return {
                "athlete_token": r.athlete_token,
                "sport": getattr(obs, "sport", None),
                "session_duration_s": getattr(obs, "session_duration_s", None),
                "assessment": asdict(r.assessment),
                "coach_messages": [asdict(m) for m in r.coach_messages],
                "trainer_notes": [asdict(n) for n in r.trainer_notes],
                "physician_alert": asdict(r.physician_alert) if r.physician_alert else None,
            }
    raise HTTPException(404, f"session {token!r} not found")


@app.post("/demo/reload")
def demo_reload() -> dict[str, Any]:
    _seed()
    return {"reloaded": True, "session_count": len(_reports)}





class CameraRunRequest(BaseModel):
    """Camera-driven athlete session. Mean motion → workload intensity.
    Form asymmetry, recovery HR drop need pose detector / HR sensor →
    sliders / numeric inputs.
    """

    athlete_token: str = Field("WEBCAM_ATH", min_length=1, max_length=64)
    sport: str = "soccer"
    workload_intensity: float = Field(0.45, ge=0.0, le=1.0)
    form_asymmetry: float = Field(0.15, ge=0.0, le=1.0)
    recovery_drop_bpm: float = Field(32.0, ge=0.0, le=200.0)


@app.post("/camera/run")
def camera_run(req: CameraRunRequest) -> dict[str, Any]:
    """Replace the dashboard with a single camera-derived athlete session."""
    global _sessions, _reports
    obs = generate_observation(
        athlete_token=req.athlete_token,
        sport=req.sport,  # type: ignore[arg-type]
        form_asymmetry=req.form_asymmetry,
        workload_intensity=req.workload_intensity,
        recovery_drop_bpm=req.recovery_drop_bpm,
        seed=42,
    )
    sessions = [obs]
    baseline = demo_baseline()
    _sessions = sessions
    _reports = [_engine.review(o, baseline=baseline) for o in sessions]
    return {"athlete_token": req.athlete_token, "workload_intensity": req.workload_intensity,
            "report_count": len(_reports)}


@app.get("/export.html", response_class=HTMLResponse)
def export_html() -> str:
    rows: list[str] = []
    for r in _reports:
        a = r.assessment
        cls = {"hold": "u", "monitor": "w", "steady": "s"}.get(a.risk_band, "")
        rows.append(
            f"<tr><td>{r.athlete_token}</td>"
            f"<td class='{cls}'><b>{a.risk_band}</b></td>"
            f"<td>{a.overall:.2f}</td>"
            f"<td>{a.form_asymmetry_safety:.2f}</td>"
            f"<td>{a.workload_load_safety:.2f}</td>"
            f"<td>{a.recovery_hr_safety:.2f}</td>"
            f"<td>{a.baseline_deviation_safety:.2f}</td></tr>"
        )
    rows_html = "\n".join(rows)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8">
<title>triage4-sport — sessions</title>
<style>
body{{font:14px/1.5 system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem;
color:#1a1a2e;background:#f4f6fb;}}
h1{{margin-top:1.5em;}}table{{border-collapse:collapse;width:100%;}}
th,td{{padding:6px 10px;text-align:left;border-bottom:1px solid #d6dce6;}}
th{{background:#dee5f3;}}tr:hover td{{background:#fffceb;}}
td.u{{color:#a4262c;}}td.w{{color:#a86b00;}}td.s{{color:#107c10;}}
</style></head><body>
<h1>triage4-sport</h1>
<p>{len(_reports)} athlete sessions reviewed.</p>
<table><thead><tr><th>Athlete</th><th>Risk band</th><th>Overall</th>
<th>Form sym.</th><th>Workload</th><th>Recovery HR</th><th>Baseline dev.</th></tr></thead>
<tbody>{rows_html}</tbody></table>
</body></html>"""
