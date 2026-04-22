"""Uniform health checks for any ``PlatformBridge``.

Part of the Phase 10 preparation work. Every bridge implementation —
loopback or real — must satisfy the same telemetry contract:

- connected flag is truthful,
- pose is a finite ``GeoPose``,
- battery_pct is in [0, 100],
- last_update_ts is not stale beyond ``max_staleness_s``,
- platform_id is non-empty and matches between the bridge and its
  telemetry snapshot.

``check_bridge_health(bridge)`` returns a ``BridgeHealth`` report with
a boolean ``ok`` flag and a list of reason strings. Safety-critical
call sites (e.g. ``autonomy/task_allocator``) can gate waypoint
dispatch on ``health.ok`` so a disconnected or confused platform
cannot be commanded to move.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

from triage4.core.models import GeoPose
from triage4.integrations.platform_bridge import PlatformBridge, PlatformTelemetry


@dataclass
class BridgeHealth:
    platform_id: str
    ok: bool
    connected: bool
    battery_pct: float
    pose: GeoPose
    age_s: float
    reasons: list[str] = field(default_factory=list)


_DEFAULT_MAX_STALENESS_S = 5.0
_DEFAULT_LOW_BATTERY_PCT = 20.0


def _is_finite_pose(pose: GeoPose) -> bool:
    return all(math.isfinite(v) for v in (pose.x, pose.y, pose.z, pose.yaw))


def check_telemetry(
    telemetry: PlatformTelemetry,
    *,
    now_ts: float | None = None,
    max_staleness_s: float = _DEFAULT_MAX_STALENESS_S,
    low_battery_pct: float = _DEFAULT_LOW_BATTERY_PCT,
) -> BridgeHealth:
    """Evaluate a ``PlatformTelemetry`` snapshot in isolation.

    Kept separate from ``check_bridge_health`` so bridges can be
    validated offline (e.g. from a stored log) without a live
    instance.
    """
    reasons: list[str] = []
    reference = now_ts if now_ts is not None else time.time()
    age = max(0.0, reference - float(telemetry.last_update_ts))

    if not telemetry.platform_id:
        reasons.append("empty platform_id")

    if not telemetry.connected:
        reasons.append("platform disconnected")

    if not _is_finite_pose(telemetry.pose):
        reasons.append("non-finite pose")

    bat = float(telemetry.battery_pct)
    if not (0.0 <= bat <= 100.0):
        reasons.append(f"battery_pct out of range ({bat:.1f})")
    elif bat < low_battery_pct:
        reasons.append(f"low battery ({bat:.1f}%)")

    if max_staleness_s > 0.0 and age > max_staleness_s:
        reasons.append(f"telemetry stale ({age:.1f}s > {max_staleness_s:.1f}s)")

    ok = not reasons or reasons == [f"low battery ({bat:.1f}%)"]
    # Low-battery on its own is a warning, not a hard failure — the bridge
    # is still usable for observation even if we'd rather not dispatch it
    # on new waypoints.

    return BridgeHealth(
        platform_id=telemetry.platform_id,
        ok=ok,
        connected=bool(telemetry.connected),
        battery_pct=bat,
        pose=telemetry.pose,
        age_s=round(age, 3),
        reasons=reasons,
    )


def check_bridge_health(
    bridge: PlatformBridge,
    *,
    now_ts: float | None = None,
    max_staleness_s: float = _DEFAULT_MAX_STALENESS_S,
    low_battery_pct: float = _DEFAULT_LOW_BATTERY_PCT,
) -> BridgeHealth:
    """Evaluate a live bridge via its telemetry snapshot."""
    telemetry = bridge.telemetry
    report = check_telemetry(
        telemetry,
        now_ts=now_ts,
        max_staleness_s=max_staleness_s,
        low_battery_pct=low_battery_pct,
    )

    if telemetry.platform_id != bridge.platform_id:
        report.reasons.append(
            f"platform_id mismatch: bridge={bridge.platform_id!r} "
            f"telemetry={telemetry.platform_id!r}"
        )
        report = BridgeHealth(
            platform_id=bridge.platform_id,
            ok=False,
            connected=report.connected,
            battery_pct=report.battery_pct,
            pose=report.pose,
            age_s=report.age_s,
            reasons=report.reasons,
        )

    return report


def safe_to_dispatch(health: BridgeHealth) -> bool:
    """Narrower gate: would we send a new waypoint to this platform now?

    Stricter than ``health.ok`` because it also refuses low-battery
    platforms — a waypoint costs energy the platform may not have.
    """
    if not health.ok:
        return False
    if health.battery_pct < _DEFAULT_LOW_BATTERY_PCT:
        return False
    if not health.connected:
        return False
    return True
