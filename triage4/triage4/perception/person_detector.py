from __future__ import annotations

from typing import Any


class PersonDetector:
    """Stub person detector.

    Replaceable with a real CV model. Output contract:
        [{"bbox": [x1, y1, x2, y2], "score": 0.0..1.0}, ...]
    """

    def detect(self, frame_rgb: Any) -> list[dict]:
        raise NotImplementedError

    @staticmethod
    def box(x1: float, y1: float, x2: float, y2: float, score: float = 1.0) -> dict:
        return {"bbox": [float(x1), float(y1), float(x2), float(y2)], "score": float(score)}
