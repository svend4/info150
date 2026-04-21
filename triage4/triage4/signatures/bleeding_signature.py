from __future__ import annotations


class BleedingSignatureExtractor:
    """Minimal bleeding signature proxy.

    Inputs are three 0..1 scalars:
      * visual_redness  — strength of red pattern
      * thermal_drop    — local thermal inconsistency
      * pooling_hint    — static pooling / stain-like cue

    Output: bleeding_visual_score and confidence.
    """

    def extract(
        self,
        visual_redness: float,
        thermal_drop: float = 0.0,
        pooling_hint: float = 0.0,
    ) -> dict:
        vr = float(max(0.0, min(1.0, visual_redness)))
        td = float(max(0.0, min(1.0, thermal_drop)))
        ph = float(max(0.0, min(1.0, pooling_hint)))

        score = (vr * 0.65) + (td * 0.20) + (ph * 0.15)
        confidence = min(1.0, max(0.35, 0.45 + score * 0.5))

        return {
            "bleeding_visual_score": round(score, 3),
            "confidence": round(confidence, 3),
        }
