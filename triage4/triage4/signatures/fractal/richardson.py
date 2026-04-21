"""Richardson-divider fractal dimension for 1D / polyline signals.

Adapted from the `meta2` fractal module (divider / Richardson method).
Useful for chest-motion curves, skin-perfusion curves and wound-boundary
polylines where we care about how jagged the signal is as we change the
measurement scale.
"""

from __future__ import annotations

import math
from typing import Sequence


class RichardsonDivider:
    """Richardson-style log-log slope of polyline length vs. step size."""

    def __init__(self, step_fractions: Sequence[float] = (0.05, 0.1, 0.2, 0.3)) -> None:
        self.step_fractions = tuple(float(s) for s in step_fractions if 0.0 < float(s) < 1.0)
        if len(self.step_fractions) < 2:
            raise ValueError("step_fractions must contain at least two values in (0,1)")

    def estimate_1d(self, signal: Sequence[float]) -> float:
        """Estimate a coastline-like dimension of a 1D time series.

        The signal is treated as a polyline (i, signal[i]). The returned
        dimension is in roughly [1.0, 2.0]; 1.0 means a smooth curve,
        closer to 2.0 means a space-filling / very jagged curve.
        """
        xs = [float(i) for i in range(len(signal))]
        ys = [float(v) for v in signal]
        return self._estimate_polyline(xs, ys)

    def _estimate_polyline(self, xs: list[float], ys: list[float]) -> float:
        n = len(xs)
        if n < 4:
            return 0.0

        total_span = max(xs) - min(xs)
        if total_span <= 0.0:
            return 0.0

        log_steps: list[float] = []
        log_lengths: list[float] = []

        for frac in self.step_fractions:
            step = max(1, int(frac * n))
            length = 0.0
            for i in range(step, n, step):
                dx = xs[i] - xs[i - step]
                dy = ys[i] - ys[i - step]
                length += math.hypot(dx, dy)
            if length <= 0.0:
                continue
            log_steps.append(math.log(step))
            log_lengths.append(math.log(length))

        if len(log_steps) < 2:
            return 0.0

        slope = _linear_slope(log_steps, log_lengths)
        dim = 1.0 - slope
        return round(max(1.0, min(2.0, dim)), 3)


def _linear_slope(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
    den = sum((xs[i] - mean_x) ** 2 for i in range(n))
    if den == 0.0:
        return 0.0
    return num / den
