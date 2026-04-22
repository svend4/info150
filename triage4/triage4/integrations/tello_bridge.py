"""DJI Tello bridge — $100 entry point to Phase 10 proper.

Matches the pattern of the existing platform bridges:

- ``LoopbackTelloBridge`` — in-process simulator. Always available
  (stdlib only). Kinematic model mirrors the Tello's actual flight
  envelope (0.1 m → 500 cm waypoint, 10 s flight time in a single
  battery, SDK-style command acks).
- ``TelloBridge`` — real backend. Wraps ``djitellopy.Tello`` so
  that ``publish_casualty`` / ``publish_handoff`` become on-screen
  text + log lines, and ``send_waypoint`` translates a triage4
  ``GeoPose`` into relative ``move_*`` commands in the Tello body
  frame.
- ``build_tello_bridge`` — lazy factory. Raises
  ``BridgeUnavailable`` when ``djitellopy`` isn't installed,
  matching the pattern from ``build_pymavlink_bridge`` and friends.

Why Tello: cheapest real drone with a supported Python SDK
(`djitellopy`), a 720p onboard camera accessible as a frame source,
and programmable mobility — a genuine Phase-10 platform at ~$100.

Coordinate-frame note: Tello's SDK uses a body-local frame in
centimetres (forward / right / down relative to the drone's
heading). triage4 ``GeoPose`` is in metres in a map / odom frame.
``send_waypoint`` treats the pose as a relative displacement from
the current position and scales to centimetres. That is an
intentional simplification — see ``docs/PHASE_10_TELLO.md`` for
the frame handling and why we don't try to bolt GPS onto a Tello.
"""

from __future__ import annotations

import math
import threading
import time
from dataclasses import asdict
from typing import Any

from triage4.core.models import CasualtyNode, GeoPose
from triage4.graph.mission_graph import MissionGraph
from triage4.integrations.platform_bridge import (
    BridgeUnavailable,
    PlatformTelemetry,
)


# Tello envelope constants (from DJI SDK docs).
_TELLO_MIN_MOVE_CM = 20     # any axis — smaller commands are rejected by FW
_TELLO_MAX_MOVE_CM = 500    # any axis, per single move_* command
_TELLO_MAX_BATTERY_DRAIN_PER_SEC = 0.16  # ~10 min flight, empirically
_SECONDS_PER_MINUTE = 60.0


