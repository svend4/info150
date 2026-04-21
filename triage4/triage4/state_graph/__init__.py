"""K3-2.2 Relational Body-State Layer.

Composes evidence tokens into a graph of hypotheses with supporting edges.
"""

from .body_state_graph import BodyStateGraph
from .evidence_memory import EvidenceEvent, EvidenceMemory

__all__ = ["BodyStateGraph", "EvidenceEvent", "EvidenceMemory"]
