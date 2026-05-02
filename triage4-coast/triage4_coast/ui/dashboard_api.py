"""FastAPI dashboard for triage4-coast — coast-strip ops dashboard."""

from __future__ import annotations

import time
from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from ..coast_safety.coast_safety_engine import CoastSafetyEngine
from ..core.enums import ZoneKind
from ..sim.synthetic_coast import demo_coast, generate_zone_observation
from . import aggregates, broadcast, camera_health, groups, history

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


_HISTORY_CHANNELS = (
    "density_safety",
    "drowning_safety",
    "sun_safety",
    "lost_child_safety",
    "fall_event_safety",
    "stationary_person_safety",
    "flow_anomaly_safety",
    "slip_risk_safety",
    "overall",
)


def _record_history(report: Any) -> None:
    """Append every zone's channel scores to the history store."""
    ts = time.time()
    for s in report.scores:
        history.record_scores(
            zone_id=s.zone_id,
            channels={ch: getattr(s, ch) for ch in _HISTORY_CHANNELS},
            ts_unix=ts,
        )


_record_history(_report)


def _seed() -> None:
    global _zones, _report
    _zones = demo_coast()
    _report = _engine.review(coast_id=_COAST_ID, zones=_zones)
    _record_history(_report)


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


@app.get("/zones/{zone_id}/history")
def zone_history(
    zone_id: str,
    channel: str = "overall",
    hours: float = 24.0,
    limit: int = 1000,
) -> dict[str, Any]:
    """Return ``[(ts, value), ...]`` for one zone+channel."""
    if channel not in _HISTORY_CHANNELS:
        raise HTTPException(
            400,
            f"channel must be one of {_HISTORY_CHANNELS}, got {channel!r}",
        )
    if hours <= 0 or hours > 24 * 30:
        raise HTTPException(400, "hours must be in (0, 720]")
    since = time.time() - hours * 3600.0
    rows = history.fetch_history(
        zone_id=zone_id, channel=channel, since_unix=since, limit=limit,
    )
    return {
        "zone_id": zone_id,
        "channel": channel,
        "hours": hours,
        "points": [{"ts": ts, "value": v} for ts, v in rows],
    }


@app.get("/cameras/health")
def cameras_health() -> dict[str, Any]:
    """Return health snapshots for all known cameras."""
    return {"cameras": [asdict(h) for h in camera_health.snapshot()]}


@app.get("/coast/aggregates")
def coast_aggregates(hours: int = 4, bucket_minutes: int = 5) -> dict[str, Any]:
    """Bucketized ok/watch/urgent counts across all zones over time."""
    if hours <= 0 or hours > 24 * 30:
        raise HTTPException(400, "hours must be in (0, 720]")
    if bucket_minutes <= 0 or bucket_minutes > 1440:
        raise HTTPException(400, "bucket_minutes must be in (0, 1440]")
    zone_ids = [s.zone_id for s in _report.scores]
    rows = aggregates.coast_level_counts_over_time(
        zone_ids=zone_ids, hours=hours, bucket_minutes=bucket_minutes,
    )
    return {
        "hours": hours,
        "bucket_minutes": bucket_minutes,
        "buckets": rows,
    }


@app.get("/zones/{zone_id}/hourly")
def zone_hourly(
    zone_id: str, channel: str = "overall", hours: int = 24,
) -> dict[str, Any]:
    """Hourly mean of one zone+channel."""
    try:
        rows = aggregates.hourly_zone_density(
            zone_id=zone_id, channel=channel, hours=hours,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"zone_id": zone_id, "channel": channel, "hours": hours,
            "buckets": rows}


class BroadcastRequest(BaseModel):
    """Operator-initiated broadcast — placeholder for real PA/push.

    The endpoint records the action in an audit log; downstream
    integration (PA system, SMS, mobile push) is left to deployment.
    """

    kind: str = Field(..., min_length=1, max_length=64)
    message: str = Field(..., min_length=1, max_length=500)
    zone_id: str | None = None
    operator_id: str | None = Field(None, max_length=64)


@app.post("/broadcast")
def broadcast_send(req: BroadcastRequest) -> dict[str, Any]:
    """Record a broadcast in the audit log; return the entry."""
    try:
        entry = broadcast.record(
            kind=req.kind,
            message=req.message,
            zone_id=req.zone_id,
            operator_id=req.operator_id,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"recorded": True, "entry": {
        "ts_unix": entry.ts_unix,
        "kind": entry.kind,
        "message": entry.message,
        "zone_id": entry.zone_id,
        "operator_id": entry.operator_id,
    }}


