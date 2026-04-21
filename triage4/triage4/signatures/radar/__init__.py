"""Multi-axis radar / compass shape descriptors.

Ported from svend4/infom ``signatures/heptagram.py``,
``signatures/octagram.py`` and ``signatures/hexsig.py``.
See ``third_party/ATTRIBUTION.md``.

Upstream uses these as multi-dimensional "stars" for knowledge-graph
cluster summaries. In triage4 they provide ready-made radar profiles for
casualty-level multi-axis state:

- HeptagramSignature: 7 axes (strength, direction, temporal, confidence,
  scale, context, source). Good for "signal quality + severity".
- OctagramSignature: 8 axes on a compass with 3D elevation. Good for
  situational context (abstract/concrete, future/past, complex/simple,
  global/local).
- HexSignature: 6-bit Q6 hypercube code plus Voronoi / Delaunay / shortest
  path utilities. Good as a compact categorical fingerprint.
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
from .hexsig import (
    DEGREE as HEXSIG_DEGREE,
    DISTANCE_SPECTRUM as HEXSIG_DISTANCE_SPECTRUM,
    HexSignature,
    MAX_DIST as HEXSIG_MAX_DIST,
    N_DIMS as HEXSIG_N_DIMS,
    N_NODES as HEXSIG_N_NODES,
    antipode,
    bfs_distances,
    build_hex_signature,
    delaunay_graph,
    embed_to_q6,
    from_bits,
    hamming,
    hamming_ball,
    hamming_sphere,
    is_perfect_code,
    median as hex_median,
    metric_interval,
    neighbors,
    packing_number,
    shortest_path,
    to_bits,
    voronoi_cells,
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
    "HEXSIG_DEGREE",
    "HEXSIG_DISTANCE_SPECTRUM",
    "HEXSIG_MAX_DIST",
    "HEXSIG_N_DIMS",
    "HEXSIG_N_NODES",
    "HeptagramRay",
    "HeptagramSignature",
    "HexSignature",
    "OCTAGRAM_N_RAYS",
    "OctaRay",
    "OctagramSignature",
    "SkeletonType",
    "antipode",
    "bfs_distances",
    "build_heptagram_signature",
    "build_hex_signature",
    "build_octagram_signature",
    "build_shell_octagram",
    "build_tower_octagram",
    "delaunay_graph",
    "embed_to_q6",
    "from_bits",
    "hamming",
    "hamming_ball",
    "hamming_sphere",
    "heptagram_distance",
    "heptagram_from_edge_weights",
    "hex_median",
    "is_perfect_code",
    "metric_interval",
    "neighbors",
    "octagram_distance",
    "packing_number",
    "shortest_path",
    "to_bits",
    "voronoi_cells",
]
