"""triage4 — CRDT denied-comms coordination demo.

Simulates three medics (A, B, C) working the same incident without a
working backbone. Each tablet keeps a ``CRDTCasualtyGraph`` replica and
they periodically sync pairwise whenever two medics meet.

The script shows that:
- every replica converges on the same set of casualties and priorities
  regardless of sync order;
- conflicting priority updates are resolved by timestamp (LWW), not by
  a central server;
- observation counts accumulate across all replicas.

Run from the project root:

    python examples/crdt_sync_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from triage4.state_graph import CRDTCasualtyGraph  # noqa: E402


def _show(label: str, graphs: dict[str, CRDTCasualtyGraph]) -> None:
    print(f"\n-- {label} --")
    for name, g in graphs.items():
        ids = sorted(g.casualty_ids)
        prio = {c: g.get_priority(c) for c in ids}
        obs = {c: g.observation_count(c) for c in ids}
        print(f"medic {name}: {len(ids)} casualties")
        for cid in ids:
            print(
                f"   {cid:<4s} priority={prio[cid]:<10s} "
                f"observations={obs[cid]}"
            )


def main() -> None:
    a = CRDTCasualtyGraph(replica_id="medic_A")
    b = CRDTCasualtyGraph(replica_id="medic_B")
    c = CRDTCasualtyGraph(replica_id="medic_C")

    # Medic A sees C1 and C2 first.
    a.add_casualty("C1")
    a.set_priority("C1", "immediate", ts=1.0)
    a.increment_observation("C1")
    a.add_casualty("C2")
    a.set_priority("C2", "delayed", ts=2.0)
    a.increment_observation("C2")

    # Medic B independently sees C2 and C3 on the other side of the scene.
    b.add_casualty("C2")
    b.set_priority("C2", "minimal", ts=2.5)   # disagrees with A on C2
    b.increment_observation("C2")
    b.add_casualty("C3")
    b.set_priority("C3", "immediate", ts=3.0)
    b.increment_observation("C3")

    # Medic C only sees C4 — they're isolated at first.
    c.add_casualty("C4")
    c.set_priority("C4", "delayed", ts=1.5)
    c.increment_observation("C4")

    _show("After independent observations", {"A": a, "B": b, "C": c})

    # A and B meet. Sync both ways.
    a.merge(b)
    b.merge(a)
    _show("After A <-> B meet", {"A": a, "B": b, "C": c})

    # Later, C meets A.
    c.merge(a)
    a.merge(c)
    _show("After C <-> A meet", {"A": a, "B": b, "C": c})

    # Finally, B gets to sync with C.
    b.merge(c)
    c.merge(b)
    _show("After B <-> C meet", {"A": a, "B": b, "C": c})

    # Sanity: all three replicas now carry the same visible state.
    ids = sorted(a.casualty_ids)
    print(f"\nall replicas see: {ids}")
    for cid in ids:
        priorities = {name: g.get_priority(cid) for name, g in (("A", a), ("B", b), ("C", c))}
        print(f"   {cid} priority (per replica): {priorities}")
        assert len(set(priorities.values())) == 1, "CRDT divergence!"

    print("\n✓ all replicas converged — denied-comms handoff works")


if __name__ == "__main__":
    main()
