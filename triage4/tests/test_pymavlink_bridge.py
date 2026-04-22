"""Tests for ``PyMAVLinkBridge`` using an injected mock connection.

No pymavlink needed to run — the bridge is tested via a fake
connection object that captures outbound calls. The lazy-imported
factory path (``build_pymavlink_bridge``) is tested separately.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from triage4.core.models import CasualtyNode, GeoPose
from triage4.graph.mission_graph import MissionGraph
from triage4.integrations.platform_bridge import PlatformBridge
from triage4.integrations.pymavlink_bridge import PyMAVLinkBridge


# ---------------------------------------------------------------------------
# Fake pymavlink connection surface
# ---------------------------------------------------------------------------


@dataclass
class _FakeMAVMessage:
    """Minimal duck-typed MAVLink message."""
    _type: str
    fields: dict = field(default_factory=dict)

    def get_type(self) -> str:
        return self._type

    def __getattr__(self, name: str):
        if name in self.fields:
            return self.fields[name]
        raise AttributeError(name)


class _FakeMav:
    """Captures the outbound ``mav.*_send`` calls."""

    def __init__(self) -> None:
        self.waypoints: list[tuple] = []
        self.statustexts: list[tuple[int, bytes]] = []

    def mission_item_int_send(
        self,
        target_sys,
        target_comp,
        seq,
        frame,
        command,
        current,
        autocontinue,
        p1, p2, p3, p4,
        x, y, z,
    ):
        self.waypoints.append((target_sys, target_comp, seq, frame, command,
                               current, autocontinue,
                               p1, p2, p3, p4, x, y, z))

    def statustext_send(self, severity, text_bytes):
        self.statustexts.append((severity, text_bytes))


class _FakeConnection:
    """Smallest ``mavutil.mavlink_connection``-compatible surface."""

    def __init__(self, inbound_messages=None) -> None:
        self.mav = _FakeMav()
        self.target_system = 1
        self.target_component = 1
        self._inbound = list(inbound_messages or [])
        self._close_called = False

    def recv_match(self, type=None, blocking=False, timeout=None):
        if not self._inbound:
            return None
        return self._inbound.pop(0)

    def close(self) -> None:
        self._close_called = True


# ---------------------------------------------------------------------------
# Basic contract
# ---------------------------------------------------------------------------


def test_rejects_none_connection():
    with pytest.raises(ValueError):
        PyMAVLinkBridge(connection=None)


def test_satisfies_platform_bridge_protocol():
    bridge = PyMAVLinkBridge(connection=_FakeConnection(), platform_id="uav_a")
    assert isinstance(bridge, PlatformBridge)


def test_default_telemetry_is_populated():
    bridge = PyMAVLinkBridge(connection=_FakeConnection(), platform_id="uav_a")
    tm = bridge.telemetry
    assert tm.platform_id == "uav_a"
    assert tm.connected is True
    assert tm.pose.frame == "WGS84"


# ---------------------------------------------------------------------------
# Waypoint dispatch — the critical lat/lon swap
# ---------------------------------------------------------------------------


def test_send_waypoint_swaps_lat_lon_correctly():
    """triage4 GeoPose(x=lon, y=lat) → MAVLink (x=lat*1e7, y=lon*1e7)."""
    conn = _FakeConnection()
    bridge = PyMAVLinkBridge(connection=conn)

    # x = -122.0 (longitude, west), y = 37.0 (latitude, northern)
    bridge.send_waypoint(GeoPose(x=-122.0, y=37.0, z=50.0))

    assert len(conn.mav.waypoints) == 1
    wp = conn.mav.waypoints[0]
    # Field order in _FakeMav.mission_item_int_send:
    # ..., x, y, z → indices -3, -2, -1
    lat_e7, lon_e7, alt = wp[-3], wp[-2], wp[-1]
    assert lat_e7 == int(37.0 * 1e7)
    assert lon_e7 == int(-122.0 * 1e7)
    assert alt == 50.0


def test_send_waypoint_uses_default_frame_and_command_when_mav_absent():
    conn = _FakeConnection()
    bridge = PyMAVLinkBridge(connection=conn, mavlink_module=None)
    conn.mav = _FakeMav()  # no MAV_CMD_* constants on this mock
    bridge.send_waypoint(GeoPose(x=0.0, y=0.0, z=10.0))
    wp = conn.mav.waypoints[0]
    # Frame index (after target_sys, target_comp, seq) should be
    # MAV_FRAME_GLOBAL_RELATIVE_ALT_INT == 3.
    assert wp[3] == 3
    # Command should be MAV_CMD_NAV_WAYPOINT == 16.
    assert wp[4] == 16


# ---------------------------------------------------------------------------
# publish_* emits STATUSTEXT
# ---------------------------------------------------------------------------


def test_publish_casualty_emits_statustext():
    conn = _FakeConnection()
    bridge = PyMAVLinkBridge(connection=conn)
    node = CasualtyNode(
        id="C1",
        location=GeoPose(x=1.0, y=2.0),
        platform_source="test",
        confidence=0.9,
        status="assessed",
        triage_priority="immediate",
    )
    bridge.publish_casualty(node)
    assert len(conn.mav.statustexts) >= 1
    severity, blob = conn.mav.statustexts[0]
    decoded = blob.decode("utf-8")
    assert decoded.startswith("triage4:")
    assert severity == 6  # MAV_SEVERITY_INFO


def test_publish_handoff_emits_statustext_with_prefix():
    conn = _FakeConnection()
    bridge = PyMAVLinkBridge(connection=conn)
    bridge.publish_handoff({"casualty_id": "C1", "medic": "m1", "priority": "immediate"})
    assert any(
        b"triage4:h:" in blob for _, blob in conn.mav.statustexts
    )


def test_publish_long_payload_is_chunked():
    conn = _FakeConnection()
    bridge = PyMAVLinkBridge(connection=conn)
    long_node = CasualtyNode(
        id="C" * 40,  # force a long JSON
        location=GeoPose(x=1.0, y=2.0),
        platform_source="test" * 10,
        confidence=0.9,
        status="assessed",
        triage_priority="immediate",
    )
    bridge.publish_casualty(long_node)
    # Every chunk must be <= 48 bytes (the _STATUSTEXT_CHUNK constant).
    assert len(conn.mav.statustexts) >= 2
    for _, blob in conn.mav.statustexts:
        assert len(blob) <= 48


# ---------------------------------------------------------------------------
# Telemetry ingest
# ---------------------------------------------------------------------------


def test_poll_telemetry_updates_pose_from_global_position_int():
    gpi = _FakeMAVMessage("GLOBAL_POSITION_INT", {
        "lon": int(-122.084 * 1e7),
        "lat": int(37.422 * 1e7),
        "alt": 50_000,  # 50 m in mm
        "hdg": 9000,    # 90.00 deg in 1/100 deg
    })
    conn = _FakeConnection(inbound_messages=[gpi])
    bridge = PyMAVLinkBridge(connection=conn)
    processed = bridge.poll_telemetry(timeout_s=0.0)
    assert processed == 1
    assert bridge.telemetry.pose.x == pytest.approx(-122.084, abs=1e-4)
    assert bridge.telemetry.pose.y == pytest.approx(37.422, abs=1e-4)
    assert bridge.telemetry.pose.z == pytest.approx(50.0, abs=1e-3)
    assert bridge.telemetry.pose.yaw == pytest.approx(90.0, abs=1e-2)


def test_poll_telemetry_updates_battery_from_sys_status():
    sys_status = _FakeMAVMessage("SYS_STATUS", {"battery_remaining": 72})
    conn = _FakeConnection(inbound_messages=[sys_status])
    bridge = PyMAVLinkBridge(connection=conn)
    bridge.poll_telemetry(timeout_s=0.0)
    assert bridge.telemetry.battery_pct == 72.0


def test_poll_telemetry_refreshes_heartbeat_timestamp():
    hb = _FakeMAVMessage("HEARTBEAT", {})
    conn = _FakeConnection(inbound_messages=[hb])
    bridge = PyMAVLinkBridge(connection=conn)
    before = bridge.telemetry.last_update_ts
    bridge.poll_telemetry(timeout_s=0.0)
    assert bridge.telemetry.last_update_ts >= before
    assert bridge.telemetry.connected is True


def test_poll_telemetry_handles_no_messages():
    bridge = PyMAVLinkBridge(connection=_FakeConnection())
    assert bridge.poll_telemetry(timeout_s=0.0) == 0


def test_poll_telemetry_swallows_connection_errors():
    class _BrokenConn(_FakeConnection):
        def recv_match(self, **kw):
            raise RuntimeError("socket is dead")

    bridge = PyMAVLinkBridge(connection=_BrokenConn())
    assert bridge.poll_telemetry(timeout_s=0.0) == 0


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


def test_close_disconnects_and_calls_connection_close():
    conn = _FakeConnection()
    bridge = PyMAVLinkBridge(connection=conn)
    bridge.close()
    assert conn._close_called is True
    assert bridge.telemetry.connected is False


def test_close_is_idempotent():
    conn = _FakeConnection()
    bridge = PyMAVLinkBridge(connection=conn)
    bridge.close()
    bridge.close()
    assert bridge.telemetry.connected is False


def test_close_swallows_connection_close_errors():
    class _BrokenConn(_FakeConnection):
        def close(self):
            raise RuntimeError("already closed")
    bridge = PyMAVLinkBridge(connection=_BrokenConn())
    bridge.close()  # must not raise


def test_publish_accepts_mission_graph():
    conn = _FakeConnection()
    bridge = PyMAVLinkBridge(connection=conn)
    mg = MissionGraph()
    mg.assign_medic("m1", "C1")
    mg.mark_unresolved("sector-A")
    bridge.publish_mission_graph(mg)
    assert any(
        b"triage4:g:" in blob for _, blob in conn.mav.statustexts
    )


# ---------------------------------------------------------------------------
# Factory — BridgeUnavailable path still honoured
# ---------------------------------------------------------------------------


def test_build_pymavlink_bridge_raises_bridge_unavailable_without_sdk(monkeypatch):
    """With pymavlink not importable, the factory must raise
    BridgeUnavailable (not NotImplementedError, and not an
    ImportError that leaks into the caller)."""
    import builtins
    real_import = builtins.__import__

    def _blocker(name, *args, **kwargs):
        if name == "pymavlink" or name.startswith("pymavlink."):
            raise ImportError("simulated: pymavlink not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocker)

    from triage4.integrations.platform_bridge import BridgeUnavailable
    from triage4.integrations.mavlink_bridge import build_pymavlink_bridge
    with pytest.raises(BridgeUnavailable):
        build_pymavlink_bridge()
