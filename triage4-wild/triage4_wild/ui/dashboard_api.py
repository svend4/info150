"""FastAPI dashboard for triage4-wild — ranger reserve dashboard."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from ..core.models import ReserveReport
from ..sim.synthetic_reserve import demo_observations
from ..wildlife_health.monitoring_engine import WildlifeHealthEngine

app = FastAPI(title="triage4-wild API", version="0.1.0")

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

_RESERVE_ID = "DEMO_RESERVE"
_engine = WildlifeHealthEngine()


def _build_report() -> tuple[list, ReserveReport]:
    obs_list = demo_observations()
    aggregate = ReserveReport(reserve_id=_RESERVE_ID)
    for obs in obs_list:
        single = _engine.review(obs, reserve_id=_RESERVE_ID)
        aggregate.scores.extend(single.scores)
        aggregate.alerts.extend(single.alerts)
    return obs_list, aggregate


_observations, _report = _build_report()


def _seed() -> None:
    global _observations, _report
    _observations, _report = _build_report()


def _level_counts() -> dict[str, int]:
    counts: dict[str, int] = {"ok": 0, "watch": 0, "urgent": 0}
    for s in _report.scores:
        counts[s.alert_level] = counts.get(s.alert_level, 0) + 1
    return counts


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "service": "triage4-wild", "version": "0.1.0",
        "reserve_id": _report.reserve_id,
        "observation_count": len(_report.scores),
        "alert_count": len(_report.alerts),
    }


@app.get("/report")
def report() -> dict[str, Any]:
    return {
        "reserve_id": _report.reserve_id,
        "observation_count": len(_report.scores),
        "level_counts": _level_counts(),
        "scores": [asdict(s) for s in _report.scores],
        "alerts": [asdict(a) for a in _report.alerts],
    }


@app.get("/observations")
def observations() -> list[dict[str, Any]]:
    return [asdict(s) for s in _report.scores]


@app.get("/observations/{token}")
def observation_by_token(token: str) -> dict[str, Any]:
    for s in _report.scores:
        if s.obs_token == token:
            return {
                **asdict(s),
                "alerts": [asdict(a) for a in _report.alerts if a.obs_token == token],
            }
    raise HTTPException(404, f"observation {token!r} not found")


@app.get("/alerts")
def alerts() -> list[dict[str, Any]]:
    return [asdict(a) for a in _report.alerts]


@app.post("/demo/reload")
def demo_reload() -> dict[str, Any]:
    _seed()
    return {"reloaded": True, "observation_count": len(_report.scores),
            "alert_count": len(_report.alerts)}


@app.get("/export.html", response_class=HTMLResponse)
def export_html() -> str:
    rows: list[str] = []
    for s in _report.scores:
        cls = {"urgent": "u", "watch": "w", "ok": "s"}.get(s.alert_level, "")
        rows.append(
            f"<tr><td>{s.obs_token}</td>"
            f"<td class='{cls}'><b>{s.alert_level}</b></td>"
            f"<td>{s.overall:.2f}</td>"
            f"<td>{s.gait_safety:.2f}</td>"
            f"<td>{s.thermal_safety:.2f}</td>"
            f"<td>{s.postural_safety:.2f}</td>"
            f"<td>{s.body_condition_safety:.2f}</td>"
            f"<td>{s.threat_signal:.2f}</td></tr>"
        )
    rows_html = "\n".join(rows)
    alerts_html = "\n".join(
        f"<li>[{a.kind}] {a.obs_token}: {a.text}</li>" for a in _report.alerts
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8">
<title>triage4-wild — reserve {_report.reserve_id}</title>
<style>
body{{font:14px/1.5 system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem;
color:#1a1a2e;background:#f6f3ed;}}
h1,h2{{margin-top:1.5em;}}table{{border-collapse:collapse;width:100%;}}
th,td{{padding:6px 10px;text-align:left;border-bottom:1px solid #d6dce6;}}
th{{background:#e9e2cd;}}tr:hover td{{background:#fffceb;}}
td.u{{color:#a4262c;}}td.w{{color:#a86b00;}}td.s{{color:#107c10;}}
ul{{padding-left:1.2rem;}}
</style></head><body>
<h1>triage4-wild</h1>
<p>Reserve <code>{_report.reserve_id}</code> · {len(_report.scores)} observations.</p>
<table><thead><tr><th>Obs</th><th>Level</th><th>Overall</th>
<th>Gait</th><th>Thermal</th><th>Posture</th><th>Body</th><th>Threat</th></tr></thead>
<tbody>{rows_html}</tbody></table>
<h2>Alerts</h2><ul>{alerts_html or "<li><i>none</i></li>"}</ul>
</body></html>"""
