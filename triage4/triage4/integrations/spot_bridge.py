"""Spot / quadruped bridge.

Part of Phase 8. The default ``LoopbackSpotBridge`` simulates a
Spot-class quadruped: it walks toward the most recent waypoint at a
configurable speed, tracks a ``gait`` state, and drains battery faster
on rough terrain. A real ``bosdyn``-based backend is provided as a
skeleton behind a lazy import.
"""

from __future__ import annotations

import math
import time
from dataclasses import asdict

from triage4.core.models import CasualtyNode, GeoPose
from triage4.graph.mission_graph import MissionGraph
from triage4.integrations.platform_bridge import (
    BridgeUnavailable,
    PlatformTelemetry,
)


class LoopbackSpotBridge:
    """Deterministic quadruped simulator."""

    VALID_GAITS = ("sit", "stand", "walk", "trot")

    def __init__(
        self,
        platform_id: str = "sim_spot",
        start_pose: GeoPose | None = None,
        speed: float = 1.2,
        rough_terrain: bool = False,
    ) -> None:
        self._platform_id = str(platform_id)
        self._speed = max(0.01, float(speed))
        self._rough = bool(rough_terrain)
        self._gait = "stand"
        self._waypoint: GeoPose | None = None
        self._telemetry = PlatformTelemetry(
            platform_id=self._platform_id,
            pose=start_pose or GeoPose(0.0, 0.0),
            battery_pct=100.0,
            connected=True,
            last_update_ts=time.time(),
            extra={"gait": self._gait, "rough_terrain": self._rough},
        )
        self._events: list[tuple[str, dict]] = []

    @property
    def platform_id(self) -> str:
        return self._platform_id

    @property
    def telemetry(self) -> PlatformTelemetry:
        return self._telemetry

    @property
    def events(self) -> list[tuple[str, dict]]:
        return list(self._events)

    @property
    def gait(self) -> str:
        return self._gait

    def set_gait(self, gait: str) -> None:
        if gait not in self.VALID_GAITS:
            raise ValueError(
                f"gait must be one of {self.VALID_GAITS}, got {gait!r}"
            )
        self._gait = gait
        self._telemetry.extra["gait"] = gait

    def step(self, dt_s: float) -> None:
        if self._waypoint is None or dt_s <= 0 or self._gait not in {"walk", "trot"}:
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
        drain_rate = 0.03 if self._rough else 0.015
        self._telemetry.battery_pct = max(
            0.0, self._telemetry.battery_pct - travel * drain_rate
        )
        self._telemetry.last_update_ts = time.time()

    def publish_casualty(self, node: CasualtyNode) -> None:
        self._events.append(("casualty", node.to_dict()))

    def publish_mission_graph(self, graph: MissionGraph) -> None:
        self._events.append(("mission_graph", graph.as_json()))

    def publish_handoff(self, payload: dict) -> None:
        self._events.append(("handoff", dict(payload)))

    def send_waypoint(self, pose: GeoPose) -> None:
        self._waypoint = pose
        # Arriving at a new waypoint implicitly transitions us into walk.
        if self._gait in {"sit", "stand"}:
            self.set_gait("walk")
        self._events.append(("waypoint", asdict(pose)))

    def close(self) -> None:
        self._telemetry.connected = False


def build_bosdyn_bridge(  # pragma: no cover
    hostname: str = "192.168.80.3",
    username: str = "user",
    password: str = "",
    platform_id: str = "spot",
    lease_timeout_s: float = 30.0,
):
    """Skeleton real Spot backend using Boston Dynamics ``bosdyn`` SDK.

    Not wired to a real Spot — raises ``NotImplementedError`` on
    purpose. The outline below matches ``bosdyn-client`` ≥ 3.x and
    each numbered block is a concrete set of SDK calls a future
    engineer can fill in.

    Implementation outline::

        import bosdyn.client
        from bosdyn.client.robot_command import (
            RobotCommandClient, RobotCommandBuilder, blocking_stand,
        )
        from bosdyn.client.robot_state import RobotStateClient
        from bosdyn.client.lease import LeaseClient, LeaseKeepAlive

        # 1. Authenticate + lease.
        sdk = bosdyn.client.create_standard_sdk("triage4")
        robot = sdk.create_robot(hostname)
        robot.authenticate(username, password)
        robot.time_sync.wait_for_sync()
        lease_client = robot.ensure_client(LeaseClient.default_service_name)
        lease_client.take()
        keep_alive = LeaseKeepAlive(lease_client)

        # 2. Gait / motion commands.
        cmd = robot.ensure_client(RobotCommandClient.default_service_name)
        blocking_stand(cmd)
        def walk_to(pose: GeoPose) -> None:
            walk = RobotCommandBuilder.synchro_se2_trajectory_point_command(
                goal_x=pose.x, goal_y=pose.y, goal_heading=pose.yaw,
                frame_name="odom",
            )
            cmd.robot_command_async(walk)

        # 3. Telemetry loop.
        state = robot.ensure_client(RobotStateClient.default_service_name)
        def _tick() -> None:
            rs = state.get_robot_state()
            telemetry.battery_pct = rs.battery_states[0].charge_percentage.value
            # Convert BodyState.vision_tform_body into GeoPose(x, y, yaw)
            # via bosdyn.client.frame_helpers.

    Safety note: always call ``keep_alive.shutdown()`` and release the
    lease in ``close()`` — a stuck lease leaves the robot uncommandable
    by anybody else. See docs/HARDWARE_INTEGRATION.md for the full
    checklist.
    """
    try:
        import bosdyn  # noqa: F401
    except ImportError as exc:
        raise BridgeUnavailable(
            "bosdyn-client is not installed. Install with "
            "'pip install bosdyn-client' or use LoopbackSpotBridge in tests."
        ) from exc
    raise NotImplementedError(
        "Real bosdyn backend is a skeleton — wire up the three numbered "
        "blocks above. See docs/HARDWARE_INTEGRATION.md."
    )
