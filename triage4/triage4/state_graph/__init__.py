"""K3-2.2 Relational Body-State Layer.

Composes evidence tokens into a graph of hypotheses with supporting edges.
Also hosts the denied-comms CRDT casualty graph (Phase 9c).
"""

from .body_state_graph import BodyStateGraph
from .evidence_memory import EvidenceEvent, EvidenceMemory
from .graph_consistency import check_casualty_graph_consistency
from .crdt_graph import CRDTCasualtyGraph, LWWEntry

__all__ = [
    "BodyStateGraph",
    "CRDTCasualtyGraph",
    "EvidenceEvent",
    "EvidenceMemory",
    "LWWEntry",
    "check_casualty_graph_consistency",
]
