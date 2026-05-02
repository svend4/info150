"""Per-camera health tracking — last-frame timestamp, FPS, drops.

Process-local in-memory store (no persistence — health is a "now"
view). The dashboard polls ``snapshot()`` and renders a small status
bar.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock


@dataclass
class CameraHealth:
    """Live health summary for one camera source."""

    source: str
    state: str = "unknown"   # "ok" | "stale" | "down" | "unknown"
    last_frame_ts_unix: float | None = None
    frames_seen: int = 0
    frames_dropped: int = 0
    fps: float = 0.0
    last_error: str | None = None


_STORE: dict[str, CameraHealth] = {}
_LOCK = Lock()
_FPS_WINDOW = 5.0   # seconds


def record_frame(source: str) -> None:
    """Mark that ``source`` produced a frame at this instant."""
    now = time.time()
    with _LOCK:
        h = _STORE.setdefault(source, CameraHealth(source=source))
        if h.last_frame_ts_unix is not None:
            dt = now - h.last_frame_ts_unix
            if dt > 0:
                instant_fps = 1.0 / dt
                # Exponential smoothing.
                h.fps = 0.7 * h.fps + 0.3 * instant_fps
        h.last_frame_ts_unix = now
        h.frames_seen += 1
        h.state = "ok"
        h.last_error = None


def record_drop(source: str, error: str = "") -> None:
    """Mark that ``source`` failed to produce a frame."""
    with _LOCK:
        h = _STORE.setdefault(source, CameraHealth(source=source))
        h.frames_dropped += 1
        if error:
            h.last_error = error[:200]


def mark_state(source: str, state: str, error: str | None = None) -> None:
    """Force-set the state of a camera (e.g. after an open() failure)."""
    if state not in ("ok", "stale", "down", "unknown"):
        raise ValueError(f"unknown state {state!r}")
    with _LOCK:
        h = _STORE.setdefault(source, CameraHealth(source=source))
        h.state = state
        if error is not None:
            h.last_error = error[:200] if error else None


def _refresh_state(h: CameraHealth) -> None:
    """If last frame too old, mark stale → eventually down."""
    if h.last_frame_ts_unix is None:
        return
    age = time.time() - h.last_frame_ts_unix
    if age > 30.0:
        h.state = "down"
    elif age > 5.0:
        h.state = "stale"


def snapshot() -> list[CameraHealth]:
    """Return a list of all known cameras' current health."""
    with _LOCK:
        out: list[CameraHealth] = []
        for h in _STORE.values():
            _refresh_state(h)
            out.append(CameraHealth(
                source=h.source,
                state=h.state,
                last_frame_ts_unix=h.last_frame_ts_unix,
                frames_seen=h.frames_seen,
                frames_dropped=h.frames_dropped,
                fps=round(h.fps, 2),
                last_error=h.last_error,
            ))
        return out


def reset() -> None:
    """Clear the in-memory store. Test-only."""
    with _LOCK:
        _STORE.clear()


__all__ = [
    "CameraHealth",
    "mark_state",
    "record_drop",
    "record_frame",
    "reset",
    "snapshot",
]
