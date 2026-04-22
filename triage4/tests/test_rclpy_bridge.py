"""Tests for ``ROS2Bridge`` using an injected fake Node.

No rclpy installed in CI — the bridge is tested via a fake Node
that captures publishers + subscriptions + publish calls. The
lazy-imported factory path is tested separately.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import pytest

from triage4.core.models import CasualtyNode, GeoPose
from triage4.graph.mission_graph import MissionGraph
from triage4.integrations.platform_bridge import PlatformBridge
from triage4.integrations.rclpy_bridge import ROS2Bridge


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeStringMsg:
    """std_msgs/String-compatible: has a ``.data`` field."""

    def __init__(self) -> None:
        self.data: str = ""


class _FakePublisher:
    def __init__(self, topic: str) -> None:
        self.topic = topic
        self.published: list[_FakeStringMsg] = []

    def publish(self, msg) -> None:
        self.published.append(msg)


@dataclass
class _FakeSubscription:
    msg_cls: type
    topic: str
    callback: callable
    qos: int


@dataclass
class _FakeNode:
    name: str = "ros2_test"
    publishers: dict[str, _FakePublisher] = field(default_factory=dict)
    subscriptions: list[_FakeSubscription] = field(default_factory=list)
    destroyed: bool = False

    def create_publisher(self, msg_cls, topic: str, qos: int) -> _FakePublisher:
        pub = _FakePublisher(topic)
        self.publishers[topic] = pub
        return pub

    def create_subscription(self, msg_cls, topic: str, callback, qos: int):
        self.subscriptions.append(_FakeSubscription(msg_cls, topic, callback, qos))

    def destroy_node(self) -> None:
        self.destroyed = True


@dataclass
class _FakePose:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass
class _FakeOdomPose:
    position: _FakePose = field(default_factory=_FakePose)


@dataclass
class _FakeNestedPose:
    pose: _FakeOdomPose = field(default_factory=_FakeOdomPose)


@dataclass
class _FakeOdometry:
    """Odometry-like: has ``pose.pose.position``."""

    pose: _FakeNestedPose = field(default_factory=_FakeNestedPose)


@dataclass
class _FakeBatteryState:
    percentage: float = 0.0


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_rejects_none_node():
    with pytest.raises(ValueError):
        ROS2Bridge(node=None, string_msg_cls=_FakeStringMsg)


def test_rejects_none_msg_cls():
    with pytest.raises(ValueError):
        ROS2Bridge(node=_FakeNode(), string_msg_cls=None)


def test_satisfies_platform_bridge_protocol():
    b = ROS2Bridge(node=_FakeNode(), string_msg_cls=_FakeStringMsg)
    assert isinstance(b, PlatformBridge)


def test_creates_publisher_per_topic():
    node = _FakeNode()
    bridge = ROS2Bridge(node=node, string_msg_cls=_FakeStringMsg)
    assert "/triage4/casualty" in node.publishers
    assert "/triage4/mission_graph" in node.publishers
    assert "/triage4/handoff" in node.publishers
    assert "/triage4/waypoint" in node.publishers
    assert bridge.topics["casualty"] == "/triage4/casualty"


def test_custom_topics_override_defaults():
    node = _FakeNode()
    bridge = ROS2Bridge(
        node=node, string_msg_cls=_FakeStringMsg,
        topics={"casualty": "/custom/casualty"},
    )
    assert bridge.topics["casualty"] == "/custom/casualty"
    assert "/custom/casualty" in node.publishers


# ---------------------------------------------------------------------------
# publish_* round-trip through JSON
# ---------------------------------------------------------------------------


def test_publish_casualty_emits_json_string():
    node = _FakeNode()
    bridge = ROS2Bridge(node=node, string_msg_cls=_FakeStringMsg)
    casualty = CasualtyNode(
        id="C1",
        location=GeoPose(x=1.5, y=2.5),
        platform_source="test",
        confidence=0.9,
        status="assessed",
        triage_priority="immediate",
    )
    bridge.publish_casualty(casualty)

    pub = node.publishers["/triage4/casualty"]
    assert len(pub.published) == 1
    data = json.loads(pub.published[0].data)
    assert data["id"] == "C1"
    assert data["triage_priority"] == "immediate"


def test_publish_mission_graph_emits_json():
    node = _FakeNode()
    bridge = ROS2Bridge(node=node, string_msg_cls=_FakeStringMsg)
    mg = MissionGraph()
    mg.assign_medic("m1", "C1")
    mg.mark_unresolved("sector-A")
    bridge.publish_mission_graph(mg)
    data = json.loads(node.publishers["/triage4/mission_graph"].published[0].data)
    assert data["medic_assignments"] == {"m1": "C1"}
    assert "sector-A" in data["unresolved_regions"]


def test_publish_handoff_emits_json():
    node = _FakeNode()
    bridge = ROS2Bridge(node=node, string_msg_cls=_FakeStringMsg)
    bridge.publish_handoff({"casualty_id": "C1", "medic": "m1"})
    data = json.loads(node.publishers["/triage4/handoff"].published[0].data)
    assert data["medic"] == "m1"


def test_send_waypoint_emits_pose_json():
    node = _FakeNode()
    bridge = ROS2Bridge(node=node, string_msg_cls=_FakeStringMsg)
    bridge.send_waypoint(GeoPose(x=3.0, y=4.0, z=5.0))
    data = json.loads(node.publishers["/triage4/waypoint"].published[0].data)
    assert data["x"] == 3.0
    assert data["y"] == 4.0
    assert data["z"] == 5.0


def test_publish_after_close_raises():
    node = _FakeNode()
    bridge = ROS2Bridge(node=node, string_msg_cls=_FakeStringMsg)
    bridge.close()
    with pytest.raises(RuntimeError):
        bridge.publish_handoff({"medic": "m1"})


# ---------------------------------------------------------------------------
# Telemetry callbacks
# ---------------------------------------------------------------------------


def test_on_odometry_updates_pose_from_nested_position():
    bridge = ROS2Bridge(node=_FakeNode(), string_msg_cls=_FakeStringMsg)
    odom = _FakeOdometry()
    odom.pose.pose.position = _FakePose(x=10.0, y=-3.0, z=0.5)
    bridge.on_odometry(odom)
    assert bridge.telemetry.pose.x == 10.0
    assert bridge.telemetry.pose.y == -3.0
    assert bridge.telemetry.pose.z == 0.5
    assert bridge.telemetry.pose.frame == "odom"


def test_on_odometry_accepts_flat_pose_stamped():
    """PoseStamped-like: pose.position directly (no nesting)."""
    bridge = ROS2Bridge(node=_FakeNode(), string_msg_cls=_FakeStringMsg)

    @dataclass
    class _PoseStamped:
        pose: _FakePose = field(default_factory=lambda: _FakePose(5.0, 6.0, 7.0))

    # Wrap _FakePose so it has .position — this keeps the test for the
    # fallback path where pose.pose is None.
    @dataclass
    class _WithPosition:
        position: _FakePose = field(default_factory=lambda: _FakePose(5.0, 6.0, 7.0))

    @dataclass
    class _Msg:
        pose: _WithPosition = field(default_factory=_WithPosition)

    bridge.on_odometry(_Msg())
    assert bridge.telemetry.pose.x == 5.0


def test_on_odometry_ignores_missing_position():
    bridge = ROS2Bridge(node=_FakeNode(), string_msg_cls=_FakeStringMsg)

    @dataclass
    class _Empty:
        pass

    before = bridge.telemetry.pose.x
    bridge.on_odometry(_Empty())
    assert bridge.telemetry.pose.x == before


def test_on_battery_state_converts_0_1_to_0_100():
    bridge = ROS2Bridge(node=_FakeNode(), string_msg_cls=_FakeStringMsg)
    bridge.on_battery_state(_FakeBatteryState(percentage=0.73))
    assert bridge.telemetry.battery_pct == pytest.approx(73.0, abs=1e-6)


def test_on_battery_state_clamps_bad_values():
    bridge = ROS2Bridge(node=_FakeNode(), string_msg_cls=_FakeStringMsg)
    bridge.on_battery_state(_FakeBatteryState(percentage=1.5))
    assert bridge.telemetry.battery_pct == 100.0


def test_on_battery_state_ignores_none_percentage():
    bridge = ROS2Bridge(node=_FakeNode(), string_msg_cls=_FakeStringMsg)
    bridge.on_battery_state(_FakeBatteryState(percentage=None))
    # default battery_pct is 100.0, must be unchanged
    assert bridge.telemetry.battery_pct == 100.0


# ---------------------------------------------------------------------------
# Default subscriptions
# ---------------------------------------------------------------------------


def test_subscribe_defaults_registers_odom_and_battery():
    node = _FakeNode()
    bridge = ROS2Bridge(node=node, string_msg_cls=_FakeStringMsg)
    bridge.subscribe_defaults(
        odometry_msg_cls=_FakeOdometry,
        odom_topic="/odom",
        battery_msg_cls=_FakeBatteryState,
        battery_topic="/battery_state",
    )
    topics = [s.topic for s in node.subscriptions]
    assert "/odom" in topics
    assert "/battery_state" in topics


def test_subscribe_defaults_skips_battery_when_none():
    node = _FakeNode()
    bridge = ROS2Bridge(node=node, string_msg_cls=_FakeStringMsg)
    bridge.subscribe_defaults(
        odometry_msg_cls=_FakeOdometry,
        odom_topic="/odom",
        battery_msg_cls=None,
    )
    topics = [s.topic for s in node.subscriptions]
    assert "/battery_state" not in topics


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


def test_close_destroys_node():
    node = _FakeNode()
    bridge = ROS2Bridge(node=node, string_msg_cls=_FakeStringMsg)
    bridge.close()
    assert node.destroyed is True
    assert bridge.telemetry.connected is False


def test_close_is_idempotent():
    node = _FakeNode()
    bridge = ROS2Bridge(node=node, string_msg_cls=_FakeStringMsg)
    bridge.close()
    bridge.close()


# ---------------------------------------------------------------------------
# Factory — BridgeUnavailable path
# ---------------------------------------------------------------------------


def test_build_rclpy_bridge_raises_bridge_unavailable_without_sdk(monkeypatch):
    import builtins
    real_import = builtins.__import__

    def _blocker(name, *args, **kwargs):
        if name == "rclpy" or name.startswith("rclpy."):
            raise ImportError("simulated: rclpy not installed")
        if name == "std_msgs" or name.startswith("std_msgs."):
            raise ImportError("simulated: std_msgs not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocker)

    from triage4.integrations.platform_bridge import BridgeUnavailable
    from triage4.integrations.ros2_bridge import build_rclpy_bridge
    with pytest.raises(BridgeUnavailable):
        build_rclpy_bridge()
