from __future__ import annotations

from triage4.core.models import CasualtyNode


class TaskAllocator:
    """Suggests an ordering of casualties for medics or robots.

    Heuristic: immediate first, then delayed, then minimal; within each
    priority class, higher confidence and newer observation come first.
    """

    _PRIORITY_ORDER = {"immediate": 0, "delayed": 1, "minimal": 2, "unknown": 3, "expectant": 4}

    def recommend(self, nodes: list[CasualtyNode]) -> list[dict]:
        def sort_key(n: CasualtyNode) -> tuple[int, float, float]:
            rank = self._PRIORITY_ORDER.get(n.triage_priority, 99)
            return (rank, -n.confidence, -n.last_seen_ts)

        ordered = sorted(nodes, key=sort_key)
        return [
            {
                "casualty_id": n.id,
                "priority": n.triage_priority,
                "confidence": n.confidence,
                "location": {"x": n.location.x, "y": n.location.y},
            }
            for n in ordered
        ]
