"""Event-sourced evidence memory (vendored-in from `infom`, adapted).

The upstream `infom` project ships a broader knowledge-graph with memory,
GraphRAG and causal links. triage4 needs only the slice that is useful for
decision-support auditing: a monotonically-growing event log plus named
snapshots that can be replayed for after-action review.

See `third_party/INFOM_ATTRIBUTION.md` for provenance.
"""

from __future__ import annotations

import copy
import time
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class EvidenceEvent:
    ts: float
    kind: str
    casualty_id: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class EvidenceMemory:
    """Append-only event log with causal edges and named snapshots.

    Design borrowed from `infom`:
      - every event has a timestamp and a kind (detection, signature,
        hypothesis, handoff, revisit, …);
      - causal edges connect a derived event to the events that produced it;
      - snapshots freeze the whole graph under a name so it can be diff-ed
        or replayed later.
    """

    def __init__(self) -> None:
        self._events: list[EvidenceEvent] = []
        self._causal: list[tuple[int, int, str]] = []
        self._snapshots: dict[str, dict] = {}

    # ------------------------------------------------------------------ events

    def record(
        self,
        kind: str,
        casualty_id: str,
        payload: dict[str, Any] | None = None,
        *,
        ts: float | None = None,
        causes: list[int] | None = None,
    ) -> int:
        event = EvidenceEvent(
            ts=float(ts if ts is not None else time.time()),
            kind=str(kind),
            casualty_id=str(casualty_id),
            payload=dict(payload or {}),
        )
        self._events.append(event)
        event_idx = len(self._events) - 1
        for cause_idx in causes or []:
            if 0 <= cause_idx < event_idx:
                self._causal.append((cause_idx, event_idx, "caused"))
        return event_idx

    def events_for(self, casualty_id: str) -> list[EvidenceEvent]:
        return [e for e in self._events if e.casualty_id == casualty_id]

    def causal_chain(self, event_idx: int) -> list[int]:
        """Return the transitive set of upstream events that caused this one."""
        if not 0 <= event_idx < len(self._events):
            return []
        backward: dict[int, list[int]] = {}
        for src, dst, _ in self._causal:
            backward.setdefault(dst, []).append(src)

        seen: set[int] = set()
        stack = list(backward.get(event_idx, []))
        while stack:
            i = stack.pop()
            if i in seen:
                continue
            seen.add(i)
            stack.extend(backward.get(i, []))
        return sorted(seen)

    # --------------------------------------------------------------- snapshots

    def snapshot(self, name: str) -> None:
        self._snapshots[str(name)] = {
            "events": [copy.deepcopy(e.to_dict()) for e in self._events],
            "causal": list(self._causal),
            "ts": time.time(),
        }

    def load_snapshot(self, name: str) -> dict | None:
        snap = self._snapshots.get(name)
        return copy.deepcopy(snap) if snap is not None else None

    # -------------------------------------------------------------- serialization

    def as_json(self) -> dict:
        return {
            "events": [e.to_dict() for e in self._events],
            "causal": list(self._causal),
            "snapshots": sorted(self._snapshots.keys()),
        }

    def __len__(self) -> int:
        return len(self._events)
