"""Real pymavlink-backed ``PlatformBridge`` implementation.

Separate from ``LoopbackMAVLinkBridge`` so the loopback path (the
default for everyone who does ``pip install triage4``) has zero
pymavlink surface.

This file does NOT import ``pymavlink`` at module load. The real
connection is constructed by ``build_pymavlink_bridge`` in
``mavlink_bridge.py``, which lazy-imports the SDK and hands a
ready-made connection into ``PyMAVLinkBridge.__init__``. That
separation lets us unit-test the bridge logic with a mock
connection without ever needing the real SDK in CI.

Responsibilities:
- convert ``GeoPose`` ↔ MAVLink ``MISSION_ITEM_INT`` (the lat/lon
  swap is the single most common integration footgun — tagged
  RISK_REGISTER ``BRIDGE-003``);
- drain the inbound message queue via ``poll_telemetry(timeout)``
  or a background thread started with ``start_telemetry_thread()``;
- emit ``publish_*`` over MAVLink ``STATUSTEXT`` with a
  ``triage4:`` prefix so ground-control stations can surface the
  events without schema changes.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict

from triage4.core.models import CasualtyNode, GeoPose
from triage4.graph.mission_graph import MissionGraph
from triage4.integrations.platform_bridge import PlatformTelemetry


# MAVLink STATUSTEXT has a 50-byte text limit per message. We
# segment longer triage4 payloads so nothing is silently dropped.
_STATUSTEXT_CHUNK = 48  # leave two bytes for the "triage4:" prefix sigil

# Severity — MAV_SEVERITY_INFO = 6 is a reasonable default for triage
# events that are not autopilot failures.
_MAV_SEVERITY_INFO = 6


class PyMAVLinkBridge:
    """Satisfies ``PlatformBridge`` against a live MAVLink autopilot.

    Expects a pre-configured connection object shaped like the return
    value of ``pymavlink.mavutil.mavlink_connection``. In practice the
    ``build_pymavlink_bridge`` factory creates that connection; tests
    inject a mock with the same surface.
    """

    def __init__(
        self,
        connection,
        platform_id: str = "uav",
        *,
        mavlink_module=None,
    ) -> None:
        if connection is None:
            raise ValueError("connection must not be None")
        self._conn = connection
        self._platform_id = str(platform_id)
        # The caller can inject the ``mavutil.mavlink`` module for
        # frame/command constants — or we try to fish it off the
        # connection at runtime. Explicit injection keeps tests
        # hermetic.
        self._mav = mavlink_module

        self._telemetry = PlatformTelemetry(
            platform_id=self._platform_id,
            pose=GeoPose(0.0, 0.0, 0.0, 0.0, frame="WGS84"),
            battery_pct=100.0,
            connected=True,
            last_update_ts=time.time(),
        )
        self._closed = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    # -- PlatformBridge surface -----------------------------------------

    @property
    def platform_id(self) -> str:
        return self._platform_id

    @property
    def telemetry(self) -> PlatformTelemetry:
        return self._telemetry

    def publish_casualty(self, node: CasualtyNode) -> None:
        payload = {
            "id": node.id,
            "priority": node.triage_priority,
            "confidence": round(float(node.confidence), 3),
            "x": round(float(node.location.x), 4),
            "y": round(float(node.location.y), 4),
        }
        self._send_statustext(f"c:{json.dumps(payload, separators=(',', ':'))}")

    def publish_mission_graph(self, graph: MissionGraph) -> None:
        payload = {
            "assigned_medics": len(graph.medic_assignments),
            "unresolved": len(graph.unresolved_regions),
            "revisits": len(graph.revisit_queue),
        }
        self._send_statustext(f"g:{json.dumps(payload, separators=(',', ':'))}")

    def publish_handoff(self, payload: dict) -> None:
        compact = {
            k: payload[k]
            for k in ("casualty_id", "medic", "priority")
            if k in payload
        }
        self._send_statustext(f"h:{json.dumps(compact, separators=(',', ':'))}")

    def send_waypoint(self, pose: GeoPose) -> None:
        """Emit a single ``MISSION_ITEM_INT`` for the given pose.

        Coordinate-frame contract:
          - triage4 ``GeoPose(x=longitude, y=latitude, z=altitude_m)``
          - MAVLink ``(x=latitude*1e7, y=longitude*1e7, z=altitude_m)``

        The x/y swap below is the single point of truth. Any future
        change to ``GeoPose`` semantics MUST update this block.
        """
        mav = self._resolve_mav_module()
        frame = getattr(mav, "MAV_FRAME_GLOBAL_RELATIVE_ALT_INT", 3)
        cmd = getattr(mav, "MAV_CMD_NAV_WAYPOINT", 16)

        target_system = getattr(self._conn, "target_system", 1)
        target_component = getattr(self._conn, "target_component", 1)

        self._conn.mav.mission_item_int_send(
            target_system,
            target_component,
            0,                   # seq
            frame,
            cmd,
            2,                   # current — 2 = "guided mode" waypoint
            1,                   # autocontinue
            0.0, 0.0, 0.0, 0.0,  # param1..param4 (hold / radius / pass / yaw)
            int(float(pose.y) * 1e7),   # lat * 1e7
            int(float(pose.x) * 1e7),   # lon * 1e7
            float(pose.z),
        )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        try:
            self._conn.close()
        except Exception:
            # Best-effort — connections in weird states shouldn't
            # leak an exception out of close().
            pass
        self._telemetry.connected = False

    # -- telemetry loop --------------------------------------------------

    def poll_telemetry(self, timeout_s: float = 0.1) -> int:
        """Drain pending inbound messages; return count processed.

        Called manually (from the event loop or a test) or via the
        background thread that ``start_telemetry_thread`` launches.
        Never raises — a malformed message is logged as a connection
        hiccup and discarded.
        """
        processed = 0
        try:
            msg = self._conn.recv_match(
                type=["GLOBAL_POSITION_INT", "SYS_STATUS", "HEARTBEAT"],
                blocking=True,
                timeout=max(0.0, float(timeout_s)),
            )
        except Exception:
            return 0

        while msg is not None:
            self._ingest(msg)
            processed += 1
            try:
                msg = self._conn.recv_match(
                    type=["GLOBAL_POSITION_INT", "SYS_STATUS", "HEARTBEAT"],
                    blocking=False,
                )
            except Exception:
                break
        return processed

    def start_telemetry_thread(self, tick_s: float = 0.1) -> None:
        """Launch a background thread that polls telemetry continuously."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()

        def _loop() -> None:
            while not self._stop_event.is_set() and not self._closed:
                try:
                    self.poll_telemetry(timeout_s=tick_s)
                except Exception:
                    time.sleep(tick_s)

        self._thread = threading.Thread(target=_loop, daemon=True, name="pymavlink_rx")
        self._thread.start()

    # -- internals -------------------------------------------------------

    def _ingest(self, msg) -> None:
        mtype = msg.get_type() if hasattr(msg, "get_type") else None
        if mtype == "GLOBAL_POSITION_INT":
            self._telemetry.pose = GeoPose(
                x=float(getattr(msg, "lon", 0)) * 1e-7,
                y=float(getattr(msg, "lat", 0)) * 1e-7,
                z=float(getattr(msg, "alt", 0)) * 1e-3,
                yaw=float(getattr(msg, "hdg", 0)) * 0.01,
                frame="WGS84",
            )
            self._telemetry.last_update_ts = time.time()
        elif mtype == "SYS_STATUS":
            remaining = getattr(msg, "battery_remaining", None)
            if remaining is not None and remaining >= 0:
                self._telemetry.battery_pct = float(remaining)
            self._telemetry.last_update_ts = time.time()
        elif mtype == "HEARTBEAT":
            self._telemetry.connected = True
            self._telemetry.last_update_ts = time.time()

    def _send_statustext(self, text: str) -> None:
        severity = _MAV_SEVERITY_INFO
        # MAVLink 2 allows 50-byte payloads; chunk longer strings.
        full = f"triage4:{text}"
        for i in range(0, len(full), _STATUSTEXT_CHUNK):
            chunk = full[i : i + _STATUSTEXT_CHUNK]
            try:
                self._conn.mav.statustext_send(
                    severity,
                    chunk.encode("utf-8"),
                )
            except Exception:
                # Non-fatal — publishing is best-effort.
                return

    def _resolve_mav_module(self):
        """Return the ``mavutil.mavlink`` module, injecting it if needed."""
        if self._mav is not None:
            return self._mav
        # Fish it off the connection's mav attribute when possible.
        mav_attr = getattr(self._conn, "mav", None)
        if mav_attr is not None:
            return mav_attr
        return _ConstantsFallback


class _ConstantsFallback:
    """Minimal constants that match MAVLink v2 numeric enums.

    Used only when neither the caller nor the connection provides the
    real ``mavutil.mavlink`` module. Keeps ``send_waypoint`` working
    in tests / mocks without ever importing pymavlink.
    """

    MAV_FRAME_GLOBAL_RELATIVE_ALT_INT = 3
    MAV_CMD_NAV_WAYPOINT = 16


def _snapshot_bridge(bridge: PyMAVLinkBridge) -> dict:
    """Testing helper — current telemetry in a stable dict shape."""
    return {
        "platform_id": bridge.platform_id,
        "telemetry": asdict(bridge.telemetry),
    }