def _group_to_dict(g: groups.TourGroup) -> dict[str, Any]:
    return {
        "group_id": g.group_id,
        "name": g.name,
        "expected_count": g.expected_count,
        "meeting_zone_id": g.meeting_zone_id,
        "operator_id": g.operator_id,
        "started_ts_unix": g.started_ts_unix,
        "last_checkin_ts_unix": g.last_checkin_ts_unix,
        "last_known_count": g.last_known_count,
        "last_known_zone_id": g.last_known_zone_id,
        "state": g.state,
        "history": [
            {"ts_unix": c.ts_unix, "count": c.count,
             "zone_id": c.zone_id, "note": c.note}
            for c in g.history
        ],
    }


class GroupRegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    expected_count: int = Field(..., gt=0, le=200)
    meeting_zone_id: str | None = None
    operator_id: str | None = Field(None, max_length=64)
    initial_count: int | None = None


@app.post("/groups")
def groups_register(req: GroupRegisterRequest) -> dict[str, Any]:
    try:
        g = groups.register(
            name=req.name,
            expected_count=req.expected_count,
            meeting_zone_id=req.meeting_zone_id,
            operator_id=req.operator_id,
            initial_count=req.initial_count,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return _group_to_dict(g)


@app.get("/groups")
def groups_list() -> dict[str, Any]:
    return {"groups": [_group_to_dict(g) for g in groups.list_all()]}


@app.get("/groups/{group_id}")
def groups_get(group_id: str) -> dict[str, Any]:
    try:
        g = groups.get(group_id)
    except KeyError:
        raise HTTPException(404, f"unknown group {group_id!r}")
    return _group_to_dict(g)


class GroupCheckinRequest(BaseModel):
    count: int = Field(..., ge=0, le=200)
    zone_id: str | None = None
    note: str | None = Field(None, max_length=300)


@app.post("/groups/{group_id}/checkin")
def groups_checkin(group_id: str, req: GroupCheckinRequest) -> dict[str, Any]:
    try:
        g = groups.checkin(
            group_id=group_id,
            count=req.count,
            zone_id=req.zone_id,
            note=req.note,
        )
    except KeyError:
        raise HTTPException(404, f"unknown group {group_id!r}")
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return _group_to_dict(g)


@app.post("/groups/{group_id}/complete")
def groups_complete(group_id: str) -> dict[str, Any]:
    try:
        g = groups.complete(group_id)
    except KeyError:
        raise HTTPException(404, f"unknown group {group_id!r}")
    return _group_to_dict(g)


@app.delete("/groups/{group_id}")
def groups_remove(group_id: str) -> dict[str, Any]:
    try:
        groups.remove(group_id)
    except KeyError:
        raise HTTPException(404, f"unknown group {group_id!r}")
    return {"removed": True, "group_id": group_id}


@app.get("/broadcast/log")
def broadcast_log(limit: int = 50) -> dict[str, Any]:
    """Most-recent broadcasts (newest first)."""
    if limit <= 0 or limit > 500:
        raise HTTPException(400, "limit must be in (0, 500]")
    entries = broadcast.recent(limit=limit)
    return {
        "kinds": list(broadcast.VALID_KINDS),
        "entries": [
            {
                "ts_unix": e.ts_unix,
                "kind": e.kind,
                "message": e.message,
                "zone_id": e.zone_id,
                "operator_id": e.operator_id,
            } for e in entries
        ],
    }


class CameraReportRequest(BaseModel):
    """Lightweight ping from any client that pulled a frame from a
    named source. The client posts after each successful read so the
    backend can track FPS / drops without owning the stream itself.
    """

    source: str = Field(..., min_length=1, max_length=200)
    ok: bool = True
    error: str | None = None


@app.post("/cameras/report")
def cameras_report(req: CameraReportRequest) -> dict[str, Any]:
    if req.ok:
        camera_health.record_frame(req.source)
    else:
        camera_health.record_drop(req.source, error=req.error or "")
    return {"acknowledged": True}


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
    fall_event_flag: bool = False
    stationary_person_signal: float = Field(0.0, ge=0.0, le=1.0)
    flow_anomaly_signal: float = Field(0.0, ge=0.0, le=1.0)
    slip_risk_signal: float = Field(0.0, ge=0.0, le=1.0)


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
        fall_event_flag=req.fall_event_flag,
        stationary_person_signal=req.stationary_person_signal,
        flow_anomaly_signal=req.flow_anomaly_signal,
        slip_risk_signal=req.slip_risk_signal,
    )
    _zones = [cam_zone]
    _report = _engine.review(coast_id="WEBCAM_COAST", zones=_zones)
    _record_history(_report)
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
