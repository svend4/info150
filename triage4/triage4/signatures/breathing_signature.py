from __future__ import annotations

from typing import Iterable


class BreathingSignatureExtractor:
    """Very small simulation-first breathing proxy.

    Input: short time-series of chest amplitudes or torso height changes.
    Output: breathing_curve, chest_motion_fd, respiration_proxy, quality_score.
    The fractal-dimension-like score is a lightweight motion-complexity proxy.
    """

    def extract(self, signal: Iterable[float]) -> dict:
        curve = [float(v) for v in signal]
        if len(curve) < 2:
            return {
                "breathing_curve": curve,
                "chest_motion_fd": 0.0,
                "respiration_proxy": 0.0,
                "quality_score": 0.0,
            }

        deltas = [abs(curve[i + 1] - curve[i]) for i in range(len(curve) - 1)]
        mean_delta = sum(deltas) / len(deltas)
        amplitude = max(curve) - min(curve)
        mean_curve = sum(curve) / len(curve)
        variance_proxy = sum((x - mean_curve) ** 2 for x in curve) / len(curve)

        chest_motion_fd = min(1.0, max(0.0, (mean_delta * 2.4) + (variance_proxy * 1.8)))
        respiration_proxy = min(1.0, max(0.0, amplitude * 2.0))
        quality_score = min(1.0, max(0.2, 0.4 + amplitude + mean_delta))

        return {
            "breathing_curve": curve,
            "chest_motion_fd": round(chest_motion_fd, 3),
            "respiration_proxy": round(respiration_proxy, 3),
            "quality_score": round(quality_score, 3),
        }
