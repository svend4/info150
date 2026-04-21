from __future__ import annotations

from triage4.graph.casualty_graph import CasualtyGraph


class InfoMGraphAdapter:
    """Adapter that exports a triage4 casualty graph to an infom-like JSON."""

    def snapshot(self, graph: CasualtyGraph) -> dict:
        return {
            "kind": "casualty_graph_snapshot",
            "version": 1,
            "data": graph.as_json(),
        }
