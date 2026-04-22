"""Denied-comms casualty graph on top of CRDT primitives.

Part of Phase 9c (innovation pack 2, idea #4). When the backbone is
down, each medic / operator tablet keeps its own
``CRDTCasualtyGraph``. Whenever any two replicas meet (Bluetooth, LoRa,
ad-hoc WiFi) they call ``merge`` and end up with identical state
without needing a central server.

Design:
- **OR-set** of casualty ids (add-then-remove-safe);
- **LWW-register** for ``triage_priority`` (latest timestamp wins; ties
  broken by replica_id ordering);
- **G-counter** of observation counts per casualty.

Keeps the API narrow — we pay only for what triage needs, not a full
Riak/automerge stack.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class LWWEntry:
    value: str
    ts: float
    replica_id: str


def _lww_wins(a: LWWEntry, b: LWWEntry) -> LWWEntry:
    if a.ts != b.ts:
        return a if a.ts > b.ts else b
    return a if a.replica_id >= b.replica_id else b


@dataclass
class CRDTCasualtyGraph:
    """Conflict-free casualty graph — mergeable across partitions."""

    replica_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    # OR-set: adds keyed by unique tags, tombstones track removals.
    _adds: dict[str, set[str]] = field(default_factory=dict)
    _tombstones: dict[str, set[str]] = field(default_factory=dict)
    # LWW register per casualty: id → (value, ts, replica_id).
    _priority: dict[str, LWWEntry] = field(default_factory=dict)
    # G-counter of observation counts: id → {replica_id: count}.
    _observation_counts: dict[str, dict[str, int]] = field(default_factory=dict)

    # --- OR-set over casualty ids ----------------------------------------

    def add_casualty(self, casualty_id: str) -> None:
        tag = f"{self.replica_id}:{uuid.uuid4()}"
        self._adds.setdefault(casualty_id, set()).add(tag)

    def remove_casualty(self, casualty_id: str) -> None:
        tags = self._adds.get(casualty_id, set())
        self._tombstones.setdefault(casualty_id, set()).update(tags)

    @property
    def casualty_ids(self) -> set[str]:
        alive: set[str] = set()
        for cid, tags in self._adds.items():
            surviving = tags - self._tombstones.get(cid, set())
            if surviving:
                alive.add(cid)
        return alive

    # --- LWW priority ----------------------------------------------------

    def set_priority(self, casualty_id: str, priority: str, ts: float | None = None) -> None:
        entry = LWWEntry(
            value=priority,
            ts=float(ts) if ts is not None else time.time(),
            replica_id=self.replica_id,
        )
        current = self._priority.get(casualty_id)
        self._priority[casualty_id] = (
            entry if current is None else _lww_wins(current, entry)
        )

    def get_priority(self, casualty_id: str) -> str | None:
        entry = self._priority.get(casualty_id)
        return entry.value if entry is not None else None

    # --- G-counter observations -----------------------------------------

    def increment_observation(self, casualty_id: str) -> None:
        counts = self._observation_counts.setdefault(casualty_id, {})
        counts[self.replica_id] = counts.get(self.replica_id, 0) + 1

    def observation_count(self, casualty_id: str) -> int:
        counts = self._observation_counts.get(casualty_id, {})
        return sum(counts.values())

    # --- merge -----------------------------------------------------------

    def merge(self, other: "CRDTCasualtyGraph") -> None:
        """Merge another replica into this one. Commutative + idempotent."""
        for cid, tags in other._adds.items():
            self._adds.setdefault(cid, set()).update(tags)
        for cid, tags in other._tombstones.items():
            self._tombstones.setdefault(cid, set()).update(tags)

        for cid, other_entry in other._priority.items():
            current = self._priority.get(cid)
            self._priority[cid] = (
                other_entry if current is None else _lww_wins(current, other_entry)
            )

        for cid, other_counts in other._observation_counts.items():
            mine = self._observation_counts.setdefault(cid, {})
            for replica, count in other_counts.items():
                mine[replica] = max(mine.get(replica, 0), int(count))

    # --- serialization for transport ------------------------------------

    def snapshot(self) -> dict:
        return {
            "replica_id": self.replica_id,
            "adds": {k: sorted(v) for k, v in self._adds.items()},
            "tombstones": {k: sorted(v) for k, v in self._tombstones.items()},
            "priority": {
                k: {"value": v.value, "ts": v.ts, "replica_id": v.replica_id}
                for k, v in self._priority.items()
            },
            "observation_counts": {
                k: dict(v) for k, v in self._observation_counts.items()
            },
        }
