from __future__ import annotations

from triage4.graph.casualty_graph import CasualtyGraph
from triage4.state_graph.evidence_memory import EvidenceMemory


class InfoMGraphAdapter:
    """Exports triage4 state into an infom-like knowledge-graph snapshot.

    Uses the vendored-in `EvidenceMemory` (see
    `triage4.state_graph.evidence_memory`) so the output shape is compatible
    with infom-style replay and causal-chain queries.
    """

    def __init__(self, memory: EvidenceMemory | None = None) -> None:
        self.memory = memory or EvidenceMemory()

    def record_assessment(self, casualty_id: str, priority: str, confidence: float) -> int:
        return self.memory.record(
            kind="assessment",
            casualty_id=casualty_id,
            payload={"priority": priority, "confidence": confidence},
        )

    def snapshot(self, graph: CasualtyGraph, name: str = "latest") -> dict:
        self.memory.snapshot(name)
        return {
            "kind": "casualty_graph_snapshot",
            "version": 2,
            "snapshot_name": name,
            "casualty_graph": graph.as_json(),
            "evidence_memory": self.memory.as_json(),
        }
