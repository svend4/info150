import pytest

from triage4.core.models import CasualtyNode, GeoPose
from triage4.graph.casualty_graph import CasualtyGraph
from triage4.graph.mission_graph import MissionGraph
from triage4.integrations import (
    BridgeUnavailable,
    LoopbackMAVLinkBridge,
    LoopbackROS2Bridge,
    LoopbackSpotBridge,
    LoopbackWebSocketBridge,
    PlatformBridge,
    PlatformTelemetry,
    build_bosdyn_bridge,
    build_pymavlink_bridge,
    build_rclpy_bridge,
    build_fastapi_websocket_bridge,
)


def _node(cid: str = "C1") -> CasualtyNode:
    return CasualtyNode(
        id=cid,
        location=GeoPose(x=10.0, y=20.0),
        platform_source="sim_uav",
        confidence=0.9,
        status="assessed",
        triage_priority="immediate",
    )


@pytest.mark.parametrize(
    "factory",
    [
        lambda: LoopbackWebSocketBridge(),
        lambda: LoopbackMAVLinkBridge(),
        lambda: LoopbackROS2Bridge(),
        lambda: LoopbackSpotBridge(),
    ],
)
def test_bridges_implement_platform_bridge_protocol(factory):
    bridge = factory()
    assert isinstance(bridge, PlatformBridge)
    assert isinstance(bridge.telemetry, PlatformTelemetry)
    assert bridge.platform_id == bridge.telemetry.platform_id

    bridge.publish_casualty(_node())
    bridge.publish_mission_graph(MissionGraph())
    bridge.publish_handoff({"priority": "immediate"})
    bridge.send_waypoint(GeoPose(x=1.0, y=2.0))

    bridge.close()
    assert bridge.telemetry.connected is False


# --- WebSocket bridge -------------------------------------------------------


def test_websocket_records_everything_in_order():
    bridge = LoopbackWebSocketBridge()
    bridge.publish_casualty(_node("C1"))
    bridge.publish_handoff({"priority": "delayed"})
    assert [h["kind"] for h in bridge.history] == ["casualty", "handoff"]


def test_websocket_scene_uses_in4n_adapter():
    bridge = LoopbackWebSocketBridge()
    graph = CasualtyGraph()
    graph.upsert(_node("C1"))
    bridge.publish_scene(graph)
    scene = bridge.history[-1]
    assert scene["kind"] == "scene"
    assert "nodes" in scene["payload"]


def test_websocket_after_close_raises():
    bridge = LoopbackWebSocketBridge()
    bridge.close()
    with pytest.raises(RuntimeError):
        bridge.publish_casualty(_node())


def test_websocket_history_capped():
    bridge = LoopbackWebSocketBridge(max_history=3)
    for i in range(5):
        bridge.publish_handoff({"i": i})
    assert len(bridge.history) == 3


# --- MAVLink bridge ---------------------------------------------------------


def test_mavlink_step_moves_toward_waypoint():
    bridge = LoopbackMAVLinkBridge(
        start_pose=GeoPose(0.0, 0.0), speed=10.0, drain_per_metre=0.5
    )
    bridge.send_waypoint(GeoPose(x=100.0, y=0.0))
    bridge.step(1.0)  # 10 m
    assert bridge.telemetry.pose.x == pytest.approx(10.0, rel=1e-6)
    assert bridge.telemetry.battery_pct == pytest.approx(100.0 - 5.0, rel=1e-6)


def test_mavlink_arrives_at_waypoint():
    bridge = LoopbackMAVLinkBridge(start_pose=GeoPose(0.0, 0.0), speed=10.0)
    bridge.send_waypoint(GeoPose(x=5.0, y=0.0))
    bridge.step(1.0)  # distance only 5 m → arrive
    assert bridge.telemetry.pose.x == pytest.approx(5.0)


def test_mavlink_build_pymavlink_raises_when_missing():
    try:
        import pymavlink  # noqa: F401
    except ImportError:
        with pytest.raises(BridgeUnavailable):
            build_pymavlink_bridge()
    else:
        pytest.skip("pymavlink installed")


# --- ROS2 bridge ------------------------------------------------------------


def test_ros2_publishes_under_expected_topics():
    bridge = LoopbackROS2Bridge()
    bridge.publish_casualty(_node("C1"))
    casualty_msgs = bridge.published_on("casualty")
    assert len(casualty_msgs) == 1
    assert casualty_msgs[0]["topic"] == "/triage4/casualty"


def test_ros2_inject_telemetry_populates_snapshot():
    bridge = LoopbackROS2Bridge()
    bridge.inject_telemetry(
        pose=GeoPose(x=7.0, y=8.0), battery_pct=42.0, extra={"link": "wifi"}
    )
    assert bridge.telemetry.pose.x == 7.0
    assert bridge.telemetry.battery_pct == 42.0
    assert bridge.telemetry.extra["link"] == "wifi"


def test_ros2_published_on_unknown_kind_raises():
    bridge = LoopbackROS2Bridge()
    with pytest.raises(KeyError):
        bridge.published_on("nonsense")


def test_ros2_build_rclpy_raises_when_missing():
    try:
        import rclpy  # noqa: F401
    except ImportError:
        with pytest.raises(BridgeUnavailable):
            build_rclpy_bridge()
    else:
        pytest.skip("rclpy installed")


# --- Spot bridge ------------------------------------------------------------


def test_spot_walk_moves_and_drains():
    bridge = LoopbackSpotBridge(
        start_pose=GeoPose(0.0, 0.0), speed=2.0, rough_terrain=False
    )
    bridge.set_gait("walk")
    bridge.send_waypoint(GeoPose(x=4.0, y=0.0))
    bridge.step(1.0)  # 2 m
    assert bridge.telemetry.pose.x == pytest.approx(2.0)
    assert bridge.telemetry.battery_pct < 100.0


def test_spot_rough_terrain_drains_faster():
    smooth = LoopbackSpotBridge(speed=2.0, rough_terrain=False)
    rough = LoopbackSpotBridge(speed=2.0, rough_terrain=True)
    for b in (smooth, rough):
        b.send_waypoint(GeoPose(x=100.0, y=0.0))
        b.step(1.0)
    assert rough.telemetry.battery_pct < smooth.telemetry.battery_pct


def test_spot_sit_does_not_walk():
    bridge = LoopbackSpotBridge()
    bridge.set_gait("sit")
    bridge.send_waypoint(GeoPose(x=5.0, y=0.0))
    # Waypoint transitions to walk implicitly, so step moves.
    bridge.step(0.0)
    start_x = bridge.telemetry.pose.x
    assert start_x == 0.0


def test_spot_invalid_gait_raises():
    bridge = LoopbackSpotBridge()
    with pytest.raises(ValueError):
        bridge.set_gait("fly")


def test_spot_build_bosdyn_raises_when_missing():
    try:
        import bosdyn  # noqa: F401
    except ImportError:
        with pytest.raises(BridgeUnavailable):
            build_bosdyn_bridge()
    else:
        pytest.skip("bosdyn installed")


# --- skeleton factories -----------------------------------------------------


def test_fastapi_websocket_factory_is_skeleton():
    with pytest.raises(NotImplementedError):
        build_fastapi_websocket_bridge()
