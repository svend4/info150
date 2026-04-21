"""Uncertainty propagation for triage decisions.

Part of triage4 Phase 7. Takes per-signal quality / confidence numbers
from the extractors (e.g. ``BreathingSignatureExtractor`` returns a
``quality_score``, ``PerfusionSignatureExtractor`` returns one too) and
combines them into a single uncertainty estimate for a fused triage
decision.

The model is intentionally simple:
- confidence per channel ∈ [0, 1];
- overall confidence = Σ (w_i · conf_i) / Σ w_i;
- overall uncertainty = 1 − overall_confidence, attenuated by
  ``visibility_score``.

Returns :class:`UncertaintyReport` so the caller can either show the
breakdown to the operator or pass ``adjusted_score`` through further
fusion.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from triage4.core.models import CasualtySignature


@dataclass
class UncertaintyReport:
    base_score: float
    overall_confidence: float
    overall_uncertainty: float
    adjusted_score: float
    per_channel_confidence: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name, val in (
            ("base_score", self.base_score),
            ("overall_confidence", self.overall_confidence),
            ("overall_uncertainty", self.overall_uncertainty),
            ("adjusted_score", self.adjusted_score),
        ):
            if not 0.0 <= val <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {val}")


class UncertaintyModel:
    """Combine per-channel quality into an overall confidence."""

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = dict(
            weights
            or {
                "breathing_quality": 0.30,
                "perfusion_quality": 0.25,
                "bleeding_confidence": 0.25,
                "thermal_quality": 0.20,
            }
        )

    def from_signature(
        self, sig: CasualtySignature, base_score: float
    ) -> UncertaintyReport:
        raw = sig.raw_features or {}
        per_channel: dict[str, float] = {}
        for name in self.weights:
            val = raw.get(name)
            if val is None:
                continue
            per_channel[name] = _clamp01(float(val))

        if per_channel:
            total_w = sum(self.weights[c] for c in per_channel)
            overall_conf = sum(
                per_channel[c] * self.weights[c] for c in per_channel
            ) / total_w
        else:
            overall_conf = 0.5

        visibility = _clamp01(sig.visibility_score)
        overall_conf = _clamp01(overall_conf * (0.5 + 0.5 * visibility))
        uncertainty = _clamp01(1.0 - overall_conf)
        adjusted = _clamp01(base_score * overall_conf)

        return UncertaintyReport(
            base_score=_clamp01(base_score),
            overall_confidence=overall_conf,
            overall_uncertainty=uncertainty,
            adjusted_score=adjusted,
            per_channel_confidence=per_channel,
        )


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))
