"""triage4 — mission replay demo.

Shows the K3-3.3 world-replay path: as a mission unfolds, every
scene transition is appended to a ``TimelineStore``; after the
mission, a ``ReplayEngine`` walks the timeline frame-by-frame so an
operator (or a counterfactual scorer) can reconstruct what was
known at each tick.

This demo simulates a 6-tick mission with one UAV and four
casualties. Casualty C1's priority is revised from ``delayed`` to
``immediate`` at tick 3 when new bleeding evidence is observed. The
replay shows the revision.

Run from the project root:

    python examples/mission_replay_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from triage4.core.models import CasualtyNode, GeoPose  # noqa: E402
from triage4.graph.casualty_graph import CasualtyGraph  # noqa: E402
from triage4.world_replay.replay_engine import ReplayEngine  # noqa: E402
from triage4.world_replay.timeline_store import TimelineStore  # noqa: E402


def _node(cid: str, x: float, y: float, priority: str, conf: float = 0.8) -> CasualtyNode:
    return CasualtyNode(
        id=cid,
        location=GeoPose(x=x, y=y),
        platform_source="uav",
        confidence=conf,
        status="assessed",
        triage_priority=priority,
    )


def _snapshot(graph: CasualtyGraph, uav_x: float, uav_y: float) -> dict:
    return {
        "uav": {"x": uav_x, "y": uav_y},
        "casualties": [
            {"id": n.id, "x": n.location.x, "y": n.location.y,
             "priority": n.triage_priority, "confidence": n.confidence}
            for n in graph.all_nodes()
        ],
    }


def main() -> None:
    graph = CasualtyGraph()
    graph.upsert(_node("C1", 10.0, 20.0, "delayed", conf=0.7))
    graph.upsert(_node("C2", 25.0, 15.0, "minimal"))
    graph.upsert(_node("C3", 40.0, 30.0, "immediate"))
    graph.upsert(_node("C4", 15.0, 45.0, "minimal"))

    store = TimelineStore()

    print("recording mission timeline")
    print("=" * 70)
    for t in range(6):
        uav_x = 5.0 + 8.0 * t
        uav_y = 10.0 + 5.0 * t

        # At t=3 we get new bleeding evidence on C1 — revise its priority.
        if t == 3:
            c1 = graph.nodes["C1"]
            c1.triage_priority = "immediate"
            c1.confidence = 0.92
            print(f"  t={t}  event: C1 reclassified delayed → immediate")

        store.record(float(t), _snapshot(graph, uav_x, uav_y))

    print(f"\nrecorded {len(store)} frames")
    print()

    print("replaying the mission")
    print("=" * 70)
    replay = ReplayEngine(store)
    while True:
        frame = replay.next_frame()
        if frame is None or replay._idx > len(store):
            break

        t = frame["t"]
        uav = frame["uav"]
        c1 = next(c for c in frame["casualties"] if c["id"] == "C1")
        n_immediate = sum(1 for c in frame["casualties"] if c["priority"] == "immediate")
        print(
            f"  t={t:.1f}  uav=({uav['x']:.1f}, {uav['y']:.1f})  "
            f"C1.priority={c1['priority']:<10s}  total-immediate={n_immediate}"
        )

    print("\n" + "=" * 70)
    print("frame-at random-access example: frame_at(3)")
    print("=" * 70)
    frame3 = replay.frame_at(3)
    print(f"  t={frame3['t']}")
    for c in frame3["casualties"]:
        print(f"    {c['id']:<4s} ({c['x']:5.1f}, {c['y']:5.1f})  "
              f"priority={c['priority']}")

    print("\n✓ timeline replay works — operators can scrub any tick.")


if __name__ == "__main__":
    main()