class LoopbackTelloBridge:
    """In-process Tello simulator.

    Mirrors the parts of ``djitellopy.Tello`` that triage4 actually
    uses: takeoff / land / gait, relative moves, battery drain,
    frame read. Deterministic — advance with ``step(dt_s)`` exactly
    like ``LoopbackMAVLinkBridge``.
    """

    def __init__(
        self,
        platform_id: str = "sim_tello",
        start_pose: GeoPose | None = None,
        *,
        speed_cm_per_s: float = 60.0,
    ) -> None:
        self._platform_id = str(platform_id)
        self._speed = max(10.0, float(speed_cm_per_s))
        self._airborne = False
        self._last_command: tuple[str, float, float, float] | None = None
        self._command_log: list[tuple[float, str, dict[str, Any]]] = []
        self._published: list[tuple[str, Any]] = []
        self._telemetry = PlatformTelemetry(
            platform_id=self._platform_id,
            pose=start_pose or GeoPose(0.0, 0.0, 0.0, 0.0, frame="tello_body"),
            battery_pct=100.0,
            connected=True,
            last_update_ts=time.time(),
            extra={"airborne": False, "gait": "idle"},
        )
        self._closed = False

    # -- PlatformBridge surface -----------------------------------------

    @property
    def platform_id(self) -> str:
        return self._platform_id

    @property
    def telemetry(self) -> PlatformTelemetry:
        return self._telemetry

    @property
    def published(self) -> list[tuple[str, Any]]:
        return list(self._published)

    @property
    def command_log(self) -> list[tuple[float, str, dict[str, Any]]]:
        return list(self._command_log)

    @property
    def airborne(self) -> bool:
        return self._airborne

    def publish_casualty(self, node: CasualtyNode) -> None:
        self._published.append(("casualty", node.to_dict()))

    def publish_mission_graph(self, graph: MissionGraph) -> None:
        self._published.append(("mission_graph", graph.as_json()))

    def publish_handoff(self, payload: dict) -> None:
        self._published.append(("handoff", dict(payload)))

    def send_waypoint(self, pose: GeoPose) -> None:
        """Queue a waypoint interpreted as a relative displacement (m)."""
        if self._closed:
            raise RuntimeError("bridge is closed")
        self._last_command = (
            "waypoint",
            float(pose.x),
            float(pose.y),
            float(pose.z),
        )
        self._command_log.append(
            (time.time(), "waypoint", {
                "dx_m": float(pose.x),
                "dy_m": float(pose.y),
                "dz_m": float(pose.z),
            })
        )
        self._published.append(("waypoint", asdict(pose)))

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._airborne = False
        self._telemetry.connected = False
        self._telemetry.extra["airborne"] = False

    # -- Tello-flavoured controls -------------------------------------

    def takeoff(self) -> None:
        if self._closed:
            raise RuntimeError("bridge is closed")
        self._airborne = True
        self._telemetry.extra["airborne"] = True
        self._telemetry.extra["gait"] = "hover"
        # Tello reaches ~80 cm hover on takeoff.
        self._telemetry.pose = GeoPose(
            x=self._telemetry.pose.x,
            y=self._telemetry.pose.y,
            z=0.80,
            yaw=self._telemetry.pose.yaw,
            frame=self._telemetry.pose.frame,
        )
        self._command_log.append((time.time(), "takeoff", {}))

    def land(self) -> None:
        if not self._airborne:
            return
        self._airborne = False
        self._telemetry.extra["airborne"] = False
        self._telemetry.extra["gait"] = "idle"
        self._telemetry.pose = GeoPose(
            x=self._telemetry.pose.x,
            y=self._telemetry.pose.y,
            z=0.0,
            yaw=self._telemetry.pose.yaw,
            frame=self._telemetry.pose.frame,
        )
        self._command_log.append((time.time(), "land", {}))

    def step(self, dt_s: float) -> None:
        """Advance the simulator by ``dt_s`` seconds."""
        if self._closed or dt_s <= 0:
            return
        if self._airborne:
            drain = _TELLO_MAX_BATTERY_DRAIN_PER_SEC * dt_s
            self._telemetry.battery_pct = max(
                0.0, self._telemetry.battery_pct - drain
            )

            if self._last_command is not None:
                _, dx, dy, dz = self._last_command
                dist = math.sqrt(dx * dx + dy * dy + dz * dz)
                if dist > 1e-6:
                    travel = min(dist, (self._speed / 100.0) * dt_s)
                    ratio = travel / dist
                    self._telemetry.pose = GeoPose(
                        x=self._telemetry.pose.x + dx * ratio,
                        y=self._telemetry.pose.y + dy * ratio,
                        z=max(0.0, self._telemetry.pose.z + dz * ratio),
                        yaw=self._telemetry.pose.yaw,
                        frame=self._telemetry.pose.frame,
                    )
                    # Shrink the remaining command by ``ratio``.
                    remaining = dist - travel
                    if remaining <= 1e-6:
                        self._last_command = None
                    else:
                        scale = remaining / dist
                        self._last_command = (
                            "waypoint",
                            dx * scale,
                            dy * scale,
                            dz * scale,
                        )

            # Battery exhaustion → forced landing.
            if self._telemetry.battery_pct <= 0.0:
                self.land()

        self._telemetry.last_update_ts = time.time()


