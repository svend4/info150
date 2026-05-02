"""FastAPI dashboard for triage4-crowd — venue ops dashboard."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from ..core.enums import ZoneKind
from ..sim.synthetic_venue import demo_venue, generate_zone_observation
from ..venue_monitor.monitoring_engine import VenueMonitorEngine

app = FastAPI(title="triage4-crowd API", version="0.1.0")

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

_VENUE_ID = "DEMO_VENUE"
_engine = VenueMonitorEngine()
_zones = demo_venue()
_report = _engine.review(venue_id=_VENUE_ID, zones=_zones)


def _seed() -> None:
    global _zones, _report
    _zones = demo_venue()
    _report = _engine.review(venue_id=_VENUE_ID, zones=_zones)


def _level_counts() -> dict[str, int]:
    counts: dict[str, int] = {"ok": 0, "watch": 0, "urgent": 0}
    for s in _report.scores:
        counts[s.alert_level] = counts.get(s.alert_level, 0) + 1
    return counts


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "service": "triage4-crowd", "version": "0.1.0",
        "venue_id": _report.venue_id,
        "zone_count": len(_report.scores),
        "alert_count": len(_report.alerts),
    }


@app.get("/report")
def report() -> dict[str, Any]:
    return {
        "venue_id": _report.venue_id,
        "zone_count": len(_report.scores),
        "level_counts": _level_counts(),
        "scores": [asdict(s) for s in _report.scores],
        "alerts": [asdict(a) for a in _report.alerts],
    }


@app.get("/zones")
def zones() -> list[dict[str, Any]]:
    return [asdict(s) for s in _report.scores]


@app.get("/zones/{zone_id}")
def zone_by_id(zone_id: str) -> dict[str, Any]:
    for s in _report.scores:
        if s.zone_id == zone_id:
            return {
                **asdict(s),
                "alerts": [asdict(a) for a in _report.alerts if a.zone_id == zone_id],
            }
    raise HTTPException(404, f"zone {zone_id!r} not found")


@app.get("/alerts")
def alerts() -> list[dict[str, Any]]:
    return [asdict(a) for a in _report.alerts]


@app.post("/demo/reload")
def demo_reload() -> dict[str, Any]:
    _seed()
    return {"reloaded": True, "zone_count": len(_report.scores),
            "alert_count": len(_report.alerts)}


class CameraRunRequest(BaseModel):
    """Camera-driven zone request.

    The browser computes ``flow_compaction`` (inter-frame motion proxy)
    and ``density_pressure`` (frame-variance proxy) from a captured
    webcam stream. Pressure and medical-rate cannot be inferred from a
    single 2D camera, so the user sets them via UI sliders. The server
    builds one synthetic zone with these parameters, runs the engine,
    and replaces the in-memory report.
    """

    zone_id: str = Field("WEBCAM_ZONE", min_length=1, max_length=64)
    zone_kind: ZoneKind = "standing"
    flow_compaction: float = Field(0.0, ge=0.0, le=1.0)
    density_pressure: float = Field(0.0, ge=0.0, le=1.0)
    pressure_level: float = Field(0.0, ge=0.0, le=1.0)
    medical_rate: float = Field(0.0, ge=0.0, le=1.0)


@app.post("/camera/run")
def camera_run(req: CameraRunRequest) -> dict[str, Any]:
    """Build a fresh single-zone report from camera-derived signals."""
    global _zones, _report
    cam_zone = generate_zone_observation(
        zone_id=req.zone_id,
        zone_kind=req.zone_kind,
        density_pressure=req.density_pressure,
        flow_compaction=req.flow_compaction,
        pressure_level=req.pressure_level,
        medical_rate=req.medical_rate,
        seed=42,
    )
    _zones = [cam_zone]
    _report = _engine.review(venue_id="WEBCAM_VENUE", zones=_zones)
    return {
        "zone_id": req.zone_id,
        "zone_kind": req.zone_kind,
        "flow_compaction": req.flow_compaction,
        "density_pressure": req.density_pressure,
        "zone_count": len(_report.scores),
        "alert_count": len(_report.alerts),
    }


@app.get("/export.html", response_class=HTMLResponse)
def export_html() -> str:
    rows: list[str] = []
    for s in _report.scores:
        cls = {"urgent": "u", "watch": "w", "ok": "s"}.get(s.alert_level, "")
        rows.append(
            f"<tr><td>{s.zone_id}</td>"
            f"<td class='{cls}'><b>{s.alert_level}</b></td>"
            f"<td>{s.overall:.2f}</td>"
            f"<td>{s.density_safety:.2f}</td>"
            f"<td>{s.flow_safety:.2f}</td>"
            f"<td>{s.pressure_safety:.2f}</td>"
            f"<td>{s.medical_safety:.2f}</td></tr>"
        )
    rows_html = "\n".join(rows)
    alerts_html = "\n".join(
        f"<li>[{a.kind}] {a.zone_id}: {a.text}</li>" for a in _report.alerts
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8">
<title>triage4-crowd — venue {_report.venue_id}</title>
<style>
body{{font:14px/1.5 system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem;
color:#1a1a2e;background:#f4f5fa;}}
h1,h2{{margin-top:1.5em;}}table{{border-collapse:collapse;width:100%;}}
th,td{{padding:6px 10px;text-align:left;border-bottom:1px solid #d6dce6;}}
th{{background:#e6e9f3;}}tr:hover td{{background:#fffceb;}}
td.u{{color:#a4262c;}}td.w{{color:#a86b00;}}td.s{{color:#107c10;}}
ul{{padding-left:1.2rem;}}
</style></head><body>
<h1>triage4-crowd</h1>
<p>Venue <code>{_report.venue_id}</code> · {len(_report.scores)} zones reviewed.</p>
<table><thead><tr><th>Zone</th><th>Level</th><th>Overall</th>
<th>Density</th><th>Flow</th><th>Pressure</th><th>Medical</th></tr></thead>
<tbody>{rows_html}</tbody></table>
<h2>Alerts</h2><ul>{alerts_html or "<li><i>none</i></li>"}</ul>
</body></html>"""
