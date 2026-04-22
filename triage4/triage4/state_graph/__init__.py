"""K3-1.3 / K3-2.2 Relational Body-State + Skeletal Layer.

Composes evidence tokens into a graph of hypotheses with supporting
edges (K3-2.2), hosts the denied-comms CRDT casualty graph (Phase
9c), reconciles contradictory hypotheses via ``ConflictResolver``
(K3-2.2), and tracks time-evolving joint positions + wound
intensity via ``SkeletalGraph`` (K3-1.3).
"""

from .body_state_graph import BodyStateGraph
from .conflict_resolver import (
    ConflictGroup,
    ConflictResolver,
    ResolvedHypotheses,
    ResolvedHypothesis,
)
from .evidence_memory import EvidenceEvent, EvidenceMemory
from .graph_consistency import check_casualty_graph_consistency
from .crdt_graph import CRDTCasualtyGraph, LWWEntry
from .skeletal_graph import (
    AsymmetryReport,
    JointObservation,
    JointTrend,
    SkeletalGraph,
    SkeletalSnapshot,
    UnknownJoint,
)

__all__ = [
    "AsymmetryReport",
    "BodyStateGraph",
    "CRDTCasualtyGraph",
    "ConflictGroup",
    "ConflictResolver",
    "EvidenceEvent",
    "EvidenceMemory",
    "JointObservation",
    "JointTrend",
    "LWWEntry",
    "ResolvedHypotheses",
    "ResolvedHypothesis",
    "SkeletalGraph",
    "SkeletalSnapshot",
    "UnknownJoint",
    "check_casualty_graph_consistency",
]
