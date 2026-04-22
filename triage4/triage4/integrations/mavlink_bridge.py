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


def build_pymavlink_bridge(  # pragma: no cover
    connection_url: str = "udp:127.0.0.1:14550",
    platform_id: str = "uav",
    source_system: int = 255,
    source_component: int = 0,
    timeout_s: float = 5.0,
):
    """Skeleton real MAVLink backend. Requires ``pymavlink`` (optional extra).

    Not wired to a real autopilot — raises ``NotImplementedError`` so
    the skeleton cannot silently ship. The pseudocode below is aligned
    with the pymavlink 2.x API and can be turned into a working bridge
    by replacing the numbered blocks.

    Implementation outline::

        from pymavlink import mavutil

        # 1. Connect to the autopilot.
        conn = mavutil.mavlink_connection(
            connection_url,
            source_system=source_system,
            source_component=source_component,
        )
        conn.wait_heartbeat(timeout=timeout_s)

        # 2. Telemetry subscription loop (run in a background thread).
        def _rx_loop() -> None:
            while not closed:
                msg = conn.recv_match(
                    type=["GLOBAL_POSITION_INT", "SYS_STATUS"],
                    blocking=True, timeout=1.0,
                )
                if msg is None:
                    continue
                if msg.get_type() == "GLOBAL_POSITION_INT":
                    telemetry.pose = GeoPose(
                        x=msg.lon * 1e-7, y=msg.lat * 1e-7, z=msg.alt * 1e-3,
                        frame="WGS84",
                    )
                elif msg.get_type() == "SYS_STATUS":
                    telemetry.battery_pct = float(msg.battery_remaining)

        # 3. send_waypoint translates GeoPose → mission_item_int_send.
        def send_waypoint(pose: GeoPose) -> None:
            conn.mav.mission_item_int_send(
                conn.target_system, conn.target_component,
                seq=0,
                frame=mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
                command=mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                current=2, autocontinue=1,
                param1=0, param2=0, param3=0, param4=0,
                x=int(pose.y * 1e7), y=int(pose.x * 1e7), z=pose.z,
            )

    Coordinate-frame note: triage4 uses ``GeoPose(x=lon, y=lat)``;
    MAVLink's ``mission_item_int`` uses ``(x=lat*1e7, y=lon*1e7)``.
    Swap the fields carefully — see docs/HARDWARE_INTEGRATION.md.
    """
    try:
        import pymavlink  # noqa: F401
    except ImportError as exc:
        raise BridgeUnavailable(
            "pymavlink is not installed. Install with 'pip install pymavlink' "
            "or pick LoopbackMAVLinkBridge for a simulator."
        ) from exc
    raise NotImplementedError(
        "Real pymavlink backend is a skeleton — implement the three "
        "numbered blocks above. See docs/HARDWARE_INTEGRATION.md."
    )
