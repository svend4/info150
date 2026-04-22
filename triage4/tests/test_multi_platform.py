"""Tests for the MultiPlatformManager orchestrator."""

from __future__ import annotations

import time

import pytest

from triage4.core.models import CasualtyNode, GeoPose
from triage4.graph.mission_graph import MissionGraph
from triage4.integrations import (
    DispatchResult,
    LoopbackMAVLinkBridge,
    LoopbackROS2Bridge,
    LoopbackSpotBridge,
    MultiPlatformManager,
    NoHealthyPlatform,
    PlatformBridge,
    PlatformNotFound,
)


def _uav(pid: str = "uav", battery: float = 90.0) -> LoopbackMAVLinkBridge:
    b = LoopbackMAVLinkBridge(platform_id=pid)
    b._telemetry.battery_pct = battery
    return b


def _spot(pid: str = "spot", battery: float = 80.0) -> LoopbackSpotBridge:
    b = LoopbackSpotBridge(platform_id=pid)
    b._telemetry.battery_pct = battery
    return b


def _ros(pid: str = "ros") -> LoopbackROS2Bridge:
    return LoopbackROS2Bridge(platform_id=pid)


def _casualty() -> CasualtyNode:
    return CasualtyNode(
        id="C1",
        location=GeoPose(x=0.0, y=0.0),
        platform_source="test",
        confidence=0.9,
        status="assessed",
        triage_priority="immediate",
    )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def test_manager_registers_bridges_via_ctor():
    m = MultiPlatformManager([_uav(), _spot()])
    assert m.platform_ids == ["spot", "uav"]
    assert len(m) == 2


def test_manager_register_and_unregister():
    m = MultiPlatformManager()
    m.register(_uav("uav_a"))
    m.register(_spot("spot_a"))
    assert "uav_a" in m
    assert "spot_a" in m

    m.unregister("uav_a")
    assert "uav_a" not in m
    assert len(m) == 1


def test_manager_register_rejects_duplicate_platform_id():
    m = MultiPlatformManager([_uav("dup")])
    with pytest.raises(ValueError):
        m.register(_uav("dup"))


def test_manager_unregister_unknown_raises():
    m = MultiPlatformManager()
    with pytest.raises(PlatformNotFound):
        m.unregister("ghost")


def test_manager_get_returns_registered_bridge():
    uav = _uav("uav_b")
    m = MultiPlatformManager([uav])
    assert m.get("uav_b") is uav


# ---------------------------------------------------------------------------
# PlatformBridge protocol conformance
# ---------------------------------------------------------------------------


def test_manager_satisfies_platform_bridge_protocol():
    m = MultiPlatformManager([_uav(), _spot()])
    assert isinstance(m, PlatformBridge)
    assert m.platform_id == "triage4:multi"


def test_manager_telemetry_reports_all_connected_and_min_battery():
    m = MultiPlatformManager([_uav("u", battery=90.0), _spot("s", battery=60.0)])
    tm = m.telemetry
    assert tm.connected is True
    assert tm.battery_pct == 60.0
    assert tm.extra["member_count"] == 2


def test_manager_telemetry_reports_disconnected_if_any_member_disconnects():
    uav = _uav("u")
    m = MultiPlatformManager([uav, _spot("s")])
    uav.close()
    assert m.telemetry.connected is False


def test_manager_telemetry_handles_empty_registry():
    m = MultiPlatformManager()
    tm = m.telemetry
    assert tm.connected is False
    assert tm.extra == {}


# ---------------------------------------------------------------------------
# Broadcast / targeted publish
# ---------------------------------------------------------------------------


def test_publish_casualty_broadcasts_to_all():
    uav = _uav()
    ros = _ros()
    m = MultiPlatformManager([uav, ros])
    m.publish_casualty(_casualty())
    assert len(uav.published) == 1
    assert len(ros.published_on("casualty")) == 1