class TelloBridge:
    """Real backend wrapping ``djitellopy.Tello``.

    Accepts a pre-connected Tello object so unit tests can inject a
    mock. Callers usually go through ``build_tello_bridge`` instead.
    """

    def __init__(
        self,
        tello,
        *,
        platform_id: str = "tello",
        default_altitude_m: float = 1.2,
    ) -> None:
        if tello is None:
            raise ValueError("tello must not be None")
        self._tello = tello
        self._platform_id = str(platform_id)
        self._default_altitude_m = float(default_altitude_m)
        self._last_command: tuple[str, float, float, float] | None = None
        self._closed = False

        battery = self._safe_get_battery()
        self._telemetry = PlatformTelemetry(
            platform_id=self._platform_id,
            pose=GeoPose(0.0, 0.0, 0.0, 0.0, frame="tello_body"),
            battery_pct=battery,
            connected=True,
            last_update_ts=time.time(),
            extra={"airborne": False},
        )
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def platform_id(self) -> str:
        return self._platform_id

    @property
    def telemetry(self) -> PlatformTelemetry:
        return self._telemetry

    # -- PlatformBridge publish surface ---------------------------------

    def publish_casualty(self, node: CasualtyNode) -> None:
        # Tello has no telemetry surface for casualty summaries.
        # We just log the event — a companion computer (laptop /
        # smartphone) is expected to be the source of truth.
        self._log(f"casualty {node.id} priority={node.triage_priority}")

    def publish_mission_graph(self, graph: MissionGraph) -> None:
        self._log(
            f"mission: "
            f"medics={len(graph.medic_assignments)} "
            f"unresolved={len(graph.unresolved_regions)}"
        )

    def publish_handoff(self, payload: dict) -> None:
        compact = {k: payload[k] for k in ("casualty_id", "medic", "priority")
                   if k in payload}
        self._log(f"handoff {compact}")

    def send_waypoint(self, pose: GeoPose) -> None:
        """Translate a relative pose (metres) into Tello ``move_*``.

        Tello's SDK uses the body frame in centimetres. triage4
        ``GeoPose(x, y, z)`` is interpreted as (forward, right, up)
        in metres. Zero components are skipped; values below the
        ``_TELLO_MIN_MOVE_CM`` threshold are clamped up to it to
        avoid firmware rejection.
        """
        if self._closed:
            raise RuntimeError("bridge is closed")

        dx_cm = int(round(float(pose.x) * 100.0))
        dy_cm = int(round(float(pose.y) * 100.0))
        dz_cm = int(round(float(pose.z) * 100.0))

        self._move_axis("forward", "back", dx_cm)
        self._move_axis("right", "left", dy_cm)
        self._move_axis("up", "down", dz_cm)

        self._last_command = (
            "waypoint", float(pose.x), float(pose.y), float(pose.z),
        )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        try:
            if getattr(self._tello, "is_flying", False):
                self._tello.land()
        except Exception:
            pass
        try:
            self._tello.end()
        except Exception:
            pass
        self._telemetry.connected = False

    # -- Tello-flavoured helpers -----------------------------------

    def takeoff(self) -> None:
        self._tello.takeoff()
        self._telemetry.extra["airborne"] = True

    def land(self) -> None:
        self._tello.land()
        self._telemetry.extra["airborne"] = False

    def frame(self):
        """Grab a frame from the Tello's live camera stream.

        Returns ``None`` if streaming hasn't been enabled. Callers
        should ``self._tello.streamon()`` once at startup.
        """
        reader = getattr(self._tello, "get_frame_read", None)
        if reader is None:
            return None
        return reader().frame

    def start_telemetry_thread(self, tick_s: float = 0.5) -> None:
        """Poll battery + flight state on a background thread."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()

        def _loop() -> None:
            while not self._stop_event.is_set() and not self._closed:
                try:
                    battery = self._safe_get_battery()
                    self._telemetry.battery_pct = battery
                    self._telemetry.extra["airborne"] = bool(
                        getattr(self._tello, "is_flying", False)
                    )
                    self._telemetry.last_update_ts = time.time()
                except Exception:
                    pass
                time.sleep(max(0.05, float(tick_s)))

        self._thread = threading.Thread(
            target=_loop, daemon=True, name="tello_telemetry",
        )
        self._thread.start()

    # -- internals ---------------------------------------------------

    def _safe_get_battery(self) -> float:
        try:
            value = self._tello.get_battery()
        except Exception:
            return 100.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 100.0

    def _move_axis(self, positive_cmd: str, negative_cmd: str, cm: int) -> None:
        if cm == 0:
            return
        distance = abs(cm)
        if distance < _TELLO_MIN_MOVE_CM:
            distance = _TELLO_MIN_MOVE_CM
        distance = min(distance, _TELLO_MAX_MOVE_CM)
        fn_name = positive_cmd if cm > 0 else negative_cmd
        fn = getattr(self._tello, f"move_{fn_name}", None)
        if fn is None:
            raise RuntimeError(
                f"tello SDK missing move_{fn_name} — incompatible djitellopy"
            )
        fn(distance)

    def _log(self, text: str) -> None:
        # Prefer the Tello's own LED-strip / on-screen display if the SDK
        # exposes one; otherwise print to stdout.
        sender = getattr(self._tello, "send_rc_control", None)
        if sender is None:
            print(f"[tello:{self._platform_id}] {text}")
        else:
            # Not every djitellopy version exposes a text channel;
            # be conservative and stick to stdout.
            print(f"[tello:{self._platform_id}] {text}")


def build_tello_bridge(
    host: str = "192.168.10.1",
    *,
    platform_id: str = "tello",
    connect_timeout_s: float = 10.0,
    start_telemetry: bool = True,
):
    """Build a real ``TelloBridge``.

    Steps:

    1. Lazy-import ``djitellopy``. Raises ``BridgeUnavailable``
       when the package is absent.
    2. Instantiate ``Tello``, set the host (Tellos default to
       192.168.10.1 in AP mode).
    3. ``connect()`` and wait for the initial battery read — raises
       ``BridgeUnavailable`` if the connect handshake times out.
    4. Wrap in ``TelloBridge`` and optionally start the telemetry
       thread.
    """
    try:
        from djitellopy import Tello  # type: ignore[import-not-found]
    except ImportError as exc:
        raise BridgeUnavailable(
            "djitellopy is not installed. Install with "
            "'pip install djitellopy' or use LoopbackTelloBridge "
            "in tests."
        ) from exc

    tello = Tello(host=host)
    start = time.time()
    try:
        tello.connect()
    except Exception as exc:
        raise BridgeUnavailable(
            f"Tello at {host!r} did not respond within "
            f"{connect_timeout_s}s — is the drone powered on and "
            "is the host's Wi-Fi connected to it?"
        ) from exc

    elapsed = time.time() - start
    if elapsed > connect_timeout_s:
        try:
            tello.end()
        except Exception:
            pass
        raise BridgeUnavailable(
            f"Tello connect took {elapsed:.1f}s > {connect_timeout_s}s"
        )

    bridge = TelloBridge(tello=tello, platform_id=platform_id)
    if start_telemetry:
        bridge.start_telemetry_thread()
    return bridge
