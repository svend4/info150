"""Box-counting fractal dimension.

Adapted (not copied) from the `meta2.signatures.fractal` module as described
in the project drafts. The algorithm is the standard Minkowski–Bouligand
box-counting method restricted to 2D binary masks.

Implementation is pure-Python (no NumPy) to keep triage4 dependency-light.
For wound-boundary complexity or thermal-anomaly texture, a binary mask is
sampled at a sequence of box sizes; the slope of log(N) over log(1/size)
in a log-log plot approximates the fractal dimension.
"""

from __future__ import annotations

import math
from typing import Sequence


Mask = Sequence[Sequence[int]]


class BoxCountingFD:
    """Box-counting fractal-dimension estimator.

    Parameters
    ----------
    box_sizes:
        Iterable of box sizes (in pixels) to sample. Must be >= 2.
    """

    def __init__(self, box_sizes: Sequence[int] = (2, 4, 8, 16, 32)) -> None:
        self.box_sizes = tuple(int(s) for s in box_sizes if int(s) >= 2)
        if len(self.box_sizes) < 2:
            raise ValueError("box_sizes must contain at least two values >= 2")

    def estimate(self, mask: Mask) -> float:
        """Estimate fractal dimension of a 2D binary mask.

        Returns a value in roughly [1.0, 2.0]. Returns 0.0 if the mask is
        empty or degenerate.
        """
        if not mask or not mask[0]:
            return 0.0

        h = len(mask)
        w = len(mask[0])

        log_inv_sizes: list[float] = []
        log_counts: list[float] = []

        for size in self.box_sizes:
            if size > min(h, w):
                continue
            count = 0
            for y0 in range(0, h, size):
                for x0 in range(0, w, size):
                    if self._box_has_pixel(mask, x0, y0, size, w, h):
                        count += 1
            if count <= 0:
                continue
            log_inv_sizes.append(math.log(1.0 / size))
            log_counts.append(math.log(count))

        if len(log_counts) < 2:
            return 0.0

        slope = _linear_slope(log_inv_sizes, log_counts)
        return round(max(0.0, min(2.0, slope)), 3)

    @staticmethod
    def _box_has_pixel(mask: Mask, x0: int, y0: int, size: int, w: int, h: int) -> bool:
        y_end = min(y0 + size, h)
        x_end = min(x0 + size, w)
        for y in range(y0, y_end):
            row = mask[y]
            for x in range(x0, x_end):
                if row[x]:
                    return True
        return False


def _linear_slope(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
    den = sum((xs[i] - mean_x) ** 2 for i in range(n))
    if den == 0.0:
        return 0.0
    return num / den
