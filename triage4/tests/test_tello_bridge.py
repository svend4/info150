"""Tests for the Tello bridge — loopback + injected-mock real path.

No ``djitellopy`` required: ``TelloBridge`` is unit-tested via a
fake Tello object; ``build_tello_bridge`` is checked for the
BridgeUnavailable path.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from triage4.core.models import CasualtyNode, GeoPose
from triage4.graph.mission_graph import MissionGraph
from triage4.integrations import (
    LoopbackTelloBridge,
    TelloBridge,
)
from triage4.integrations.platform_bridge import (
    BridgeUnavailable,
    PlatformBridge,
)


def _casualty() -> CasualtyNode:
    return CasualtyNode(
        id="C1",
        location=GeoPose(x=1.0, y=2.0),
        platform_source="test",
        confidence=0.9,
        status="assessed",
        triage_priority="immediate",
    )


# ---------------------------------------------------------------------------
# Loopback — contract
# ---------------------------------------------------------------------------


def test_loopback_satisfies_platform_bridge_protocol():
    b = LoopbackTelloBridge()
    assert isinstance(b, PlatformBridge)


def test_loopback_publishes_in_order():
    b = LoopbackTelloBridge()
    b.publish_casualty(_casualty())
    b.publish_handoff({"medic": "m1", "casualty_id": "C1"})
    kinds = [k for k, _ in b.published]
    assert kinds == ["casualty", "handoff"]


def test_loopback_publish_mission_graph():
    b = LoopbackTelloBridge()
    mg = MissionGraph()
    mg.assign_medic("m1", "C1")
    b.publish_mission_graph(mg)
    assert any(kind == "mission_graph" for kind, _ in b.published)


def test_loopback_send_waypoint_logs_and_stores():
    b = LoopbackTelloBridge()
    b.send_waypoint(GeoPose(x=1.0, y=0.0, z=0.5))
    assert any(k == "waypoint" for k, _ in b.published)
    assert any(cmd == "waypoint" for _, cmd, _ in b.command_log)


def test_loopback_send_waypoint_after_close_raises():
    b = LoopbackTelloBridge()
    b.close()
    with pytest.raises(RuntimeError):
        b.send_waypoint(GeoPose(x=0.5, y=0.0))


# ---------------------------------------------------------------------------
# Loopback — kinematics
# ---------------------------------------------------------------------------


def test_loopback_takeoff_sets_airborne_and_altitude():
    b = LoopbackTelloBridge()
    b.takeoff()
    assert b.airborne is True
    assert b.telemetry.pose.z == pytest.approx(0.80, abs=1e-6)
    assert b.telemetry.extra["airborne"] is True
    assert b.telemetry.extra["gait"] == "hover"


def test_loopback_step_moves_toward_waypoint():
    b = LoopbackTelloBridge(speed_cm_per_s=60.0)
    b.takeoff()
    b.send_waypoint(GeoPose(x=1.0, y=0.0, z=0.0))
    b.step(dt_s=1.0)
    # 60 cm/s × 1 s = 60 cm → 0.60 m in the x direction.
    assert b.telemetry.pose.x == pytest.approx(0.60, abs=1e-6)


def test_loopback_step_does_nothing_when_grounded():
    b = LoopbackTelloBridge()
    b.send_waypoint(GeoPose(x=5.0, y=0.0, z=0.0))
    b.step(dt_s=1.0)
    assert b.telemetry.pose.x == 0.0


def test_loopback_battery_drains_while_airborne():
    b = LoopbackTelloBridge()
    b.takeoff()
    start = b.telemetry.battery_pct
    b.step(dt_s=10.0)
    assert b.telemetry.battery_pct < start


def test_loopback_land_resets_altitude_and_state():
    b = LoopbackTelloBridge()
    b.takeoff()
    b.land()
    assert b.airborne is False
    assert b.telemetry.pose.z == 0.0
    assert b.telemetry.extra["airborne"] is False


def test_loopback_battery_exhaustion_forces_land():
    b = LoopbackTelloBridge()
    b.takeoff()
    # Speed up exhaustion by advancing time a lot.
    b.step(dt_s=10_000.0)
    assert b.telemetry.battery_pct == 0.0
    assert b.airborne is False


def test_loopback_close_disconnects():
    b = LoopbackTelloBridge()
    b.takeoff()
    b.close()
    assert b.telemetry.connected is False
    assert b.airborne is False


def test_loopback_close_is_idempotent():
    b = LoopbackTelloBridge()
    b.close()
    b.close()


# ---------------------------------------------------------------------------
# Real bridge via injected fake Tello
# ---------------------------------------------------------------------------


@dataclass
class _FrameReadStub:
    frame = None


@dataclass
class _FakeTello:
    battery: float = 77.0
    is_flying: bool = False
    calls: list[tuple[str, tuple, dict]] = field(default_factory=list)
    stream_ready: bool = False
    ended: bool = False

    def get_battery(self):
        return self.battery

    def _record(self, name: str, *args, **kwargs) -> None:
        self.calls.append((name, args, kwargs))

    def takeoff(self):
        self.is_flying = True
        self._record("takeoff")

    def land(self):
        self.is_flying = False
        self._record("land")

    def move_forward(self, cm): self._record("move_forward", cm)
    def move_back(self, cm): self._record("move_back", cm)
    def move_right(self, cm): self._record("move_right", cm)
    def move_left(self, cm): self._record("move_left", cm)
    def move_up(self, cm): self._record("move_up", cm)
    def move_down(self, cm): self._record("move_down", cm)

    def end(self):
        self.ended = True

    def streamon(self):
        self.stream_ready = True

    def get_frame_read(self):
        return _FrameReadStub()


def test_real_bridge_rejects_none_tello():
    with pytest.raises(ValueError):
        TelloBridge(tello=None)


def test_real_bridge_reads_initial_battery():
    t = _FakeTello(battery=42.0)
    bridge = TelloBridge(tello=t)
    assert bridge.telemetry.battery_pct == 42.0
    bridge.close()


def test_real_bridge_satisfies_platform_bridge_protocol():
    bridge = TelloBridge(tello=_FakeTello())
    assert isinstance(bridge, PlatformBridge)
    bridge.close()


def test_send_waypoint_translates_metres_to_tello_axes():
    t = _FakeTello()
    bridge = TelloBridge(tello=t)
    bridge.send_waypoint(GeoPose(x=0.5, y=-0.3, z=0.4))
    names = [c[0] for c in t.calls]
    # x > 0 → move_forward, y < 0 → move_left, z > 0 → move_up.
    assert "move_forward" in names
    assert "move_left" in names
    assert "move_up" in names
    bridge.close()


def test_send_waypoint_clamps_below_minimum():
    t = _FakeTello()
    bridge = TelloBridge(tello=t)
    # 5 cm is below the Tello minimum (20 cm).
    bridge.send_waypoint(GeoPose(x=0.05, y=0.0, z=0.0))
    forward_calls = [c for c in t.calls if c[0] == "move_forward"]
    assert forward_calls, "expected a move_forward call"
    (cm,) = forward_calls[0][1]
    assert cm == 20  # clamped up to the minimum
    bridge.close()


def test_send_waypoint_caps_at_maximum():
    t = _FakeTello()
    bridge = TelloBridge(tello=t)
    bridge.send_waypoint(GeoPose(x=10.0, y=0.0, z=0.0))
    forward_calls = [c for c in t.calls if c[0] == "move_forward"]
    (cm,) = forward_calls[0][1]
    assert cm == 500  # clamped down to the Tello max
    bridge.close()


def test_send_waypoint_skips_zero_axis():
    t = _FakeTello()
    bridge = TelloBridge(tello=t)
    bridge.send_waypoint(GeoPose(x=0.5, y=0.0, z=0.0))
    names = {c[0] for c in t.calls}
    assert "move_forward" in names
    assert "move_right" not in names and "move_left" not in names
    assert "move_up" not in names and "move_down" not in names
    bridge.close()


def test_send_waypoint_after_close_raises():
    bridge = TelloBridge(tello=_FakeTello())
    bridge.close()
    with pytest.raises(RuntimeError):
        bridge.send_waypoint(GeoPose(x=0.5, y=0.0))


def test_publish_casualty_logs_without_raising():
    # The real bridge just prints; we care that it doesn't raise
    # and that it remains callable.
    bridge = TelloBridge(tello=_FakeTello())
    bridge.publish_casualty(_casualty())  # no assertion beyond "does not raise"
    bridge.close()


def test_close_lands_if_airborne():
    t = _FakeTello()
    bridge = TelloBridge(tello=t)
    bridge.takeoff()
    assert t.is_flying is True
    bridge.close()
    assert t.is_flying is False
    assert t.ended is True


def test_close_handles_non_flying_tello():
    t = _FakeTello()
    bridge = TelloBridge(tello=t)
    bridge.close()
    assert t.ended is True


def test_takeoff_and_land_mirror_state():
    t = _FakeTello()
    bridge = TelloBridge(tello=t)
    bridge.takeoff()
    assert bridge.telemetry.extra["airborne"] is True
    bridge.land()
    assert bridge.telemetry.extra["airborne"] is False
    bridge.close()


# ---------------------------------------------------------------------------
# Factory — BridgeUnavailable path
# ---------------------------------------------------------------------------


def test_build_tello_bridge_raises_bridge_unavailable_without_sdk(monkeypatch):
    import builtins
    real_import = builtins.__import__

    def _blocker(name, *args, **kwargs):
        if name == "djitellopy" or name.startswith("djitellopy."):
            raise ImportError("simulated: djitellopy not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocker)

    from triage4.integrations import build_tello_bridge
    with pytest.raises(BridgeUnavailable):
        build_tello_bridge()
