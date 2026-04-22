"""ROS2 bridge — generic topic publishing.

Part of Phase 8. The default ``LoopbackROS2Bridge`` records messages in
a list keyed by topic, so pipelines can be tested without a live ROS2
domain. A real ``rclpy`` backend is a skeleton behind a lazy import.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import asdict

from triage4.core.models import CasualtyNode, GeoPose
from triage4.graph.mission_graph import MissionGraph
from triage4.integrations.platform_bridge import (
    BridgeUnavailable,
    PlatformTelemetry,
)


class LoopbackROS2Bridge:
    """In-process ROS2-style pub/sub recorder."""

    DEFAULT_TOPICS = {
        "casualty": "/triage4/casualty",
        "mission_graph": "/triage4/mission_graph",
        "handoff": "/triage4/handoff",
        "waypoint": "/triage4/waypoint",
    }

    def __init__(
        self,
        platform_id: str = "ros2_node",
        topics: dict[str, str] | None = None,
    ) -> None:
        self._platform_id = str(platform_id)
        self._topics = dict(self.DEFAULT_TOPICS)
        if topics:
            self._topics.update(topics)
        self._published: dict[str, list[dict]] = defaultdict(list)
        self._telemetry = PlatformTelemetry(
            platform_id=self._platform_id,
            connected=True,
            last_update_ts=time.time(),
        )

    @property
    def platform_id(self) -> str:
        return self._platform_id

    @property
    def telemetry(self) -> PlatformTelemetry:
        return self._telemetry

    @property
    def topics(self) -> dict[str, str]:
        return dict(self._topics)

    def published_on(self, kind: str) -> list[dict]:
        """All messages published under the topic for ``kind``."""
        if kind not in self._topics:
            raise KeyError(f"unknown kind '{kind}'")
        return list(self._published.get(self._topics[kind], []))

    def _emit(self, kind: str, payload: dict) -> None:
        topic = self._topics[kind]
        self._published[topic].append(
            {"topic": topic, "ts": time.time(), "data": dict(payload)}
        )
        self._telemetry.last_update_ts = time.time()

    def publish_casualty(self, node: CasualtyNode) -> None:
        self._emit("casualty", node.to_dict())

    def publish_mission_graph(self, graph: MissionGraph) -> None:
        self._emit("mission_graph", graph.as_json())

    def publish_handoff(self, payload: dict) -> None:
        self._emit("handoff", dict(payload))

    def send_waypoint(self, pose: GeoPose) -> None:
        self._emit("waypoint", asdict(pose))

    def inject_telemetry(
        self,
        pose: GeoPose | None = None,
        battery_pct: float | None = None,
        extra: dict | None = None,
    ) -> None:
        """Testing helper — emulates a subscription callback."""
        if pose is not None:
            self._telemetry.pose = pose
        if battery_pct is not None:
            self._telemetry.battery_pct = float(battery_pct)
        if extra is not None:
            self._telemetry.extra.update(extra)
        self._telemetry.last_update_ts = time.time()

    def close(self) -> None:
        self._telemetry.connected = False


def build_rclpy_bridge(  # pragma: no cover
    platform_id: str = "triage4_node",
    topics: dict[str, str] | None = None,
    odom_topic: str = "/odom",
    battery_topic: str = "/battery_state",
    domain_id: int | None = None,
    qos_depth: int = 10,
):
    """Skeleton real ROS2 backend using ``rclpy``.

    Not wired up to a live ROS2 domain — raises ``NotImplementedError``
    on purpose so this skeleton cannot silently ship. The call sites
    and SDK-specific wiring below are verified against the rclpy API
    and can be turned into a working node by replacing each pseudocode
    block with the concrete rclpy calls.

    Implementation outline (rclpy ≥ Humble)::

        import rclpy
        from rclpy.node import Node
        from std_msgs.msg import String
        from nav_msgs.msg import Odometry
        from sensor_msgs.msg import BatteryState

        rclpy.init(domain_id=domain_id)
        node = Node(platform_id)

        publishers = {
            kind: node.create_publisher(String, topic, qos_depth)
            for kind, topic in (topics or LoopbackROS2Bridge.DEFAULT_TOPICS).items()
        }

        def on_odom(msg: Odometry) -> None:
            # Update the PlatformTelemetry pose from msg.pose.pose.
            ...

        def on_battery(msg: BatteryState) -> None:
            # Update telemetry.battery_pct from msg.percentage * 100.
            ...

        node.create_subscription(Odometry, odom_topic, on_odom, qos_depth)
        node.create_subscription(BatteryState, battery_topic, on_battery, qos_depth)

    The returned bridge exposes the same ``publish_casualty`` /
    ``publish_mission_graph`` / ``publish_handoff`` / ``send_waypoint``
    surface as ``LoopbackROS2Bridge`` so ``PlatformBridge`` conformance
    holds. Use ``tests/test_bridges_contract.py`` as the acceptance
    criterion before wiring this against real hardware.
    """
    try:
        import rclpy  # noqa: F401
    except ImportError as exc:
        raise BridgeUnavailable(
            "rclpy is not installed. Install ROS2 Python bindings or use "
            "LoopbackROS2Bridge in tests."
        ) from exc
    raise NotImplementedError(
        "Real rclpy backend is a skeleton — wire up Node/publishers against "
        "a running ROS2 domain. See docs/HARDWARE_INTEGRATION.md for the "
        "per-call outline."
    )
