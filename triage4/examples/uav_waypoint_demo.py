"""triage4 — UAV waypoint simulator demo.

Drives a ``LoopbackMAVLinkBridge`` to three casualty waypoints in a
deterministic synthetic scenario and prints step-by-step telemetry.

Run from the project root:

    python examples/uav_waypoint_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from triage4.core.models import GeoPose  # noqa: E402
from triage4.integrations import LoopbackMAVLinkBridge  # noqa: E402


WAYPOINTS: list[tuple[str, GeoPose]] = [
    ("C1  (immediate)", GeoPose(x=20.0, y=15.0)),
    ("C4  (immediate)", GeoPose(x=20.0, y=60.0)),
    ("C7  (immediate)", GeoPose(x=85.0, y=45.0)),
]


def main() -> None:
    bridge = LoopbackMAVLinkBridge(
        platform_id="sim_uav_alpha",
        start_pose=GeoPose(x=0.0, y=0.0),
        speed=12.0,
        drain_per_metre=0.05,
    )

    print(f"platform: {bridge.platform_id}")
    print(f"start pose: ({bridge.telemetry.pose.x:.1f}, {bridge.telemetry.pose.y:.1f})  "
          f"battery: {bridge.telemetry.battery_pct:.1f}%")
    print()

    for label, wp in WAYPOINTS:
        print(f"→ sending waypoint {label} at ({wp.x:.1f}, {wp.y:.1f})")
        bridge.send_waypoint(wp)

        # Tick the simulator forward until the UAV is within 0.5 m of
        # the target or 30 s elapse (whichever comes first).
        t = 0.0
        while t < 30.0:
            bridge.step(dt_s=1.0)
            t += 1.0
            pose = bridge.telemetry.pose
            dx = pose.x - wp.x
            dy = pose.y - wp.y
            if (dx * dx + dy * dy) < 0.25:
                break

        pose = bridge.telemetry.pose
        print(f"   arrived at ({pose.x:.2f}, {pose.y:.2f})  "
              f"t = {t:.1f}s  battery = {bridge.telemetry.battery_pct:.1f}%")

    print()
    print("published messages (log):")
    for kind, _ in bridge.published:
        print(f"  - {kind}")

    bridge.close()


if __name__ == "__main__":
    main()
