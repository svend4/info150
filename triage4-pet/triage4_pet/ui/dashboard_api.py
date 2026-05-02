"""FastAPI dashboard for triage4-pet — owner-submission dashboard.

Each PetReport bundles a per-pet assessment + vet summary + owner
messages. The dashboard aggregates multiple submissions for browsing.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from ..pet_triage.triage_engine import PetTriageEngine
from ..sim.synthetic_submission import demo_submissions, generate_observation

app = FastAPI(title="triage4-pet API", version="0.1.0")

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

_engine = PetTriageEngine()


def _build() -> tuple[list, list]:
    subs = demo_submissions()
    reports = [_engine.review(s) for s in subs]
    return subs, reports


_submissions, _reports = _build()


def _seed() -> None:
    global _submissions, _reports
    _submissions, _reports = _build()


def _rec_counts() -> dict[str, int]:
    counts: dict[str, int] = {"can_wait": 0, "routine_visit": 0, "see_today": 0}
    for r in _reports:
        counts[r.assessment.recommendation] = counts.get(r.assessment.recommendation, 0) + 1
    return counts


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "service": "triage4-pet", "version": "0.1.0",
        "submission_count": len(_reports),
    }


@app.get("/report")
def report() -> dict[str, Any]:
    return {
        "submission_count": len(_reports),
        "recommendation_counts": _rec_counts(),
        "submissions": [_summary(r) for r in _reports],
    }


def _summary(r: Any) -> dict[str, Any]:
    return {
        "pet_token": r.pet_token,
        "assessment": asdict(r.assessment),
    }


@app.get("/submissions")
def submissions() -> list[dict[str, Any]]:
    return [_summary(r) for r in _reports]


@app.get("/submissions/{token}")
def submission_by_token(token: str) -> dict[str, Any]:
    for r, sub in zip(_reports, _submissions):
        if r.pet_token == token:
            return {
                "pet_token": r.pet_token,
                "species": getattr(sub, "species", None),
                "age_years": getattr(sub, "age_years", None),
                "assessment": asdict(r.assessment),
                "vet_summary": r.vet_summary.text,
                "owner_messages": [asdict(m) for m in r.owner_messages],
            }
    raise HTTPException(404, f"submission {token!r} not found")


@app.post("/demo/reload")
def demo_reload() -> dict[str, Any]:
    _seed()
    return {"reloaded": True, "submission_count": len(_reports)}


class CameraRunRequest(BaseModel):
    """Camera-driven pet submission.

    Owner-camera input. Browser-side mean motion → activity proxy;
    *low* activity is treated as a pain/lethargy signal. Other channels
    (gait asymmetry, respiratory, cardiac, pain count) need pose/audio
    detectors a webcam alone cannot provide → manual sliders.
    """

    pet_token: str = Field("WEBCAM_PET", min_length=1, max_length=64)
    species: str = "dog"
    age_years: float = Field(5.0, ge=0.0, le=30.0)
    activity_proxy: float = Field(0.0, ge=0.0, le=1.0)
    gait_asymmetry: float = Field(0.0, ge=0.0, le=1.0)
    respiratory_elevation: float = Field(0.0, ge=0.0, le=1.0)
    cardiac_elevation: float = Field(0.0, ge=0.0, le=1.0)
    pain_behavior_count: int = Field(0, ge=0, le=10)


@app.post("/camera/run")
def camera_run(req: CameraRunRequest) -> dict[str, Any]:
    """Replace the dashboard with a single camera-derived submission."""
    global _submissions, _reports
    obs = generate_observation(
        pet_token=req.pet_token,
        species=req.species,  # type: ignore[arg-type]
        age_years=req.age_years,
        gait_asymmetry=req.gait_asymmetry,
        respiratory_elevation=req.respiratory_elevation,
        cardiac_elevation=req.cardiac_elevation,
        pain_behavior_count=req.pain_behavior_count,
        seed=42,
    )
    _submissions = [obs]
    _reports = [_engine.review(obs)]
    return {
        "pet_token": req.pet_token,
        "activity_proxy": req.activity_proxy,
        "submission_count": len(_reports),
        "recommendation": _reports[0].assessment.recommendation,
    }


@app.get("/export.html", response_class=HTMLResponse)
def export_html() -> str:
    rows: list[str] = []
    for r in _reports:
        a = r.assessment
        cls = {"see_today": "u", "routine_visit": "w", "can_wait": "s"}.get(a.recommendation, "")
        rows.append(
            f"<tr><td>{r.pet_token}</td>"
            f"<td class='{cls}'><b>{a.recommendation}</b></td>"
            f"<td>{a.overall:.2f}</td>"
            f"<td>{a.gait_safety:.2f}</td>"
            f"<td>{a.respiratory_safety:.2f}</td>"
            f"<td>{a.cardiac_safety:.2f}</td>"
            f"<td>{a.pain_safety:.2f}</td></tr>"
        )
    rows_html = "\n".join(rows)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8">
<title>triage4-pet — submissions</title>
<style>
body{{font:14px/1.5 system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem;
color:#1a1a2e;background:#f8f3f8;}}
h1{{margin-top:1.5em;}}table{{border-collapse:collapse;width:100%;}}
th,td{{padding:6px 10px;text-align:left;border-bottom:1px solid #d6dce6;}}
th{{background:#eedeea;}}tr:hover td{{background:#fffceb;}}
td.u{{color:#a4262c;}}td.w{{color:#a86b00;}}td.s{{color:#107c10;}}
</style></head><body>
<h1>triage4-pet</h1>
<p>{len(_reports)} owner submissions reviewed.</p>
<table><thead><tr><th>Pet</th><th>Recommendation</th><th>Overall</th>
<th>Gait</th><th>Respiratory</th><th>Cardiac</th><th>Pain</th></tr></thead>
<tbody>{rows_html}</tbody></table>
</body></html>"""
