from __future__ import annotations

from typing import Iterable

from triage4.signatures.fractal_motion import FractalMotionAnalyzer


class Meta2SignatureAdapter:
    """Adapter that wraps meta2-style fractal descriptors for triage4.

    Currently uses the lightweight in-tree `FractalMotionAnalyzer` as a stand-in
    so the contract is stable and testable before the real upstream is wired.
    """

    def __init__(self, analyzer: FractalMotionAnalyzer | None = None) -> None:
        self.analyzer = analyzer or FractalMotionAnalyzer()

    def to_fractal_motion(self, curve: Iterable[float]) -> float:
        return self.analyzer.chest_motion_fd(curve)
