from __future__ import annotations

from triage4.core.models import CasualtyNode


class CasualtyGraph:
    """In-memory graph of casualties and their observational edges."""

    def __init__(self) -> None:
        self.nodes: dict[str, CasualtyNode] = {}
        self.edges: list[tuple[str, str, str]] = []

    def upsert(self, node: CasualtyNode) -> None:
        self.nodes[node.id] = node

    def link(self, a: str, rel: str, b: str) -> None:
        self.edges.append((a, rel, b))

    def all_nodes(self) -> list[CasualtyNode]:
        return list(self.nodes.values())

    def immediate_nodes(self) -> list[CasualtyNode]:
        vals = [n for n in self.nodes.values() if n.triage_priority == "immediate"]
        return sorted(vals, key=lambda n: (-n.confidence, n.last_seen_ts))

    def as_json(self) -> dict:
        return {
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": self.edges,
        }
