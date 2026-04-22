"""Protocol-conformance + health-check tests for every ``PlatformBridge``.

Phase 10 preparation. Any bridge — Loopback or real-backend — must
satisfy the same contract so the rest of triage4 can swap them
transparently. These tests run against the four loopback bridges that
ship with triage4 and establish the acceptance criterion that real
bridges must also meet.

Real-backend factories (``build_rclpy_bridge``, ``build_pymavlink_bridge``,
``build_bosdyn_bridge``, ``build_fastapi_websocket_bridge``) are tested
for failure modes (raise ``BridgeUnavailable`` or ``NotImplementedError``,
never silently succeed) but not for live wiring — that requires real
hardware.
"""

from __future__ import annotations

import math
import time

import pytest

from triage4.core.models import CasualtyNode, GeoPose
from triage4.graph.mission_graph import MissionGraph
from triage4.integrations import (
    BridgeHealth,
    LoopbackMAVLinkBridge,
    LoopbackROS2Bridge,
    LoopbackSpotBridge,
    LoopbackWebSocketBridge,
    PlatformBridge,
    PlatformTelemetry,
    build_bosdyn_bridge,
    build_fastapi_websocket_bridge,
    build_pymavlink_bridge,
    build_rclpy_bridge,
    check_bridge_health,
    check_telemetry,
    safe_to_dispatch,
)


def _sample_casualty() -> CasualtyNode:
    return CasualtyNode(
        id="C1",
        location=GeoPose(x=1.0, y=2.0),
        platform_source="test",
        confidence=0.9,
        status="assessed",
        triage_priority="immediate",
    )


LOOPBACK_FACTORIES = [
    lambda: LoopbackROS2Bridge(platform_id="ros2_test"),
    lambda: LoopbackMAVLinkBridge(platform_id="uav_test"),
    lambda: LoopbackSpotBridge(platform_id="spot_test"),
    lambda: LoopbackWebSocketBridge(platform_id="dash_test"),
]


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("factory", LOOPBACK_FACTORIES)
def test_bridge_implements_platform_bridge_protocol(factory):
    bridge = factory()
    assert isinstance(bridge, PlatformBridge)
    assert bridge.platform_id
    assert isinstance(bridge.telemetry, PlatformTelemetry)


@pytest.mark.parametrize("factory", LOOPBACK_FACTORIES)
def test_bridge_roundtrips_casualty_mission_handoff_waypoint(factory):
    bridge = factory()
    bridge.publish_casualty(_sample_casualty())
    bridge.publish_mission_graph(MissionGraph())
    bridge.publish_handoff({"medic": "alpha", "casualty_id": "C1"})
    bridge.send_waypoint(GeoPose(x=5.0, y=5.0))
    # No exception == pass. Each bridge records its own way; we
    # verify only the publish path, not implementation internals.
    bridge.close()


@pytest.mark.parametrize("factory", LOOPBACK_FACTORIES)
def test_bridge_close_disconnects(factory):
    bridge = factory()
    assert bridge.telemetry.connected is True
    bridge.close()
    assert bridge.telemetry.connected is False


# ---------------------------------------------------------------------------
# BridgeHealth semantics
# ---------------------------------------------------------------------------


def test_check_bridge_health_ok_on_fresh_loopback():
    bridge = LoopbackROS2Bridge(platform_id="ros2_a")
    health = check_bridge_health(bridge)
    assert isinstance(health, BridgeHealth)
    assert health.ok is True
    assert health.connected is True
    assert health.platform_id == "ros2_a"
    assert health.reasons == []
    assert safe_to_dispatch(health) is True


def test_check_bridge_health_flags_stale_telemetry():
    bridge = LoopbackMAVLinkBridge(platform_id="uav_b")
    # Force an old timestamp.
    bridge._telemetry.last_update_ts = time.time() - 30.0
    health = check_bridge_health(bridge, max_staleness_s=5.0)
    assert health.ok is False
    assert any("stale" in r for r in health.reasons)
    assert safe_to_dispatch(health) is False


def test_check_bridge_health_flags_disconnected():
    bridge = LoopbackSpotBridge(platform_id="spot_c")
    bridge.close()
    health = check_bridge_health(bridge)
    assert health.ok is False
    assert any("disconnected" in r for r in health.reasons)
    assert safe_to_dispatch(health) is False


def test_check_bridge_health_flags_out_of_range_battery():
    bridge = LoopbackMAVLinkBridge(platform_id="uav_d")
    bridge._telemetry.battery_pct = 150.0
    health = check_bridge_health(bridge)
    assert health.ok is False
    assert any("battery_pct out of range" in r for r in health.reasons)


