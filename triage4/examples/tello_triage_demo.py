"""triage4 — Phase 10 Stage 3 Tello coordination demo.

Shows a single Tello-class drone flying a three-waypoint search
pattern while triage4 publishes casualty events and health-gates
dispatch. Uses ``LoopbackTelloBridge`` by default so the demo runs
anywhere (including CI). With ``--real`` the demo goes through
``build_tello_bridge`` to talk to a real Tello on the local Wi-Fi.

Flow:
  1. Build a ``LoopbackTelloBridge`` (or real Tello bridge).
  2. Register it with a ``MultiPlatformManager``.
  3. Loop three waypoints forming a small survey triangle.
  4. Simulate casualty sightings at each waypoint; publish them
     through the manager.
  5. Print per-step health report; refuse dispatch when battery
     drops too far.

Run from the project root:

    python examples/tello_triage_demo.py              # simulator
    python examples/tello_triage_demo.py --real       # real Tello on 192.168.10.1
    python examples/tello_triage_demo.py --real --host 192.168.10.1

See docs/PHASE_10_TELLO.md before running against a real drone.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from triage4.core.models import CasualtyNode, GeoPose, TraumaHypothesis  # noqa: E402
from triage4.integrations import (  # noqa: E402
    BridgeUnavailable,
    LoopbackTelloBridge,
    MultiPlatformManager,
    check_bridge_health,
    safe_to_dispatch,
)


_WAYPOINTS_M = [
    GeoPose(x=2.0, y=0.0, z=0.3),   # forward 2 m, up 30 cm
    GeoPose(x=0.0, y=2.0, z=0.0),   # right 2 m
    GeoPose(x=-2.0, y=-2.0, z=-0.3),  # back to origin, descend 30 cm
]


def _build_bridge(args: argparse.Namespace):
    if not args.real:
        print("[bridge] using LoopbackTelloBridge (simulator)")
        return LoopbackTelloBridge(platform_id=args.platform_id, speed_cm_per_s=80.0), "loopback"

    from triage4.integrations import build_tello_bridge
    print(f"[bridge] attempting real Tello on {args.host!r}")
    try:
        bridge = build_tello_bridge(host=args.host, platform_id=args.platform_id)
    except BridgeUnavailable as exc:
        print(f"[bridge] real Tello unreachable ({exc}); falling back to loopback")
        return LoopbackTelloBridge(platform_id=args.platform_id, speed_cm_per_s=80.0), "loopback"
    return bridge, "real"


def _hr() -> None:
    print("-" * 70)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--real", action="store_true", help="use real Tello backend")
    parser.add_argument("--host", default="192.168.10.1", help="real-Tello IP")
    parser.add_argument("--platform-id", default="tello_alpha")
    parser.add_argument("--steps", type=int, default=6, help="sim steps per waypoint")
    args = parser.parse_args(argv)

    bridge, kind = _build_bridge(args)
    manager = MultiPlatformManager([bridge])

    _hr()
    print(f"[start] bridge kind: {kind}  platform: {bridge.platform_id}")
    print(f"[start] waypoints   : {len(_WAYPOINTS_M)}")

    # Takeoff (loopback + real both support this).
    try:
        bridge.takeoff()
    except AttributeError:
        pass
    print(f"[start] airborne    : {bridge.telemetry.extra.get('airborne', '?')}")

    for wp_idx, wp in enumerate(_WAYPOINTS_M):
        _hr()
        print(f"[wp {wp_idx + 1}/{len(_WAYPOINTS_M)}] target dx_m={wp.x:+.2f}  "
              f"dy_m={wp.y:+.2f}  dz_m={wp.z:+.2f}")

        health = check_bridge_health(bridge)
        if not safe_to_dispatch(health):
            print(f"[wp {wp_idx + 1}] skipping — unhealthy: {health.reasons}")
            continue

        result = manager.send_waypoint(wp, platform_id=bridge.platform_id)
        print(f"[wp {wp_idx + 1}] dispatched accepted={result.accepted}  "
              f"reasons={result.reasons or 'none'}")

        # Simulate motion for the loopback; wait a bit for real.
        if kind == "loopback":
            for _ in range(args.steps):
                if hasattr(bridge, "step"):
                    bridge.step(dt_s=0.5)
        else:
            time.sleep(4.0)

        # Imagined casualty sighting at this waypoint.
        sighted = CasualtyNode(
            id=f"C{wp_idx + 1}",
            location=GeoPose(
                x=bridge.telemetry.pose.x,
                y=bridge.telemetry.pose.y,
            ),
            platform_source=bridge.platform_id,
            confidence=0.75,
            status="assessed",
            triage_priority="immediate" if wp_idx == 1 else "delayed",
            hypotheses=[TraumaHypothesis(
                kind="hemorrhage_suspected",
                score=0.6 + 0.1 * wp_idx,
            )],
        )
        manager.publish_casualty(sighted)
        print(f"[wp {wp_idx + 1}] published casualty {sighted.id}  "
              f"priority={sighted.triage_priority}  "
              f"pose=({bridge.telemetry.pose.x:+.2f}, "
              f"{bridge.telemetry.pose.y:+.2f})")
        print(f"[wp {wp_idx + 1}] battery = {bridge.telemetry.battery_pct:.1f}%")

    _hr()
    try:
        bridge.land()
    except AttributeError:
        pass
    bridge.close()
    print("[end] bridge closed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