def test_publish_casualty_targets_single_platform():
    uav = _uav()
    ros = _ros()
    m = MultiPlatformManager([uav, ros])
    m.publish_casualty(_casualty(), platform_id="ros")
    assert uav.published == []
    assert len(ros.published_on("casualty")) == 1


def test_publish_mission_graph_broadcasts():
    uav = _uav()
    ros = _ros()
    m = MultiPlatformManager([uav, ros])
    m.publish_mission_graph(MissionGraph())
    assert any(kind == "mission_graph" for kind, _ in uav.published)
    assert len(ros.published_on("mission_graph")) == 1


def test_publish_handoff_broadcasts():
    uav = _uav()
    ros = _ros()
    m = MultiPlatformManager([uav, ros])
    m.publish_handoff({"medic": "alpha"})
    assert any(kind == "handoff" for kind, _ in uav.published)
    assert len(ros.published_on("handoff")) == 1


def test_publish_with_unknown_platform_id_raises():
    m = MultiPlatformManager([_uav()])
    with pytest.raises(PlatformNotFound):
        m.publish_casualty(_casualty(), platform_id="ghost")


# ---------------------------------------------------------------------------
# Waypoint dispatch with health gating
# ---------------------------------------------------------------------------


def test_send_waypoint_targets_specific_platform_when_healthy():
    uav = _uav()
    m = MultiPlatformManager([uav])
    result = m.send_waypoint(GeoPose(x=10.0, y=5.0), platform_id="uav")
    assert isinstance(result, DispatchResult)
    assert result.accepted is True
    assert result.platform_id == "uav"
    assert uav.waypoint is not None


def test_send_waypoint_refuses_unhealthy_platform():
    uav = _uav()
    uav._telemetry.last_update_ts = time.time() - 60.0
    m = MultiPlatformManager([uav], max_staleness_s=5.0)
    result = m.send_waypoint(GeoPose(x=1.0, y=1.0), platform_id="uav")
    assert result.accepted is False
    assert any("stale" in r for r in result.reasons)
    assert uav.waypoint is None


def test_send_waypoint_auto_picks_healthiest_platform():
    low = _uav("low", battery=60.0)
    high = _uav("high", battery=95.0)
    m = MultiPlatformManager([low, high])
    result = m.send_waypoint(GeoPose(x=1.0, y=1.0))
    assert result.accepted is True
    assert result.platform_id == "high"
    assert low.waypoint is None
    assert high.waypoint is not None


def test_send_waypoint_raises_when_no_healthy_platform():
    uav = _uav()
    uav.close()
    m = MultiPlatformManager([uav])
    with pytest.raises(NoHealthyPlatform):
        m.send_waypoint(GeoPose(x=1.0, y=1.0))


def test_send_waypoint_raises_on_unknown_target():
    m = MultiPlatformManager([_uav()])
    with pytest.raises(PlatformNotFound):
        m.send_waypoint(GeoPose(x=1.0, y=1.0), platform_id="ghost")


# ---------------------------------------------------------------------------
# Health aggregation
# ---------------------------------------------------------------------------


def test_health_returns_per_platform_report():
    uav = _uav()
    spot = _spot()
    m = MultiPlatformManager([uav, spot])
    reports = m.health()
    assert set(reports) == {"uav", "spot"}
    assert reports["uav"].ok is True
    assert reports["spot"].ok is True


def test_healthy_platforms_excludes_unhealthy():
    uav_ok = _uav("ok")
    uav_bad = _uav("bad")
    uav_bad.close()
    m = MultiPlatformManager([uav_ok, uav_bad])
    assert m.healthy_platforms() == ["ok"]


def test_healthy_platforms_respects_low_battery_gate():
    uav = _uav("u", battery=10.0)
    m = MultiPlatformManager([uav])
    # Low battery → health.ok is True but safe_to_dispatch is False.
    assert m.healthy_platforms() == []


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


def test_close_disconnects_all_members():
    uav = _uav()
    ros = _ros()
    m = MultiPlatformManager([uav, ros])
    m.close()
    assert uav.telemetry.connected is False
    assert ros.telemetry.connected is False
