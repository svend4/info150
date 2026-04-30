"""FastAPI dashboard for triage4-clinic — telemedicine pre-screening."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from ..clinic_triage.triage_engine import ClinicalPreTriageEngine
from ..sim.synthetic_self_report import demo_submissions

app = FastAPI(title="triage4-clinic API", version="0.1.0")

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

_engine = ClinicalPreTriageEngine()


def _build() -> tuple[list, list]:
    subs = demo_submissions()
    reports = [_engine.review(s) for s in subs]
    return subs, reports


_submissions, _reports = _build()


def _seed() -> None:
    global _submissions, _reports
    _submissions, _reports = _build()


def _rec_counts() -> dict[str, int]:
    counts: dict[str, int] = {"self_care": 0, "schedule": 0, "urgent_review": 0}
    for r in _reports:
        counts[r.assessment.recommendation] = counts.get(r.assessment.recommendation, 0) + 1
    return counts


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "service": "triage4-clinic", "version": "0.1.0",
        "submission_count": len(_reports),
        "alert_count": sum(len(r.alerts) for r in _reports),
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
        "patient_token": r.patient_token,
        "assessment": asdict(r.assessment),
        "alert_count": len(r.alerts),
        "symptom_count": len(r.reported_symptoms),
    }


@app.get("/submissions")
def submissions() -> list[dict[str, Any]]:
    return [_summary(r) for r in _reports]


@app.get("/submissions/{token}")
def submission_by_token(token: str) -> dict[str, Any]:
    for r in _reports:
        if r.patient_token == token:
            return {
                "patient_token": r.patient_token,
                "assessment": asdict(r.assessment),
                "alerts": [asdict(a) for a in r.alerts],
                "readings": [asdict(reading) for reading in r.readings],
                "reported_symptoms": list(r.reported_symptoms),
            }
    raise HTTPException(404, f"submission {token!r} not found")


@app.get("/alerts")
def alerts() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in _reports:
        for a in r.alerts:
            out.append(asdict(a))
    return out


@app.post("/demo/reload")
def demo_reload() -> dict[str, Any]:
    _seed()
    return {"reloaded": True, "submission_count": len(_reports)}


@app.get("/export.html", response_class=HTMLResponse)
def export_html() -> str:
    rows: list[str] = []
    for r in _reports:
        a = r.assessment
        cls = {"urgent_review": "u", "schedule": "w", "self_care": "s"}.get(a.recommendation, "")
        rows.append(
            f"<tr><td>{r.patient_token}</td>"
            f"<td class='{cls}'><b>{a.recommendation}</b></td>"
            f"<td>{a.overall:.2f}</td>"
            f"<td>{a.cardiac_safety:.2f}</td>"
            f"<td>{a.respiratory_safety:.2f}</td>"
            f"<td>{a.acoustic_safety:.2f}</td>"
            f"<td>{a.postural_safety:.2f}</td>"
            f"<td>{len(r.alerts)}</td></tr>"
        )
    rows_html = "\n".join(rows)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8">
<title>triage4-clinic — submissions</title>
<style>
body{{font:14px/1.5 system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem;
color:#1a1a2e;background:#f1f6f9;}}
h1{{margin-top:1.5em;}}table{{border-collapse:collapse;width:100%;}}
th,td{{padding:6px 10px;text-align:left;border-bottom:1px solid #d6dce6;}}
th{{background:#dde7ec;}}tr:hover td{{background:#fffceb;}}
td.u{{color:#a4262c;}}td.w{{color:#a86b00;}}td.s{{color:#107c10;}}
</style></head><body>
<h1>triage4-clinic</h1>
<p>{len(_reports)} self-report submissions reviewed.</p>
<table><thead><tr><th>Patient</th><th>Recommendation</th><th>Overall</th>
<th>Cardiac</th><th>Respiratory</th><th>Acoustic</th><th>Postural</th><th>Alerts</th></tr></thead>
<tbody>{rows_html}</tbody></table>
</body></html>"""
