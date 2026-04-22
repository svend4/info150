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


def build_rclpy_bridge(
    platform_id: str = "triage4_node",
    topics: dict[str, str] | None = None,
    *,
    odom_topic: str = "/odom",
    battery_topic: str = "/battery_state",
    qos_depth: int = 10,
    start_executor: bool = True,
):
    """Build a real ``ROS2Bridge`` against a running ROS2 domain.

    Steps:

    1. Lazy-import ``rclpy`` + ``std_msgs.msg.String`` + telemetry
       message classes. Raises ``BridgeUnavailable`` if any are
       missing (the ROS2 Python bindings are usually apt-installed,
       not pip-installed — the error message says so).
    2. ``rclpy.init()`` if not already done, then create a fresh
       ``Node``.
    3. Instantiate ``ROS2Bridge`` with the node + ``String`` message
       class, wire up the default odometry + battery subscriptions,
       and (optionally) start the spin_once executor thread.

    Compatible with ``rclpy`` ≥ Humble (2022).

    For local dev against a ROS2 simulator, source the workspace and
    ensure ``ROS_DOMAIN_ID`` is set first. See ``docs/PHASE_10_SITL.md``.
    """
    try:
        import rclpy
        from rclpy.node import Node
        from std_msgs.msg import String
    except ImportError as exc:
        raise BridgeUnavailable(
            "rclpy / std_msgs not importable. Install ROS2 Python bindings "
            "(usually 'apt install ros-humble-rclpy ros-humble-std-msgs') "
            "or use LoopbackROS2Bridge in tests."
        ) from exc

    # Telemetry message classes — optional: if the user doesn't want
    # telemetry subscriptions, pass ``odom_topic=None`` / ``battery_topic=None``.
    try:
        from nav_msgs.msg import Odometry
        odom_cls: type | None = Odometry
    except ImportError:
        odom_cls = None
    try:
        from sensor_msgs.msg import BatteryState
        battery_cls: type | None = BatteryState
    except ImportError:
        battery_cls = None

    if not rclpy.ok():
        rclpy.init()

    node = Node(platform_id)

    from triage4.integrations.rclpy_bridge import ROS2Bridge
    bridge = ROS2Bridge(
        node=node,
        string_msg_cls=String,
        platform_id=platform_id,
        topics=topics,
        qos_depth=qos_depth,
    )

    if odom_cls is not None and odom_topic:
        bridge.subscribe_defaults(
            odometry_msg_cls=odom_cls,
            odom_topic=odom_topic,
            battery_msg_cls=battery_cls if battery_topic else None,
            battery_topic=battery_topic or "/battery_state",
            qos_depth=qos_depth,
        )

    if start_executor:
        bridge.start_executor_thread()
    return bridge
