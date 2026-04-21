from __future__ import annotations

from triage4.core.models import CasualtyNode


class ExplainabilityBuilder:
    """Builds human-readable summaries of a casualty's triage state."""

    def summarize(self, node: CasualtyNode) -> dict:
        return {
            "casualty_id": node.id,
            "priority": node.triage_priority,
            "confidence": node.confidence,
            "top_hypotheses": [
                {"kind": h.kind, "score": h.score, "why": h.explanation}
                for h in sorted(node.hypotheses, key=lambda x: x.score, reverse=True)
            ],
        }
