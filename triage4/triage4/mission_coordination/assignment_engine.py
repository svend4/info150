from __future__ import annotations

from triage4.core.models import CasualtyNode


class AssignmentEngine:
    """Very small heuristic robot/medic assigner.

    Pairs each immediate casualty with the nearest free agent (by Euclidean
    distance in the mission-frame XY plane).
    """

    def assign(
        self,
        casualties: list[CasualtyNode],
        agents: list[dict],
    ) -> list[dict]:
        free_agents = list(agents)
        out: list[dict] = []

        prioritized = sorted(
            casualties,
            key=lambda n: (0 if n.triage_priority == "immediate" else 1, -n.confidence),
        )

        for casualty in prioritized:
            if not free_agents:
                break
            best_idx = min(
                range(len(free_agents)),
                key=lambda i: self._distance(casualty, free_agents[i]),
            )
            agent = free_agents.pop(best_idx)
            out.append(
                {
                    "casualty_id": casualty.id,
                    "agent_id": agent.get("id"),
                    "agent_kind": agent.get("kind"),
                    "priority": casualty.triage_priority,
                }
            )
        return out

    @staticmethod
    def _distance(casualty: CasualtyNode, agent: dict) -> float:
        ax = float(agent.get("x", 0.0))
        ay = float(agent.get("y", 0.0))
        dx = casualty.location.x - ax
        dy = casualty.location.y - ay
        return (dx * dx + dy * dy) ** 0.5
