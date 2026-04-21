"""WebSocket bridge — operator dashboard updates.

Part of Phase 8. Provides a streaming bridge between the triage4 backend
and the web dashboard. The default ``LoopbackWebSocketBridge`` keeps all
published payloads in an in-process deque so the same code path is
trivially testable.

A real FastAPI websocket backend is provided as a thin wrapper that
records each connected client and broadcasts each outbound payload.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import asdict
from typing import Any

from triage4.core.models import CasualtyNode, GeoPose
from triage4.graph.mission_graph import MissionGraph
from triage4.integrations.in4n_adapter import In4nSceneAdapter
from triage4.integrations.platform_bridge import PlatformTelemetry


class LoopbackWebSocketBridge:
    """In-process bridge — records everything in an internal deque."""

    def __init__(
        self, platform_id: str = "dashboard", max_history: int = 512
    ) -> None:
        self._platform_id = str(platform_id)
        self._history: deque[dict] = deque(maxlen=int(max_history))
        self._telemetry = PlatformTelemetry(
            platform_id=self._platform_id,
            connected=True,
            last_update_ts=time.time(),
        )
        self._scene_adapter = In4nSceneAdapter()
        self._closed = False

    @property
    def platform_id(self) -> str:
        return self._platform_id

    @property
    def telemetry(self) -> PlatformTelemetry:
        return self._telemetry

    @property
    def history(self) -> list[dict]:
        return list(self._history)

    def _emit(self, kind: str, payload: dict) -> None:
        if self._closed:
            raise RuntimeError("bridge is closed")
        self._history.append(
            {"kind": kind, "ts": time.time(), "payload": payload}
        )
        self._telemetry.last_update_ts = time.time()

    def publish_casualty(self, node: CasualtyNode) -> None:
        self._emit("casualty", node.to_dict())

    def publish_mission_graph(self, graph: MissionGraph) -> None:
        self._emit("mission_graph", graph.as_json())

    def publish_handoff(self, payload: dict) -> None:
        self._emit("handoff", dict(payload))

    def publish_scene(
        self, casualty_graph: Any, platforms: list[dict] | None = None
    ) -> None:
        """Dashboard-specific extra: broadcast a force-graph scene."""
        scene = self._scene_adapter.export_scene(casualty_graph, platforms=platforms)
        self._emit("scene", scene)

    def send_waypoint(self, pose: GeoPose) -> None:
        # A dashboard bridge does not drive a platform — record the intent
        # so the test harness can verify it was issued.
        self._emit("waypoint_request", asdict(pose))

    def close(self) -> None:
        self._closed = True
        self._telemetry.connected = False


def build_fastapi_websocket_bridge(*args, **kwargs):  # pragma: no cover
    """Skeleton real-backend factory using FastAPI websockets.

    The real implementation would keep a set of active ``WebSocket``
    connections and broadcast JSON-serialised payloads to each. Left as
    a skeleton here because instantiating live websocket connections
    requires an async FastAPI server context which is out of scope for
    the triage4 unit-test layer.
    """
    raise NotImplementedError(
        "Real FastAPI websocket backend is a skeleton. "
        "Wire up in the FastAPI app via @app.websocket(...) and forward "
        "to LoopbackWebSocketBridge-compatible publish_* methods."
    )
