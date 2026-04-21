"""Platform-bridge base contract.

triage4 talks to robotic platforms through a thin, unified contract so
the rest of the code does not care whether the backend is ROS2, MAVLink,
a Spot-class quadruped, or an in-memory simulator used in tests.

Every concrete bridge (``ros2_bridge``, ``mavlink_bridge``,
``spot_bridge``, ``websocket_bridge``) exposes:

- a ``publish_*`` side for outbound updates (casualty assessments,
  mission-graph snapshots, medic handoff payloads);
- a ``telemetry`` snapshot property for inbound platform state;
- a ``send_waypoint`` action for requesting the platform to move;
- a ``close`` lifecycle method.

Each module ships with a ``Loopback*`` implementation that runs entirely
in-process (no external SDK required), so the default install of triage4
remains lightweight and every bridge is unit-testable. Real backends are
provided as skeletons gated behind lazy imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from triage4.core.models import CasualtyNode, GeoPose
from triage4.graph.mission_graph import MissionGraph


@dataclass
class PlatformTelemetry:
    """Latest-known state of the platform the bridge is bound to."""

    platform_id: str
    pose: GeoPose = field(default_factory=lambda: GeoPose(0.0, 0.0))
    battery_pct: float = 100.0
    connected: bool = False
    last_update_ts: float = 0.0
    extra: dict = field(default_factory=dict)


@runtime_checkable
class PlatformBridge(Protocol):
    """Unified interface triage4 uses to talk to a robotic platform."""

    @property
    def platform_id(self) -> str: ...

    @property
    def telemetry(self) -> PlatformTelemetry: ...

    def publish_casualty(self, node: CasualtyNode) -> None: ...

    def publish_mission_graph(self, graph: MissionGraph) -> None: ...

    def publish_handoff(self, payload: dict) -> None: ...

    def send_waypoint(self, pose: GeoPose) -> None: ...

    def close(self) -> None: ...


class BridgeUnavailable(RuntimeError):
    """Raised by real-backend factories when the external SDK is missing."""