def test_check_bridge_health_low_battery_is_warning_not_failure():
    """Low battery warns but ok stays true — still usable for observation."""
    bridge = LoopbackMAVLinkBridge(platform_id="uav_e")
    bridge._telemetry.battery_pct = 10.0
    health = check_bridge_health(bridge)
    assert health.ok is True
    assert any("low battery" in r for r in health.reasons)
    # But dispatch should refuse.
    assert safe_to_dispatch(health) is False


def test_check_bridge_health_flags_non_finite_pose():
    bridge = LoopbackMAVLinkBridge(platform_id="uav_f")
    bridge._telemetry.pose = GeoPose(x=float("nan"), y=0.0)
    health = check_bridge_health(bridge)
    assert health.ok is False
    assert any("non-finite pose" in r for r in health.reasons)


def test_check_bridge_health_flags_platform_id_mismatch():
    bridge = LoopbackROS2Bridge(platform_id="ros2_g")
    bridge._telemetry.platform_id = "different"
    health = check_bridge_health(bridge)
    assert health.ok is False
    assert any("platform_id mismatch" in r for r in health.reasons)


def test_check_telemetry_works_without_bridge():
    tm = PlatformTelemetry(
        platform_id="offline_log",
        pose=GeoPose(x=0.0, y=0.0),
        battery_pct=80.0,
        connected=True,
        last_update_ts=time.time(),
    )
    health = check_telemetry(tm)
    assert health.ok is True
    assert health.platform_id == "offline_log"


def test_check_telemetry_empty_platform_id_is_failure():
    tm = PlatformTelemetry(
        platform_id="",
        connected=True,
        last_update_ts=time.time(),
    )
    health = check_telemetry(tm)
    assert health.ok is False
    assert any("empty platform_id" in r for r in health.reasons)


def test_check_telemetry_disables_staleness_when_zero():
    tm = PlatformTelemetry(
        platform_id="log",
        pose=GeoPose(x=0.0, y=0.0),
        battery_pct=80.0,
        connected=True,
        last_update_ts=time.time() - 10_000.0,
    )
    health = check_telemetry(tm, max_staleness_s=0.0)
    assert health.ok is True
    assert not any("stale" in r for r in health.reasons)


# ---------------------------------------------------------------------------
# Real-backend factory failure modes
# ---------------------------------------------------------------------------


def test_build_rclpy_bridge_raises_without_sdk_or_not_implemented():
    """Either BridgeUnavailable (SDK missing) or NotImplementedError
    (SDK present, wiring unfinished). Must never silently succeed."""
    from triage4.integrations.platform_bridge import BridgeUnavailable

    with pytest.raises((BridgeUnavailable, NotImplementedError)):
        build_rclpy_bridge()


def test_build_pymavlink_bridge_raises_without_sdk_or_not_implemented():
    from triage4.integrations.platform_bridge import BridgeUnavailable

    with pytest.raises((BridgeUnavailable, NotImplementedError)):
        build_pymavlink_bridge()


def test_build_bosdyn_bridge_raises_without_sdk_or_not_implemented():
    from triage4.integrations.platform_bridge import BridgeUnavailable

    with pytest.raises((BridgeUnavailable, NotImplementedError)):
        build_bosdyn_bridge()


def test_build_fastapi_websocket_bridge_raises_not_implemented():
    # FastAPI is in the core deps, so this factory must raise
    # NotImplementedError (wiring unfinished) rather than BridgeUnavailable.
    with pytest.raises(NotImplementedError):
        build_fastapi_websocket_bridge()


# ---------------------------------------------------------------------------
# Loopback simulator semantics (lightweight sanity, not exhaustive)
# ---------------------------------------------------------------------------


def test_mavlink_loopback_step_moves_toward_waypoint():
    bridge = LoopbackMAVLinkBridge(platform_id="uav", speed=10.0)
    bridge.send_waypoint(GeoPose(x=100.0, y=0.0))
    start_x = bridge.telemetry.pose.x
    bridge.step(dt_s=1.0)
    assert bridge.telemetry.pose.x > start_x
    assert math.isfinite(bridge.telemetry.pose.x)


def test_spot_loopback_respects_gait():
    bridge = LoopbackSpotBridge(platform_id="spot", speed=1.0)
    bridge.send_waypoint(GeoPose(x=10.0, y=0.0))
    # send_waypoint auto-transitions from stand to walk.
    assert bridge.gait == "walk"
    bridge.set_gait("sit")
    start = bridge.telemetry.pose.x
    bridge.step(dt_s=5.0)
    # Sitting = no motion.
    assert bridge.telemetry.pose.x == start


def test_ros2_loopback_records_on_correct_topic():
    bridge = LoopbackROS2Bridge(platform_id="ros2")
    bridge.publish_casualty(_sample_casualty())
    msgs = bridge.published_on("casualty")
    assert len(msgs) == 1
    assert msgs[0]["topic"] == "/triage4/casualty"
