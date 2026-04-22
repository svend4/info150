"""Multi-platform coordination.

Addresses the open question from ``docs/HARDWARE_INTEGRATION.md §7``:
when several bridges operate together (two UAVs + one quadruped, or a
fleet of robots + a dashboard), the rest of triage4 needs a single
object to talk to. ``MultiPlatformManager`` is that object.

Design principles:
- It is itself a ``PlatformBridge`` (duck-typed), so it can be
  dropped anywhere a bridge is expected.
- Routing is explicit: broadcast to all by default, or target a
  specific ``platform_id``.
- Health-aware dispatch: ``send_waypoint`` refuses to hand a
  waypoint to an unhealthy platform.
- No hidden concurrency: the manager is sync + single-threaded, the
  same model every Loopback bridge uses.

Non-goals:
- Leader election across platforms.
- Cross-platform task balancing.
- Thread-safety (use one manager per thread).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from triage4.core.models import CasualtyNode, GeoPose
from triage4.graph.mission_graph import MissionGraph
from triage4.integrations.bridge_health import (
    BridgeHealth,
    check_bridge_health,
    safe_to_dispatch,
)
from triage4.integrations.platform_bridge import (
    PlatformBridge,
    PlatformTelemetry,
)


class PlatformNotFound(KeyError):
    """Raised when a targeted platform_id is not registered."""


class NoHealthyPlatform(RuntimeError):
    """Raised when ``send_waypoint`` cannot find any healthy platform."""


@dataclass
class DispatchResult:
    platform_id: str | None
    accepted: bool
    reasons: list[str] = field(default_factory=list)


class MultiPlatformManager:
    """Aggregates several ``PlatformBridge`` instances behind one surface."""

    _manager_platform_id = "triage4:multi"

    def __init__(
        self,
        bridges: list[PlatformBridge] | None = None,
        *,
        max_staleness_s: float = 5.0,
    ) -> None:
        self._bridges: dict[str, PlatformBridge] = {}
        self._max_staleness_s = float(max_staleness_s)
        for b in bridges or []:
            self.register(b)

    # -- registration ----------------------------------------------------

    def register(self, bridge: PlatformBridge) -> None:
        if bridge.platform_id in self._bridges:
            raise ValueError(f"platform_id {bridge.platform_id!r} already registered")
        self._bridges[bridge.platform_id] = bridge

    def unregister(self, platform_id: str) -> None:
        if platform_id not in self._bridges:
            raise PlatformNotFound(platform_id)
        del self._bridges[platform_id]

    def __contains__(self, platform_id: str) -> bool:
        return platform_id in self._bridges

    def __len__(self) -> int:
        return len(self._bridges)

    @property
    def platform_ids(self) -> list[str]:
        return sorted(self._bridges)

    def get(self, platform_id: str) -> PlatformBridge:
        if platform_id not in self._bridges:
            raise PlatformNotFound(platform_id)
        return self._bridges[platform_id]

    # -- PlatformBridge-shaped surface ----------------------------------

    @property
    def platform_id(self) -> str:
        return self._manager_platform_id

    @property
    def telemetry(self) -> PlatformTelemetry:
        """Aggregate telemetry: connected iff all member bridges are connected."""
        if not self._bridges:
            return PlatformTelemetry(
                platform_id=self._manager_platform_id,
                connected=False,
                last_update_ts=time.time(),
            )
        pose = next(iter(self._bridges.values())).telemetry.pose
        all_connected = all(b.telemetry.connected for b in self._bridges.values())
        min_battery = min(
            float(b.telemetry.battery_pct) for b in self._bridges.values()
        )
        newest_ts = max(
            float(b.telemetry.last_update_ts) for b in self._bridges.values()
        )
        return PlatformTelemetry(
            platform_id=self._manager_platform_id,
            pose=pose,
            battery_pct=min_battery,
            connected=all_connected,
            last_update_ts=newest_ts,
            extra={"member_count": len(self._bridges)},
        )

    def publish_casualty(
        self, node: CasualtyNode, *, platform_id: str | None = None
    ) -> None:
        """Broadcast if ``platform_id`` is None, otherwise target one bridge."""
        for b in self._resolve_targets(platform_id):
            b.publish_casualty(node)

    def publish_mission_graph(
        self, graph: MissionGraph, *, platform_id: str | None = None
    ) -> None:
        for b in self._resolve_targets(platform_id):
            b.publish_mission_graph(graph)

    def publish_handoff(
        self, payload: dict, *, platform_id: str | None = None
    ) -> None:
        for b in self._resolve_targets(platform_id):
            b.publish_handoff(payload)

    def send_waypoint(
        self,
        pose: GeoPose,
        *,
        platform_id: str | None = None,
    ) -> DispatchResult:
        """Send a waypoint to one platform.

        If ``platform_id`` is given, dispatch only to that platform and
        respect its health. If None, pick the healthiest platform by
        descending battery percentage among healthy candidates.
        """
        if platform_id is not None:
            return self._dispatch(platform_id, pose)

        healthy = self.healthy_platforms()
        if not healthy:
            raise NoHealthyPlatform("no healthy platform available")
        chosen_id = max(
            healthy, key=lambda pid: self._bridges[pid].telemetry.battery_pct
        )
        return self._dispatch(chosen_id, pose)

    def close(self) -> None:
        for b in self._bridges.values():
            b.close()

    # -- health ---------------------------------------------------------

    def health(
        self, *, now_ts: float | None = None
    ) -> dict[str, BridgeHealth]:
        return {
            pid: check_bridge_health(
                b, now_ts=now_ts, max_staleness_s=self._max_staleness_s,
            )
            for pid, b in self._bridges.items()
        }

    def healthy_platforms(self, *, now_ts: float | None = None) -> list[str]:
        return sorted(
            pid for pid, h in self.health(now_ts=now_ts).items()
            if safe_to_dispatch(h)
        )

    # -- internals ------------------------------------------------------

    def _resolve_targets(
        self, platform_id: str | None
    ) -> list[PlatformBridge]:
        if platform_id is None:
            return list(self._bridges.values())
        if platform_id not in self._bridges:
            raise PlatformNotFound(platform_id)
        return [self._bridges[platform_id]]

    def _dispatch(self, platform_id: str, pose: GeoPose) -> DispatchResult:
        if platform_id not in self._bridges:
            raise PlatformNotFound(platform_id)
        bridge = self._bridges[platform_id]
        health = check_bridge_health(
            bridge, max_staleness_s=self._max_staleness_s
        )
        if not safe_to_dispatch(health):
            return DispatchResult(
                platform_id=platform_id,
                accepted=False,
                reasons=list(health.reasons),
            )
        bridge.send_waypoint(pose)
        return DispatchResult(platform_id=platform_id, accepted=True, reasons=[])
