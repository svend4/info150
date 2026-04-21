from __future__ import annotations

from triage4.graph.casualty_graph import CasualtyGraph


class TacticalSceneBuilder:
    """Builds a lightweight tactical-scene description from a casualty graph."""

    def build(
        self,
        graph: CasualtyGraph,
        platforms: list[dict] | None = None,
        hazard_zones: list[dict] | None = None,
    ) -> dict:
        return {
            "platforms": list(platforms or []),
            "hazard_zones": list(hazard_zones or []),
            "casualties": [
                {
                    "id": n.id,
                    "x": n.location.x,
                    "y": n.location.y,
                    "priority": n.triage_priority,
                    "confidence": n.confidence,
                }
                for n in graph.all_nodes()
            ],
        }
