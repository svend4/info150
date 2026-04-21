from __future__ import annotations

import math
from typing import Iterable


class FractalMotionAnalyzer:
    """Lightweight motion-complexity descriptor.

    Adapted in spirit from the fractal logic of the upstream `meta2` project.
    Instead of a true box-counting fractal dimension, the MVP uses a stable
    proxy that captures how jagged or smooth a short motion series is.
    """

    def chest_motion_fd(self, series: Iterable[float]) -> float:
        values = [float(v) for v in series]
        if len(values) < 3:
            return 0.0

        deltas = [abs(values[i + 1] - values[i]) for i in range(len(values) - 1)]
        total = sum(deltas)
        if total <= 0.0:
            return 0.0

        mean_d = total / len(deltas)
        variance = sum((d - mean_d) ** 2 for d in deltas) / len(deltas)
        jitter = math.sqrt(variance)

        raw = (mean_d * 1.8) + (jitter * 2.2)
        return round(min(1.0, max(0.0, raw)), 3)
