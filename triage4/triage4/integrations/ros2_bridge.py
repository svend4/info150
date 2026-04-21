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


def build_rclpy_bridge(*args, **kwargs):  # pragma: no cover
    """Skeleton real ROS2 backend using ``rclpy``.

    Implementation outline:
      - ``rclpy.init()``;
      - create a ``Node``;
      - declare publishers for each topic in ``LoopbackROS2Bridge.DEFAULT_TOPICS``;
      - declare a subscription to platform odometry / battery topics that
        updates the telemetry snapshot.
    """
    try:
        import rclpy  # noqa: F401
    except ImportError as exc:  # pragma: no cover
        raise BridgeUnavailable(
            "rclpy is not installed. Install ROS2 Python bindings or use "
            "LoopbackROS2Bridge in tests."
        ) from exc
    raise NotImplementedError(
        "Real rclpy backend is a skeleton — wire up Node/publishers against "
        "a running ROS2 domain."
    )
