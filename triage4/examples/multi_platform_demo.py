"""triage4 — multi-platform coordination demo.

Shows the ``MultiPlatformManager`` running three heterogeneous
bridges behind one surface: a UAV (MAVLink loopback), a quadruped
(Spot loopback), and a ROS2 companion. The manager:

- broadcasts a new casualty to all three bridges;
- targets a mission-graph update only at the ROS2 publisher;
- picks the healthiest platform for a waypoint (by battery);
- refuses dispatch when the chosen platform is disconnected or
  telemetry goes stale.

Run from the project root:

    python examples/multi_platform_demo.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from triage4.core.models import CasualtyNode, GeoPose, TraumaHypothesis  # noqa: E402
from triage4.graph.mission_graph import MissionGraph  # noqa: E402
from triage4.integrations import (  # noqa: E402
    LoopbackMAVLinkBridge,
    LoopbackROS2Bridge,
    LoopbackSpotBridge,
    MultiPlatformManager,
    NoHealthyPlatform,
)


def _hr() -> None:
    print("-" * 70)


def main() -> None:
    # Three bridges — UAV, quadruped, companion-computer.
    uav = LoopbackMAVLinkBridge(platform_id="uav_alpha")
    uav._telemetry.battery_pct = 82.0

    spot = LoopbackSpotBridge(platform_id="spot_bravo")
    spot._telemetry.battery_pct = 55.0

    ros = LoopbackROS2Bridge(platform_id="companion")

    manager = MultiPlatformManager([uav, spot, ros])
    print(f"registered platforms: {manager.platform_ids}")

    # 1. Broadcast a casualty assessment to every platform.
    _hr()
    print("[1] broadcast a new casualty to all three bridges")
    casualty = CasualtyNode(
        id="C42",
        location=GeoPose(x=12.0, y=5.0),
        platform_source="uav_alpha",
        confidence=0.84,
        status="assessed",
        hypotheses=[TraumaHypothesis(kind="hemorrhage_major", score=0.9)],
        triage_priority="immediate",
    )
    manager.publish_casualty(casualty)
    print(f"   uav.published            = {len(uav.published)} msgs")
    print(f"   spot.events              = {len(spot.events)} msgs")
    print(f"   ros.published_on('casualty') = {len(ros.published_on('casualty'))} msgs")

    # 2. Target just the ROS2 companion with a mission-graph update.
    _hr()
    print("[2] target only the ROS2 companion with a mission-graph update")
    mg = MissionGraph()
    mg.assign_medic("m1", "C42")
    manager.publish_mission_graph(mg, platform_id="companion")
    print(f"   uav.published (unchanged) = {len(uav.published)} msgs")
    print(f"   ros mission_graph msgs    = {len(ros.published_on('mission_graph'))}")

    # 3. Health snapshot.
    _hr()
    print("[3] per-platform health snapshot")
    for pid, h in manager.health().items():
        print(
            f"   {pid:12s}  ok={h.ok}  battery={h.battery_pct:5.1f}%  "
            f"age={h.age_s:.2f}s  reasons={h.reasons or 'none'}"
        )

    # 4. Auto-pick the healthiest platform for a waypoint.
    _hr()
    print("[4] auto-pick a waypoint target (highest battery wins)")
    result = manager.send_waypoint(GeoPose(x=25.0, y=25.0))
    print(f"   dispatched to: {result.platform_id} (accepted={result.accepted})")

    # 5. Simulate the chosen platform going stale, then try again.
    _hr()
    print("[5] make uav_alpha telemetry stale and retry")
    uav._telemetry.last_update_ts = time.time() - 60.0
    result = manager.send_waypoint(GeoPose(x=30.0, y=30.0), platform_id="uav_alpha")
    print(f"   accepted={result.accepted}  reasons={result.reasons}")

    # 6. Close every bridge and see what happens when nothing is healthy.
    _hr()
    print("[6] close all bridges — expect NoHealthyPlatform")
    manager.close()
    try:
        manager.send_waypoint(GeoPose(x=0.0, y=0.0))
    except NoHealthyPlatform as exc:
        print(f"   correctly refused: {exc}")

    _hr()
    print("✓ multi-platform coordination works end-to-end in loopback mode.")


if __name__ == "__main__":
    main()
