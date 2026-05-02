"""FastAPI dashboard for triage4-coast — coast-strip ops dashboard."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from ..coast_safety.coast_safety_engine import CoastSafetyEngine
from ..core.enums import ZoneKind
from ..sim.synthetic_coast import demo_coast, generate_zone_observation

app = FastAPI(title="triage4-coast API", version="0.1.0")

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

_COAST_ID = "DEMO_COAST"
_engine = CoastSafetyEngine()
_zones = demo_coast()
_report = _engine.review(coast_id=_COAST_ID, zones=_zones)


def _seed() -> None:
    global _zones, _report
    _zones = demo_coast()
    _report = _engine.review(coast_id=_COAST_ID, zones=_zones)


def _level_counts() -> dict[str, int]:
    counts: dict[str, int] = {"ok": 0, "watch": 0, "urgent": 0}
    for s in _report.scores:
        counts[s.alert_level] = counts.get(s.alert_level, 0) + 1
    return counts


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "service": "triage4-coast", "version": "0.1.0",
        "coast_id": _report.coast_id,
        "zone_count": len(_report.scores),
        "alert_count": len(_report.alerts),
    }


@app.get("/report")
def report() -> dict[str, Any]:
    return {
        "coast_id": _report.coast_id,
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
    """Camera-driven coast-zone request.

    The browser computes ``density_pressure`` (motion / variance
    proxy) and ``sun_intensity`` (luminance proxy) from a webcam
    stream. ``in_water_motion`` and ``lost_child_flag`` cannot be
    inferred from a single static camera, so the operator sets them
    via UI controls.
    """

    zone_id: str = Field("WEBCAM_ZONE", min_length=1, max_length=64)
    zone_kind: ZoneKind = "beach"
    density_pressure: float = Field(0.0, ge=0.0, le=1.0)
    in_water_motion: float = Field(0.0, ge=0.0, le=1.0)
    sun_intensity: float = Field(0.0, ge=0.0, le=1.0)
    lost_child_flag: bool = False


@app.post("/camera/run")
def camera_run(req: CameraRunRequest) -> dict[str, Any]:
    """Build a fresh single-zone report from camera-derived signals."""
    global _zones, _report
    cam_zone = generate_zone_observation(
        zone_id=req.zone_id,
        zone_kind=req.zone_kind,
        density_pressure=req.density_pressure,
        in_water_motion=req.in_water_motion,
        sun_intensity=req.sun_intensity,
        lost_child_flag=req.lost_child_flag,
    )
    _zones = [cam_zone]
    _report = _engine.review(coast_id="WEBCAM_COAST", zones=_zones)
    return {
        "zone_id": req.zone_id,
        "zone_kind": req.zone_kind,
        "density_pressure": req.density_pressure,
        "in_water_motion": req.in_water_motion,
        "sun_intensity": req.sun_intensity,
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
            f"<td>{s.drowning_safety:.2f}</td>"
            f"<td>{s.sun_safety:.2f}</td>"
            f"<td>{s.lost_child_safety:.2f}</td></tr>"
        )
    rows_html = "\n".join(rows)
    alerts_html = "\n".join(
        f"<li>[{a.kind}] {a.zone_id}: {a.text}</li>" for a in _report.alerts
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8">
<title>triage4-coast - {_report.coast_id}</title>
<style>
body{{font:14px/1.5 system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem;
color:#1a1a2e;background:#f4f7fa;}}
h1,h2{{margin-top:1.5em;}}table{{border-collapse:collapse;width:100%;}}
th,td{{padding:6px 10px;text-align:left;border-bottom:1px solid #d6dce6;}}
th{{background:#dde7e9;}}tr:hover td{{background:#fffceb;}}
td.u{{color:#a4262c;}}td.w{{color:#a86b00;}}td.s{{color:#107c10;}}
ul{{padding-left:1.2rem;}}
</style></head><body>
<h1>triage4-coast</h1>
<p>Coast <code>{_report.coast_id}</code> - {len(_report.scores)} zones reviewed.</p>
<table><thead><tr><th>Zone</th><th>Level</th><th>Overall</th>
<th>Density</th><th>Drowning</th><th>Sun</th><th>Lost-child</th></tr></thead>
<tbody>{rows_html}</tbody></table>
<h2>Alerts</h2><ul>{alerts_html or "<li><i>none</i></li>"}</ul>
</body></html>"""
