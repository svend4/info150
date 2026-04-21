from __future__ import annotations

from triage4.core.models import CasualtyNode


class RevisitPolicy:
    """Decides whether a casualty should be reinspected."""

    def should_revisit(self, node: CasualtyNode) -> bool:
        if node.triage_priority == "immediate" and node.confidence < 0.8:
            return True
        if node.status == "tracked" and (node.last_seen_ts - node.first_seen_ts) < 20:
            return True
        return False
