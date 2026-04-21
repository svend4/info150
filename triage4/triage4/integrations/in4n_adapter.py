from __future__ import annotations

from triage4.graph.casualty_graph import CasualtyGraph


class In4nSceneAdapter:
    """Adapter that exports a scene description usable by in4n-style viewers."""

    def export_scene(self, graph: CasualtyGraph) -> dict:
        nodes = [
            {
                "id": n.id,
                "x": n.location.x,
                "y": n.location.y,
                "group": n.triage_priority,
                "confidence": n.confidence,
            }
            for n in graph.all_nodes()
        ]
        links = [{"source": a, "target": b, "kind": rel} for (a, rel, b) in graph.edges]
        return {"nodes": nodes, "links": links}
