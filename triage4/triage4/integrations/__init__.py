"""Adapters and platform bridges.

Two sets of integrations:

- **Upstream-project adapters** (``meta2_adapter``, ``infom_adapter``,
  ``in4n_adapter``) — keep triage4 compatible with the three sibling
  repositories described in ``third_party/ATTRIBUTION.md``.

- **Platform bridges** (Phase 8): unified ``PlatformBridge`` contract
  with one Loopback simulator per platform. Real ROS2 / MAVLink /
  bosdyn backends are provided as skeletons behind optional imports.
"""

from .meta2_adapter import Meta2SignatureAdapter
from .infom_adapter import InfoMGraphAdapter
from .in4n_adapter import In4nSceneAdapter
from .platform_bridge import BridgeUnavailable, PlatformBridge, PlatformTelemetry
from .bridge_health import (
    BridgeHealth,
    check_bridge_health,
    check_telemetry,
    safe_to_dispatch,
)
from .multi_platform import (
    DispatchResult,
    MultiPlatformManager,
    NoHealthyPlatform,
    PlatformNotFound,
)
from .websocket_bridge import LoopbackWebSocketBridge, build_fastapi_websocket_bridge
from .mavlink_bridge import LoopbackMAVLinkBridge, build_pymavlink_bridge
from .ros2_bridge import LoopbackROS2Bridge, build_rclpy_bridge
from .spot_bridge import LoopbackSpotBridge, build_bosdyn_bridge
from .tello_bridge import LoopbackTelloBridge, TelloBridge, build_tello_bridge
from .physionet_adapter import (
    PhysioNetRecord,
    PhysioNetUnavailable,
    load_dict,
    load_wfdb,
)
from .marker_codec import (
    InvalidMarker,
    MarkerPayload,
    decode_marker,
    encode_marker,
    from_qr_string,
    marker_to_node,
    to_qr_string,
)

__all__ = [
    "BridgeHealth",
    "BridgeUnavailable",
    "DispatchResult",
    "InfoMGraphAdapter",
    "In4nSceneAdapter",
    "InvalidMarker",
    "LoopbackMAVLinkBridge",
    "LoopbackROS2Bridge",
    "LoopbackSpotBridge",
    "LoopbackTelloBridge",
    "LoopbackWebSocketBridge",
    "MarkerPayload",
    "Meta2SignatureAdapter",
    "MultiPlatformManager",
    "NoHealthyPlatform",
    "PhysioNetRecord",
    "PhysioNetUnavailable",
    "PlatformBridge",
    "PlatformNotFound",
    "PlatformTelemetry",
    "TelloBridge",
    "build_bosdyn_bridge",
    "build_fastapi_websocket_bridge",
    "build_pymavlink_bridge",
    "build_rclpy_bridge",
    "build_tello_bridge",
    "check_bridge_health",
    "check_telemetry",
    "decode_marker",
    "encode_marker",
    "from_qr_string",
    "load_dict",
    "load_wfdb",
    "marker_to_node",
    "safe_to_dispatch",
    "to_qr_string",
]
