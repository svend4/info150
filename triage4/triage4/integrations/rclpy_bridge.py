"""Real rclpy-backed ``PlatformBridge`` implementation.

Companion to ``LoopbackROS2Bridge``. Never imports ``rclpy`` at
module load; the factory in ``ros2_bridge.py`` lazy-imports the
SDK and injects the resulting ``Node`` + ``String`` message class.
Unit tests inject a fake node with the same surface — no SDK
required in CI.

Responsibilities:
- own one publisher per triage4 topic (``/triage4/casualty``,
  ``/triage4/mission_graph``, ``/triage4/handoff``, ``/triage4/waypoint``);
- subscribe to ``/odom`` (``nav_msgs/Odometry``-compatible) and
  ``/battery_state`` (``sensor_msgs/BatteryState``-compatible) to
  update ``PlatformTelemetry``;
- translate ``CasualtyNode`` / ``MissionGraph`` to JSON payloads
  inside ``std_msgs/String`` so no custom ROS2 interfaces need to
  be compiled in the companion-computer image;
- own an executor thread so the bridge is self-running; callers can
  opt out with ``start_executor=False`` and drive ``spin_once`` by
  hand.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict

from triage4.core.models import CasualtyNode, GeoPose
from triage4.graph.mission_graph import MissionGraph
from triage4.integrations.platform_bridge import PlatformTelemetry


_DEFAULT_TOPICS: dict[str, str] = {
    "casualty": "/triage4/casualty",
    "mission_graph": "/triage4/mission_graph",
    "handoff": "/triage4/handoff",
    "waypoint": "/triage4/waypoint",
}


class ROS2Bridge:
    """ROS2 ``PlatformBridge`` driven by a live ``rclpy.node.Node``.

    The bridge keeps the ROS2-specific dependencies out of the
    constructor signature: pass in a node and the message class you
    want to use for ``publish_*`` (default JSON-in-``std_msgs/String``
    keeps interface compilation out of the loop).
    """

    def __init__(
        self,
        node,
        string_msg_cls,
        *,
        platform_id: str = "ros2_node",
        topics: dict[str, str] | None = None,
        qos_depth: int = 10,
    ) -> None:
        if node is None:
            raise ValueError("node must not be None")
        if string_msg_cls is None:
            raise ValueError("string_msg_cls must not be None")

        self._node = node
        self._string_msg_cls = string_msg_cls
        self._platform_id = str(platform_id)
        self._topics = dict(_DEFAULT_TOPICS)
        if topics:
            self._topics.update(topics)

        self._publishers = {
            kind: node.create_publisher(string_msg_cls, topic, qos_depth)
            for kind, topic in self._topics.items()
        }

        self._telemetry = PlatformTelemetry(
            platform_id=self._platform_id,
            pose=GeoPose(0.0, 0.0, 0.0, 0.0, frame="odom"),
            battery_pct=100.0,
            connected=True,
            last_update_ts=time.time(),
        )

        self._closed = False
        self._executor_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    # -- PlatformBridge surface -----------------------------------------

    @property
    def platform_id(self) -> str:
        return self._platform_id

    @property
    def telemetry(self) -> PlatformTelemetry:
        return self._telemetry

    @property
    def topics(self) -> dict[str, str]:
        return dict(self._topics)

    def publish_casualty(self, node: CasualtyNode) -> None:
        self._emit("casualty", node.to_dict())

    def publish_mission_graph(self, graph: MissionGraph) -> None:
        self._emit("mission_graph", graph.as_json())

    def publish_handoff(self, payload: dict) -> None:
        self._emit("handoff", dict(payload))

    def send_waypoint(self, pose: GeoPose) -> None:
        self._emit("waypoint", asdict(pose))

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._stop_event.set()
        if self._executor_thread is not None and self._executor_thread.is_alive():
            self._executor_thread.join(timeout=2.0)
        try:
            self._node.destroy_node()
        except Exception:
            pass
        self._telemetry.connected = False

    # -- telemetry callbacks (wired by subscribe_defaults) ---------------

    def on_odometry(self, msg) -> None:
        """Callback for ``nav_msgs/Odometry``-shaped messages.

        Accepts either a full Odometry or a PoseStamped — the code
        reads only ``pose.pose`` ducks.
        """
        pose_obj = self._nested(msg, "pose.pose") or self._nested(msg, "pose")
        if pose_obj is None:
            return
        position = getattr(pose_obj, "position", None)
        if position is None:
            return
        self._telemetry.pose = GeoPose(
            x=float(getattr(position, "x", 0.0)),
            y=float(getattr(position, "y", 0.0)),
            z=float(getattr(position, "z", 0.0)),
            frame="odom",
        )
        self._telemetry.last_update_ts = time.time()

    def on_battery_state(self, msg) -> None:
        """Callback for ``sensor_msgs/BatteryState``.

        ``percentage`` is in [0, 1] per the ROS2 spec; we surface it
        as [0, 100] to stay consistent with the rest of triage4.
        """
        pct = getattr(msg, "percentage", None)
        if pct is None:
            return
        try:
            value = float(pct)
        except (TypeError, ValueError):
            return
        self._telemetry.battery_pct = max(0.0, min(100.0, value * 100.0))
        self._telemetry.last_update_ts = time.time()

    def subscribe_defaults(
        self,
        odometry_msg_cls,
        odom_topic: str = "/odom",
        battery_msg_cls=None,
        battery_topic: str = "/battery_state",
        qos_depth: int = 10,
    ) -> None:
        """Wire the default telemetry subscriptions in one call."""
        self._node.create_subscription(
            odometry_msg_cls, odom_topic, self.on_odometry, qos_depth,
        )
        if battery_msg_cls is not None:
            self._node.create_subscription(
                battery_msg_cls, battery_topic, self.on_battery_state, qos_depth,
            )

    # -- executor thread -------------------------------------------------

    def start_executor_thread(self, tick_s: float = 0.05) -> None:
        """Drive ``rclpy.spin_once`` in a background thread."""
        if self._executor_thread is not None and self._executor_thread.is_alive():
            return
        self._stop_event.clear()

        def _loop() -> None:
            spin_once = getattr(self._node, "spin_once", None)
            # ``rclpy`` hangs spin_once off the top-level rclpy module,
            # not the node. Callers can inject either — we detect at
            # runtime.
            if spin_once is None:
                try:
                    import rclpy  # noqa: F401
                    spin_once = rclpy.spin_once  # type: ignore[attr-defined]
                except ImportError:
                    spin_once = None
            if spin_once is None:
                return

            while not self._stop_event.is_set() and not self._closed:
                try:
                    spin_once(self._node, timeout_sec=tick_s)
                except Exception:
                    time.sleep(tick_s)

        self._executor_thread = threading.Thread(
            target=_loop, daemon=True, name="rclpy_exec",
        )
        self._executor_thread.start()

    # -- internals -------------------------------------------------------

    def _emit(self, kind: str, payload: dict) -> None:
        if self._closed:
            raise RuntimeError("bridge is closed")
        pub = self._publishers.get(kind)
        if pub is None:
            raise KeyError(f"no publisher for kind {kind!r}")
        msg = self._string_msg_cls()
        msg.data = json.dumps(payload, separators=(",", ":"))
        pub.publish(msg)
        self._telemetry.last_update_ts = time.time()

    @staticmethod
    def _nested(obj, path: str):
        """Dotted-path getattr that returns None on any miss."""
        current = obj
        for part in path.split("."):
            current = getattr(current, part, None)
            if current is None:
                return None
        return current
