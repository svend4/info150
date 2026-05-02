"""Operator broadcast registry — stores audit log of operator actions.

The actual public-address / SMS / push integration is a placeholder
(callers register a webhook). Here we just record that an operator
issued a broadcast — timestamp, zone (optional), kind, message, and
operator-id (optional).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock


# Closed set of broadcast kinds the dashboard surfaces as buttons.
VALID_KINDS = (
    "shade_advisory",
    "lost_child",
    "clear_water",
    "lightning",
    "general_announcement",
)


@dataclass(frozen=True)
class BroadcastEntry:
    ts_unix: float
    kind: str
    message: str
    zone_id: str | None
    operator_id: str | None


_LOG: list[BroadcastEntry] = []
_LOCK = Lock()
_MAX_ENTRIES = 500


def record(
    *,
    kind: str,
    message: str,
    zone_id: str | None = None,
    operator_id: str | None = None,
    ts_unix: float | None = None,
) -> BroadcastEntry:
    """Append one broadcast to the audit log."""
    if kind not in VALID_KINDS:
        raise ValueError(f"kind must be one of {VALID_KINDS}, got {kind!r}")
    if not message.strip():
        raise ValueError("message must not be empty")
    if len(message) > 500:
        raise ValueError("message exceeds 500-char limit")
    if zone_id is not None and not zone_id:
        raise ValueError("zone_id must not be empty string")
    entry = BroadcastEntry(
        ts_unix=ts_unix if ts_unix is not None else time.time(),
        kind=kind,
        message=message,
        zone_id=zone_id,
        operator_id=operator_id,
    )
    with _LOCK:
        _LOG.append(entry)
        if len(_LOG) > _MAX_ENTRIES:
            del _LOG[0:len(_LOG) - _MAX_ENTRIES]
    return entry


def recent(*, limit: int = 50) -> list[BroadcastEntry]:
    """Return the most-recent ``limit`` broadcasts, newest first."""
    if limit <= 0:
        raise ValueError("limit must be positive")
    with _LOCK:
        return list(reversed(_LOG[-limit:]))


def reset() -> None:
    """Clear the log. Test-only."""
    with _LOCK:
        _LOG.clear()


__all__ = [
    "BroadcastEntry",
    "VALID_KINDS",
    "recent",
    "record",
    "reset",
]
