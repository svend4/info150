from __future__ import annotations

from typing import Iterable

from triage4.signatures.fractal import BoxCountingFD, RichardsonDivider


class FractalMotionAnalyzer:
    """Motion-complexity descriptors backed by vendored `meta2` fractal math.

    Uses Richardson-divider on 1D motion series (chest-motion curve, skin
    color curve) and box-counting on 2D binary masks (wound/thermal region).
    Both implementations are vendored in `triage4.signatures.fractal`.
    """

    def __init__(
        self,
        divider: RichardsonDivider | None = None,
        box_counter: BoxCountingFD | None = None,
    ) -> None:
        self._divider = divider or RichardsonDivider()
        self._box = box_counter or BoxCountingFD()

    def chest_motion_fd(self, series: Iterable[float]) -> float:
        values = [float(v) for v in series]
        if len(values) < 4:
            return 0.0
        dim = self._divider.estimate_1d(values)
        # Normalize to [0,1] so the downstream rapid-triage rule keeps working.
        # dim is in [1,2]; closer to 2 = more jagged = more motion complexity.
        return round(max(0.0, min(1.0, (dim - 1.0))), 3)

    def wound_boundary_fd(self, mask) -> float:
        dim = self._box.estimate(mask)
        return round(max(0.0, min(1.0, (dim - 1.0))), 3)
