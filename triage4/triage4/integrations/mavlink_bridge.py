"""MAVLink bridge — UAV platform.

Part of Phase 8. The default ``LoopbackMAVLinkBridge`` simulates a UAV
that linearly moves toward the most recent waypoint and drains its
battery while flying. A real ``pymavlink``-backed bridge is provided as
a skeleton behind a lazy import.
"""

from __future__ import annotations

import math
import time
from dataclasses import asdict
from typing import Any

from triage4.core.models import CasualtyNode, GeoPose
from triage4.graph.mission_graph import MissionGraph
from triage4.integrations.platform_bridge import (
    BridgeUnavailable,
    PlatformTelemetry,
)


class LoopbackMAVLinkBridge:
    """Deterministic UAV simulator for tests and demos."""

    def __init__(
        self,
        platform_id: str = "sim_uav",
        start_pose: GeoPose | None = None,
        speed: float = 5.0,
        drain_per_metre: float = 0.01,
    ) -> None:
        self._platform_id = str(platform_id)
        self._speed = max(0.01, float(speed))
        self._drain = max(0.0, float(drain_per_metre))
        self._waypoint: GeoPose | None = None
        self._telemetry = PlatformTelemetry(
            platform_id=self._platform_id,
            pose=start_pose or GeoPose(0.0, 0.0),
            battery_pct=100.0,
            connected=True,
            last_update_ts=time.time(),
        )
        self._published: list[tuple[str, Any]] = []

    @property
    def platform_id(self) -> str:
        return self._platform_id

    @property
    def telemetry(self) -> PlatformTelemetry:
        return self._telemetry

    @property
    def published(self) -> list[tuple[str, Any]]:
        return list(self._published)

    @property
    def waypoint(self) -> GeoPose | None:
        return self._waypoint

    def step(self, dt_s: float) -> None:
        """Advance the simulated UAV by ``dt_s`` seconds."""
        if self._waypoint is None or dt_s <= 0:
            self._telemetry.last_update_ts = time.time()
            return

        px, py = self._telemetry.pose.x, self._telemetry.pose.y
        tx, ty = self._waypoint.x, self._waypoint.y
        dx, dy = tx - px, ty - py
        dist = math.hypot(dx, dy)
        if dist < 1e-9:
            self._telemetry.last_update_ts = time.time()
            return

        travel = min(dist, self._speed * dt_s)
        ratio = travel / dist
        self._telemetry.pose = GeoPose(
            x=px + dx * ratio,
            y=py + dy * ratio,
            z=self._telemetry.pose.z,
            yaw=math.atan2(dy, dx),
            frame=self._telemetry.pose.frame,
        )
        self._telemetry.battery_pct = max(
            0.0, self._telemetry.battery_pct - travel * self._drain
        )
        self._telemetry.last_update_ts = time.time()

    def publish_casualty(self, node: CasualtyNode) -> None:
        self._published.append(("casualty", node.to_dict()))

    def publish_mission_graph(self, graph: MissionGraph) -> None:
        self._published.append(("mission_graph", graph.as_json()))

    def publish_handoff(self, payload: dict) -> None:
        self._published.append(("handoff", dict(payload)))

    def send_waypoint(self, pose: GeoPose) -> None:
        self._waypoint = pose
        self._published.append(("waypoint", asdict(pose)))

    def close(self) -> None:
        self._telemetry.connected = False


def build_pymavlink_bridge(
    connection_url: str = "udp:127.0.0.1:14550",
    platform_id: str = "uav",
    *,
    source_system: int = 255,
    source_component: int = 0,
    heartbeat_timeout_s: float = 10.0,
    start_telemetry: bool = True,
):
    """Build a real ``PyMAVLinkBridge`` against an autopilot / SITL.

    Steps the factory performs:

    1. Lazy-import ``pymavlink.mavutil``. Raises ``BridgeUnavailable``
       if the SDK is absent — the loopback path is always available
       as a fallback.
    2. ``mavutil.mavlink_connection(connection_url, ...)`` — builds
       the socket / serial connection to the autopilot.
    3. ``conn.wait_heartbeat(timeout=heartbeat_timeout_s)`` —
       negotiates ``target_system`` / ``target_component``. Raises
       ``BridgeUnavailable`` if nothing responds.
    4. Hand the connection to ``PyMAVLinkBridge`` and, optionally,
       start the telemetry thread.

    For local dev against ArduPilot SITL::

        python -c "
        from triage4.integrations import build_pymavlink_bridge
        bridge = build_pymavlink_bridge('udp:127.0.0.1:14550')
        bridge.send_waypoint(GeoPose(x=-122.084, y=37.422, z=30.0))
        "

    See ``docs/PHASE_10_SITL.md`` for the full SITL setup.
    """
    try:
        from pymavlink import mavutil
    except ImportError as exc:
        raise BridgeUnavailable(
            "pymavlink is not installed. Install with 'pip install pymavlink' "
            "or pick LoopbackMAVLinkBridge for a simulator."
        ) from exc

    from triage4.integrations.pymavlink_bridge import PyMAVLinkBridge

    conn = mavutil.mavlink_connection(
        connection_url,
        source_system=source_system,
        source_component=source_component,
    )
    try:
        conn.wait_heartbeat(timeout=heartbeat_timeout_s)
    except Exception as exc:
        try:
            conn.close()
        except Exception:
            pass
        raise BridgeUnavailable(
            f"no MAVLink heartbeat on {connection_url!r} within "
            f"{heartbeat_timeout_s}s — is the autopilot / SITL running?"
        ) from exc

    bridge = PyMAVLinkBridge(
        connection=conn,
        platform_id=platform_id,
        mavlink_module=mavutil.mavlink,
    )
    if start_telemetry:
        bridge.start_telemetry_thread()
    return bridge
