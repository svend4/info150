"""FastAPI dashboard for triage4-stroll — day-walk advisory.

The stroll engine is per-segment (returns a single
``StrollAdvisory``); the dashboard exposes one segment at a time.
POST /demo/reload regenerates with the default synthetic
segment. POST /camera/run accepts browser-derived signals and
rebuilds the advisory.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from ..core.enums import Terrain
from ..sim.synthetic_stroll import demo_segment, generate_segment
from ..walk_assistant.stroll_assistant import StrollAssistant

app = FastAPI(title="triage4-stroll API", version="0.1.0")

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

_engine = StrollAssistant()


def _build() -> Any:
    return _engine.review(demo_segment())


_advisory = _build()


def _seed() -> None:
    global _advisory
    _advisory = _build()


def _severity_counts() -> dict[str, int]:
    counts: dict[str, int] = {"ok": 0, "minor": 0, "severe": 0}
    for c in _advisory.cues:
        counts[c.severity] = counts.get(c.severity, 0) + 1
    return counts


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "service": "triage4-stroll", "version": "0.1.0",
        "walker_id": _advisory.segment.walker_id,
        "terrain": _advisory.segment.terrain,
        "cue_count": len(_advisory.cues),
    }


@app.get("/report")
def report() -> dict[str, Any]:
    seg = _advisory.segment
    return {
        "walker_id": seg.walker_id,
        "terrain": seg.terrain,
        "duration_min": seg.duration_min,
        "pace_kmh": seg.pace_kmh,
        "fatigue_index": _advisory.fatigue_index,
        "hydration_due": _advisory.hydration_due,
        "shade_advisory": _advisory.shade_advisory,
        "pace_advisory": _advisory.pace_advisory,
        "rest_due": _advisory.rest_due,
        "overall_safety": _advisory.overall_safety,
        "severity_counts": _severity_counts(),
        "cues": [asdict(c) for c in _advisory.cues],
    }


@app.get("/cues")
def cues() -> list[dict[str, Any]]:
    return [asdict(c) for c in _advisory.cues]


@app.post("/demo/reload")
def demo_reload() -> dict[str, Any]:
    _seed()
    return {
        "reloaded": True,
        "walker_id": _advisory.segment.walker_id,
        "cue_count": len(_advisory.cues),
    }


class CameraRunRequest(BaseModel):
    """Camera-driven walk-segment review.

    The browser collects ~30 frames, computes mean inter-frame
    motion (activity proxy) and mean luminance (sun proxy), and
    posts these scalars together with operator-supplied pace,
    duration, terrain, HR, and ambient temperature.
    """

    walker_id: str = Field("WEBCAM_W", min_length=1, max_length=64)
    terrain: Terrain = "flat"
    pace_kmh: float = Field(4.5, ge=0.0, le=20.0)
    duration_min: float = Field(15.0, ge=0.0, le=24 * 60)
    activity_intensity: float = Field(0.4, ge=0.0, le=1.0)
    sun_exposure_proxy: float = Field(0.4, ge=0.0, le=1.0)
    minutes_since_rest: float = Field(15.0, ge=0.0, le=24 * 60)
    air_temp_c: float | None = Field(None, ge=-40.0, le=60.0)
    hr_bpm: float | None = Field(None, ge=30.0, le=220.0)


@app.post("/camera/run")
def camera_run(req: CameraRunRequest) -> dict[str, Any]:
    """Replace the dashboard with a single camera-derived advisory."""
    global _advisory
    seg = generate_segment(
        walker_id=req.walker_id,
        terrain=req.terrain,
        pace_kmh=req.pace_kmh,
        duration_min=req.duration_min,
        activity_intensity=req.activity_intensity,
        sun_exposure_proxy=req.sun_exposure_proxy,
        minutes_since_rest=req.minutes_since_rest,
        air_temp_c=req.air_temp_c,
        hr_bpm=req.hr_bpm,
    )
    _advisory = _engine.review(seg)
    return {
        "walker_id": seg.walker_id,
        "terrain": seg.terrain,
        "fatigue_index": _advisory.fatigue_index,
        "pace_advisory": _advisory.pace_advisory,
        "overall_safety": _advisory.overall_safety,
        "cue_count": len(_advisory.cues),
    }


@app.get("/export.html", response_class=HTMLResponse)
def export_html() -> str:
    seg = _advisory.segment
    cues_html = "\n".join(
        f"<li><b>{c.severity}</b> [{c.kind}] {c.text}</li>"
        for c in _advisory.cues
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8">
<title>triage4-stroll — walker {seg.walker_id}</title>
<style>
body{{font:14px/1.5 system-ui;max-width:900px;margin:2rem auto;padding:0 1rem;
color:#1a2630;background:#f4f7f2;}}
h1,h2{{margin-top:1.5em;}}table{{border-collapse:collapse;width:100%;}}
th,td{{padding:6px 10px;text-align:left;border-bottom:1px solid #d6dce6;}}
th{{background:#e6ecd9;}}ul{{padding-left:1.2rem;}}
</style></head><body>
<h1>triage4-stroll</h1>
<p>Walker <b>{seg.walker_id}</b> · {seg.terrain} · {seg.duration_min:.0f} min · pace {seg.pace_kmh:.1f} km/h</p>
<table>
<tr><th>Channel</th><th>Value</th></tr>
<tr><td>fatigue_index</td><td>{_advisory.fatigue_index:.2f}</td></tr>
<tr><td>hydration_due</td><td>{_advisory.hydration_due}</td></tr>
<tr><td>shade_advisory</td><td>{_advisory.shade_advisory}</td></tr>
<tr><td>pace_advisory</td><td>{_advisory.pace_advisory}</td></tr>
<tr><td>rest_due</td><td>{_advisory.rest_due}</td></tr>
<tr><td>overall_safety</td><td>{_advisory.overall_safety:.2f}</td></tr>
</table>
<h2>Coaching cues ({len(_advisory.cues)})</h2>
<ul>{cues_html or "<li><i>none</i></li>"}</ul>
</body></html>"""
