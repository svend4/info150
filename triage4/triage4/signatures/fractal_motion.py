from __future__ import annotations

from typing import Iterable

import numpy as np

from triage4.signatures.fractal import (
    BoxCountingFD,
    RichardsonDivider,
    css_similarity,
    css_to_feature_vector,
    curvature_scale_space,
    freeman_chain_code,
    mask_to_contour,
)


class FractalMotionAnalyzer:
    """Motion/shape descriptors backed by vendored ``meta2`` fractal math.

    Uses the real Richardson-divider and box-counting implementations from
    ``svend4/meta2`` (see ``LICENSES/meta2.LICENSE``), with triage-oriented
    helpers around them.
    """

    def __init__(
        self,
        divider: RichardsonDivider | None = None,
        box_counter: BoxCountingFD | None = None,
    ) -> None:
        self._divider = divider or RichardsonDivider()
        self._box = box_counter or BoxCountingFD()

    # -- motion (1D time series) ------------------------------------------------

    def chest_motion_fd(self, series: Iterable[float]) -> float:
        values = list(series)
        if len(values) < 4:
            return 0.0
        dim = self._divider.estimate_1d(values)
        return round(max(0.0, min(1.0, dim - 1.0)), 3)

    # -- wound / region (2D contour or mask) ------------------------------------

    def wound_boundary_fd(self, contour_or_mask) -> float:
        arr = np.asarray(contour_or_mask)
        dim = self._box.estimate(arr)
        return round(max(0.0, min(1.0, dim - 1.0)), 3)

    def wound_shape_vector(self, contour, n_sigmas: int = 7, n_bins: int = 32):
        """CSS-based shape descriptor of a closed wound/posture contour."""
        contour_arr = np.asarray(contour, dtype=float)
        if contour_arr.ndim != 2 or contour_arr.shape[0] < 4:
            return np.zeros(n_sigmas * n_bins)
        css = curvature_scale_space(contour_arr, n_sigmas=n_sigmas)
        return css_to_feature_vector(css, n_bins=n_bins)

    def wound_shape_similarity(self, vec_a, vec_b) -> float:
        return css_similarity(np.asarray(vec_a), np.asarray(vec_b))

    def wound_shape_hash(self, contour) -> str:
        return freeman_chain_code(np.asarray(contour))

    # -- utilities --------------------------------------------------------------

    @staticmethod
    def mask_to_contour(mask):
        return mask_to_contour(mask)
