"""Fractal and shape descriptors.

Adapted from svend4/meta2 ``puzzle_reconstruction/algorithms/fractal``.
Covers the subset relevant to triage signals:

- ``box_counting`` — Minkowski-Bouligand FD of a 2D point contour / mask;
- ``divider`` — Richardson compass FD of a 1D signal or 2D polyline;
- ``css`` — Curvature Scale Space for wound / posture shape matching;
- ``chain_code`` — Freeman chain code as a fast shape hash.

IFS is intentionally not ported — triage4 does not need fractal code-book
reconstruction and it would drag in extra optimisation code. See
``LICENSES/meta2.LICENSE`` and ``third_party/ATTRIBUTION.md``.
"""

from .box_counting import (
    BoxCountingFD,
    box_counting_curve,
    box_counting_fd,
    mask_to_contour,
)
from .chain_code import freeman_chain_code
from .css import (
    css_similarity,
    css_similarity_mirror,
    css_to_feature_vector,
    curvature_scale_space,
)
from .divider import (
    RichardsonDivider,
    divider_curve,
    divider_fd,
    signal_to_contour,
)

__all__ = [
    "BoxCountingFD",
    "RichardsonDivider",
    "box_counting_curve",
    "box_counting_fd",
    "curvature_scale_space",
    "css_similarity",
    "css_similarity_mirror",
    "css_to_feature_vector",
    "divider_curve",
    "divider_fd",
    "freeman_chain_code",
    "mask_to_contour",
    "signal_to_contour",
]
