from __future__ import annotations

from typing import Any


class PoseEstimator:
    """Stub pose estimator.

    Expected output: {"keypoints": {name: (x, y)}, "confidence": 0..1, "orientation": float}.
    """

    def estimate(self, frame_rgb: Any, bbox: list[float]) -> dict:
        raise NotImplementedError
