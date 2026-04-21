"""K3-2.2 Relational Body-State Layer.

Composes evidence tokens into a graph of hypotheses with supporting edges.
"""

from .body_state_graph import BodyStateGraph
from .evidence_memory import EvidenceEvent, EvidenceMemory
from .graph_consistency import check_casualty_graph_consistency

__all__ = [
    "BodyStateGraph",
    "EvidenceEvent",
    "EvidenceMemory",
    "check_casualty_graph_consistency",
]
