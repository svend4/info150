"""Multi-axis radar / compass shape descriptors.

Ported from svend4/infom ``signatures/heptagram.py`` and
``signatures/octagram.py``. See ``third_party/ATTRIBUTION.md``.

Upstream uses these as 7-/8-dimensional "stars" for knowledge-graph
cluster summaries. In triage4 they provide a ready-made radar profile
that can be applied to casualty-level multi-axis state:

- HeptagramSignature: 7 axes — strength, direction, temporal, confidence,
  scale, context, source. Natural fit for "signal quality + severity"
  profiles.
- OctagramSignature: 8 axes on a compass with 3D elevation. Natural fit
  for situational context (abstract/concrete, future/past, complex/simple,
  global/local).
"""

from .heptagram import (
    HeptagramSignature,
    N_RAYS as HEPTAGRAM_N_RAYS,
    RAY_LABELS as HEPTAGRAM_RAY_LABELS,
    Ray as HeptagramRay,
    build_heptagram_signature,
    heptagram_distance,
    heptagram_from_edge_weights,
)
from .octagram import (
    AXIS_SEMANTICS,
    COMPASS,
    N_RAYS as OCTAGRAM_N_RAYS,
    OctaRay,
    OctagramSignature,
    SkeletonType,
    build_octagram_signature,
    build_shell_octagram,
    build_tower_octagram,
    octagram_distance,
)

__all__ = [
    "AXIS_SEMANTICS",
    "COMPASS",
    "HEPTAGRAM_N_RAYS",
    "HEPTAGRAM_RAY_LABELS",
    "HeptagramRay",
    "HeptagramSignature",
    "OCTAGRAM_N_RAYS",
    "OctaRay",
    "OctagramSignature",
    "SkeletonType",
    "build_heptagram_signature",
    "build_octagram_signature",
    "build_shell_octagram",
    "build_tower_octagram",
    "heptagram_distance",
    "heptagram_from_edge_weights",
    "octagram_distance",
]
