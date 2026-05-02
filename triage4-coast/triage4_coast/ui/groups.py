"""Tour-group registry — for group-cohesion / lost-member tracking.

A tour group is a labelled list with expected headcount + ongoing
check-ins. The operator (or a guide) updates the count periodically;
the registry computes a derived "alert" state when the count drops
or a checkin is overdue.

In-memory only (no persistence). A real deployment would back this
with sqlite or postgres so groups survive backend restarts.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from threading import Lock
from typing import Literal


GroupState = Literal["active", "complete", "alert"]
VALID_STATES: tuple[GroupState, ...] = ("active", "complete", "alert")


# --- Tunable thresholds ----------------------------------------------------
# Alert if the last checkin is older than this:
DEFAULT_OVERDUE_S = 300.0       # 5 min
# Alert if last_known_count drops below expected by more than this:
DEFAULT_MISSING_TOLERANCE = 1


@dataclass(frozen=True)
class Checkin:
    ts_unix: float
    count: int
    zone_id: str | None
    note: str | None


@dataclass
class TourGroup:
    group_id: str
    name: str
    expected_count: int
    meeting_zone_id: str | None
    operator_id: str | None
    started_ts_unix: float
    last_checkin_ts_unix: float
    last_known_count: int
    last_known_zone_id: str | None
    state: GroupState = "active"
    history: list[Checkin] = field(default_factory=list)

    def derive_state(
        self,
        *,
        now: float,
        overdue_s: float = DEFAULT_OVERDUE_S,
        missing_tolerance: int = DEFAULT_MISSING_TOLERANCE,
    ) -> GroupState:
        if self.state == "complete":
            return "complete"
        age = now - self.last_checkin_ts_unix
        if age > overdue_s:
            return "alert"
        if self.last_known_count < self.expected_count - missing_tolerance:
            return "alert"
        return "active"


_GROUPS: dict[str, TourGroup] = {}
_LOCK = Lock()


def register(
    *,
    name: str,
    expected_count: int,
    meeting_zone_id: str | None = None,
    operator_id: str | None = None,
    initial_count: int | None = None,
) -> TourGroup:
    """Create a new active group. Returns the new group."""
    if not name.strip():
        raise ValueError("name must not be empty")
    if len(name) > 64:
        raise ValueError("name must be <= 64 chars")
    if expected_count <= 0 or expected_count > 200:
        raise ValueError("expected_count must be in (0, 200]")
    if initial_count is not None and not 0 <= initial_count <= expected_count:
        raise ValueError("initial_count must be in [0, expected_count]")
    now = time.time()
    gid = uuid.uuid4().hex[:12]
    g = TourGroup(
        group_id=gid,
        name=name.strip(),
        expected_count=int(expected_count),
        meeting_zone_id=meeting_zone_id,
        operator_id=operator_id,
        started_ts_unix=now,
        last_checkin_ts_unix=now,
        last_known_count=int(initial_count) if initial_count is not None else int(expected_count),
        last_known_zone_id=meeting_zone_id,
        state="active",
        history=[Checkin(
            ts_unix=now,
            count=int(initial_count) if initial_count is not None else int(expected_count),
            zone_id=meeting_zone_id,
            note="registered",
        )],
    )
    with _LOCK:
        _GROUPS[gid] = g
    return g


def checkin(
    *,
    group_id: str,
    count: int,
    zone_id: str | None = None,
    note: str | None = None,
) -> TourGroup:
    """Append a checkin to the named group."""
    if count < 0 or count > 200:
        raise ValueError("count must be in [0, 200]")
    with _LOCK:
        if group_id not in _GROUPS:
            raise KeyError(group_id)
        g = _GROUPS[group_id]
        if g.state == "complete":
            raise ValueError("cannot check in: group is already complete")
        now = time.time()
        g.history.append(Checkin(
            ts_unix=now, count=int(count),
            zone_id=zone_id, note=note,
        ))
        g.last_checkin_ts_unix = now
        g.last_known_count = int(count)
        if zone_id is not None:
            g.last_known_zone_id = zone_id
        # Keep history bounded to last 200 entries.
        if len(g.history) > 200:
            del g.history[0:len(g.history) - 200]
        g.state = g.derive_state(now=now)
        return g


def complete(group_id: str) -> TourGroup:
    """Mark the group as finished — no more checkins allowed."""
    with _LOCK:
        if group_id not in _GROUPS:
            raise KeyError(group_id)
        g = _GROUPS[group_id]
        g.state = "complete"
        return g


def remove(group_id: str) -> None:
    with _LOCK:
        if group_id not in _GROUPS:
            raise KeyError(group_id)
        del _GROUPS[group_id]


def get(group_id: str) -> TourGroup:
    with _LOCK:
        if group_id not in _GROUPS:
            raise KeyError(group_id)
        g = _GROUPS[group_id]
        if g.state != "complete":
            g.state = g.derive_state(now=time.time())
        return g


def list_all() -> list[TourGroup]:
    with _LOCK:
        now = time.time()
        out: list[TourGroup] = []
        for g in _GROUPS.values():
            if g.state != "complete":
                g.state = g.derive_state(now=now)
            out.append(g)
        # Sort: active first, alert next, complete last; within each
        # bucket newest-checkin first.
        order = {"alert": 0, "active": 1, "complete": 2}
        out.sort(key=lambda g: (order[g.state], -g.last_checkin_ts_unix))
        return out


def reset() -> None:
    """Test-only."""
    with _LOCK:
        _GROUPS.clear()


__all__ = [
    "Checkin",
    "DEFAULT_MISSING_TOLERANCE",
    "DEFAULT_OVERDUE_S",
    "GroupState",
    "TourGroup",
    "VALID_STATES",
    "checkin",
    "complete",
    "get",
    "list_all",
    "register",
    "remove",
    "reset",
]
