from __future__ import annotations

from triage4.core.models import CasualtyNode


class HumanHandoffService:
    """Packages a casualty record into a medic-facing payload."""

    def package_for_medic(self, casualty: CasualtyNode) -> dict:
        recommended = (
            "mediate_immediate_access"
            if casualty.triage_priority == "immediate"
            else "inspect"
        )
        return {
            "casualty_id": casualty.id,
            "location": casualty.location.__dict__,
            "priority": casualty.triage_priority,
            "confidence": casualty.confidence,
            "top_hypotheses": [h.__dict__ for h in casualty.hypotheses[:3]],
            "recommended_action": recommended,
        }
