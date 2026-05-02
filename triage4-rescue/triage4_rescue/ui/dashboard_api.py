"""FastAPI dashboard for triage4-rescue — sibling-level Web UI.

Mirrors the architectural pattern of the flagship's
``triage4.ui.dashboard_api`` but scoped to the rescue domain:
START / JumpSTART tagging of civilian mass-casualty incidents.
The endpoint set is deliberately small — sibling dashboards are
single-page; multi-page navigation belongs in domain-specific
applications that consume this API.

Endpoints (all GET unless noted):
    GET  /health                  — service status + casualty count
    GET  /incident                — current incident report (JSON)
    GET  /casualties              — list of triage assessments
    GET  /casualties/{id}         — one assessment + its cues
    GET  /alerts                  — list of responder cues
    POST /demo/reload             — re-seed with the demo incident
    GET  /export.html             — self-contained offline HTML

CORS is permissive for the standard Vite dev server origins
(http://localhost:5173 and ports 4173/preview); it is NOT enabled
with credentials, matching the same flagship convention.

This module is **opt-in**: the imports here pull in fastapi +
uvicorn, which live in the ``[ui]`` extra of ``pyproject.toml``.
The rest of triage4-rescue does not depend on either.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from ..core.enums import VALID_TAGS
from ..sim.synthetic_incident import demo_incident, generate_casualty
from ..triage_protocol.protocol_engine import StartProtocolEngine

app = FastAPI(title="triage4-rescue API", version="0.1.0")

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

_INCIDENT_ID = "DEMO_INCIDENT"

# Module-level state — single in-memory incident, re-seeded via
# ``/demo/reload``. Acceptable for a sibling dashboard; production
# deployments would inject this through dependency-injection.
_engine = StartProtocolEngine()
_casualties = demo_incident(incident_id=_INCIDENT_ID)
_report = _engine.review(incident_id=_INCIDENT_ID, casualties=_casualties)


def _seed() -> None:
    """Re-build the in-memory state from the synthetic demo."""
    global _casualties, _report
    _casualties = demo_incident(incident_id=_INCIDENT_ID)
    _report = _engine.review(incident_id=_INCIDENT_ID, casualties=_casualties)


def _counts() -> dict[str, int]:
    return {tag: len(_report.assessments_with_tag(tag)) for tag in VALID_TAGS}


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "service": "triage4-rescue",
        "version": "0.1.0",
        "incident_id": _report.incident_id,
        "casualty_count": _report.casualty_count,
    }


@app.get("/incident")
def incident() -> dict[str, Any]:
    """Full incident report — assessments, cues, summary counts."""
    return {
        "incident_id": _report.incident_id,
        "casualty_count": _report.casualty_count,
        "counts": _counts(),
        "assessments": [asdict(a) for a in _report.assessments],
        "cues": [asdict(c) for c in _report.cues],
    }


@app.get("/casualties")
def casualties() -> list[dict[str, Any]]:
    """Per-casualty list — assessment + age group + reasoning."""
    by_id = {c.casualty_id: c for c in _casualties}
    out: list[dict[str, Any]] = []
    for a in _report.assessments:
        out.append(
            {
                "casualty_id": a.casualty_id,
                "tag": a.tag,
                "age_group": a.age_group,
                "age_years": getattr(by_id.get(a.casualty_id), "age_years", None),
                "reasoning": a.reasoning,
                "flag_for_secondary_review": a.flag_for_secondary_review,
            }
        )
    return out


@app.get("/casualties/{casualty_id}")
def casualty_by_id(casualty_id: str) -> dict[str, Any]:
    for a in _report.assessments:
        if a.casualty_id == casualty_id:
            return {
                "casualty_id": a.casualty_id,
                "tag": a.tag,
                "age_group": a.age_group,
                "reasoning": a.reasoning,
                "flag_for_secondary_review": a.flag_for_secondary_review,
                "cues": [
                    asdict(c) for c in _report.cues
                    if c.casualty_id == casualty_id
                ],
            }
    raise HTTPException(
        status_code=404,
        detail=f"casualty {casualty_id!r} not found",
    )


@app.get("/alerts")
def alerts() -> list[dict[str, Any]]:
    """All responder cues across the incident."""
    return [asdict(c) for c in _report.cues]


@app.post("/demo/reload")
def demo_reload() -> dict[str, Any]:
    """Re-seed with a fresh synthetic incident."""
    _seed()
    return {
        "reloaded": True,
        "incident_id": _report.incident_id,
        "casualty_count": _report.casualty_count,
    }





class CameraRunRequest(BaseModel):
    """Camera-driven mass-casualty triage. Operator selects a profile
    (RESPIRATING / AMBULATORY / UNRESPONSIVE / DECEASED). Motion +
    variance are echoed back as scene context — START tags are clinical
    decisions, not camera output.

    STRONG PRIVACY: PHI-equivalent footage. Developer-test only.
    """

    casualty_id: str = Field("WEBCAM_CASUALTY", min_length=1, max_length=64)
    profile: str = "AMBULATORY"
    scene_activity: float = Field(0.0, ge=0.0, le=1.0)
    scene_complexity: float = Field(0.0, ge=0.0, le=1.0)


@app.post("/camera/run")
def camera_run(req: CameraRunRequest) -> dict[str, Any]:
    """Replace the dashboard with a single camera-derived casualty."""
    global _casualties, _report
    obs = generate_casualty(
        casualty_id=req.casualty_id,
        profile=req.profile,  # type: ignore[arg-type]
        seed=42,
    )
    _casualties = [obs]
    _report = _engine.review(incident_id="WEBCAM_INCIDENT", casualties=_casualties)
    return {"casualty_id": req.casualty_id, "profile": req.profile,
            "scene_activity": req.scene_activity,
            "scene_complexity": req.scene_complexity,
            "tag_count": len(_report.assessments)}


@app.get("/export.html", response_class=HTMLResponse)
def export_html() -> str:
    """Self-contained offline HTML snapshot — no JS, no fetch."""
    rows: list[str] = []
    for a in _report.assessments:
        flag = " [secondary]" if a.flag_for_secondary_review else ""
        rows.append(
            f"<tr><td>{a.casualty_id}</td>"
            f"<td><b>{a.tag}</b>{flag}</td>"
            f"<td>{a.age_group}</td>"
            f"<td>{a.reasoning}</td></tr>"
        )
    rows_html = "\n".join(rows)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8">
<title>triage4-rescue — incident {_report.incident_id}</title>
<style>
body {{ font: 14px/1.5 system-ui; max-width: 960px; margin: 2rem auto;
       padding: 0 1rem; color:#1a1a2e; background:#f7f8fb; }}
h1 {{ margin-top: 0; }} table {{ border-collapse: collapse; width:100%; }}
th, td {{ padding: 6px 10px; text-align:left; border-bottom: 1px solid #e0e3ea; }}
th {{ background:#eef1f8; }} tr:hover td {{ background:#fffceb; }}
</style></head><body>
<h1>triage4-rescue</h1>
<p>Incident <code>{_report.incident_id}</code> · {_report.casualty_count} casualties tagged.</p>
<table><thead><tr><th>Casualty</th><th>Tag</th><th>Age group</th><th>Reasoning</th></tr></thead>
<tbody>{rows_html}</tbody></table>
</body></html>"""
