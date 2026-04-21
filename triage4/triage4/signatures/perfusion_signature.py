from __future__ import annotations

from typing import Iterable


class PerfusionSignatureExtractor:
    """Skin-color / perfusion proxy.

    Input: short sequence of mean-color values or luminance for a skin patch.
    Output: perfusion_drop_score, pulse_proxy, quality_score.
    """

    def extract(self, patch_series: Iterable[float]) -> dict:
        seq = [float(v) for v in patch_series]
        if len(seq) < 2:
            return {
                "perfusion_drop_score": 0.0,
                "pulse_proxy": 0.0,
                "quality_score": 0.0,
            }

        baseline = seq[0]
        drops = [max(0.0, baseline - v) for v in seq[1:]]
        mean_drop = sum(drops) / len(drops) if drops else 0.0
        amplitude = max(seq) - min(seq)
        quality = min(1.0, max(0.2, 0.35 + amplitude))

        return {
            "perfusion_drop_score": round(min(1.0, mean_drop * 2.0), 3),
            "pulse_proxy": round(min(1.0, amplitude * 1.5), 3),
            "quality_score": round(quality, 3),
        }
