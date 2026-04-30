"""FastAPI dashboard for triage4-aqua — sibling-level Web UI.

Single-page lifeguard support dashboard. Shows per-swimmer scores
(submersion / IDR / absent / distress / overall) and lifeguard
alerts. Mirrors the rescue/fish pilot pattern.

Endpoints (all GET unless noted):
    GET  /health               — service status + counts
    GET  /report               — full PoolReport (JSON)
    GET  /swimmers             — list of AquaticScore rows
    GET  /swimmers/{token}     — one swimmer's score + alerts
    GET  /alerts               — list of LifeguardAlerts
    POST /demo/reload          — re-seed with the demo pool
    GET  /export.html          — self-contained offline HTML

CORS is permissive for the standard Vite dev server origins.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from ..pool_watch.monitoring_engine import PoolWatchEngine
from ..sim.synthetic_pool import demo_pool

app = FastAPI(title="triage4-aqua API", version="0.1.0")

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

_POOL_ID = "DEMO_POOL"
_engine = PoolWatchEngine()
_observations = demo_pool()
_report = _engine.review(pool_id=_POOL_ID, observations=_observations)


def _seed() -> None:
    global _observations, _report
    _observations = demo_pool()
    _report = _engine.review(pool_id=_POOL_ID, observations=_observations)


def _level_counts() -> dict[str, int]:
    counts: dict[str, int] = {"ok": 0, "watch": 0, "urgent": 0}
    for s in _report.scores:
        counts[s.alert_level] = counts.get(s.alert_level, 0) + 1
    return counts


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "service": "triage4-aqua",
        "version": "0.1.0",
        "pool_id": _report.pool_id,
        "swimmer_count": len(_report.scores),
        "alert_count": len(_report.alerts),
    }


@app.get("/report")
def report() -> dict[str, Any]:
    return {
        "pool_id": _report.pool_id,
        "swimmer_count": len(_report.scores),
        "level_counts": _level_counts(),
        "scores": [asdict(s) for s in _report.scores],
        "alerts": [asdict(a) for a in _report.alerts],
    }


@app.get("/swimmers")
def swimmers() -> list[dict[str, Any]]:
    return [asdict(s) for s in _report.scores]


@app.get("/swimmers/{token}")
def swimmer_by_token(token: str) -> dict[str, Any]:
    for s in _report.scores:
        if s.swimmer_token == token:
            return {
                **asdict(s),
                "alerts": [
                    asdict(a) for a in _report.alerts
                    if a.swimmer_token == token
                ],
            }
    raise HTTPException(404, f"swimmer {token!r} not found")


@app.get("/alerts")
def alerts() -> list[dict[str, Any]]:
    return [asdict(a) for a in _report.alerts]


@app.post("/demo/reload")
def demo_reload() -> dict[str, Any]:
    _seed()
    return {
        "reloaded": True,
        "pool_id": _report.pool_id,
        "swimmer_count": len(_report.scores),
        "alert_count": len(_report.alerts),
    }


@app.get("/export.html", response_class=HTMLResponse)
def export_html() -> str:
    rows: list[str] = []
    for s in _report.scores:
        cls = {"urgent": "u", "watch": "w", "ok": "s"}.get(s.alert_level, "")
        rows.append(
            f"<tr><td>{s.swimmer_token}</td>"
            f"<td class='{cls}'><b>{s.alert_level}</b></td>"
            f"<td>{s.overall:.2f}</td>"
            f"<td>{s.submersion_safety:.2f}</td>"
            f"<td>{s.idr_safety:.2f}</td>"
            f"<td>{s.absent_safety:.2f}</td>"
            f"<td>{s.distress_safety:.2f}</td></tr>"
        )
    rows_html = "\n".join(rows)
    alerts_html = "\n".join(
        f"<li>[{a.kind}] {a.swimmer_token}: {a.text}</li>"
        for a in _report.alerts
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8">
<title>triage4-aqua — pool {_report.pool_id}</title>
<style>
body{{font:14px/1.5 system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem;
color:#1a1a2e;background:#f0f7fb;}}
h1,h2{{margin-top:1.5em;}}table{{border-collapse:collapse;width:100%;}}
th,td{{padding:6px 10px;text-align:left;border-bottom:1px solid #d6dce6;}}
th{{background:#dfeaf3;}}tr:hover td{{background:#fffceb;}}
td.u{{color:#a4262c;}}td.w{{color:#a86b00;}}td.s{{color:#107c10;}}
ul{{padding-left:1.2rem;}}
</style></head><body>
<h1>triage4-aqua</h1>
<p>Pool <code>{_report.pool_id}</code> · {len(_report.scores)} swimmers reviewed.</p>
<table><thead><tr><th>Swimmer</th><th>Level</th><th>Overall</th>
<th>Submersion</th><th>IDR</th><th>Absent</th><th>Distress</th></tr></thead>
<tbody>{rows_html}</tbody></table>
<h2>Alerts</h2><ul>{alerts_html or "<li><i>none</i></li>"}</ul>
</body></html>"""
