"""Fall-candidate detection — impact magnitude × post-impact stillness.

The two-factor pattern is the field-standard fall signature
(Bourke 2007, Kangas 2008, ISO 22537-1:2023):

1. An impact sample with magnitude above the threshold.
2. A stillness period after the impact exceeding the
   threshold, suggesting the subject did not get up.

A high-magnitude impact alone is NOT a fall candidate — it
may be a dropped object or a door slam. Post-impact
stillness is the differentiator. The library reports impact
candidates in three bands:

- ``none``      — below impact threshold.
- ``borderline``— impact above threshold but stillness
  inconclusive (caregiver should check in).
- ``candidate`` — both impact and stillness clear the bands.

The library NEVER reports a "confirmed fall" — a fall is a
clinical event, not a signal classification.
"""

from __future__ import annotations

from typing import Iterable, Literal

from ..core.models import ImpactSample


FallBand = Literal["none", "borderline", "candidate"]


def classify_impact(
    sample: ImpactSample,
    impact_threshold_g: float,
    stillness_threshold_s: float,
) -> FallBand:
    """Return the fall band for one impact sample."""
    if sample.magnitude_g < impact_threshold_g:
        return "none"
    if sample.stillness_after_s < stillness_threshold_s:
        return "borderline"
    return "candidate"


def compute_fall_risk(
    samples: Iterable[ImpactSample],
    impact_threshold_g: float = 2.0,
    stillness_threshold_s: float = 8.0,
) -> tuple[float, FallBand]:
    """Return ``(fall_risk_score, worst_band)`` over the window.

    fall_risk_score is in [0, 1]: 0 = no impact of note,
    intermediate for borderline, 1 for a clear candidate.
    The library reads the worst band seen in the window —
    any single candidate dominates the score.
    """
    worst: FallBand = "none"
    max_magnitude = 0.0
    max_stillness = 0.0
    for s in samples:
        band = classify_impact(s, impact_threshold_g, stillness_threshold_s)
        if _band_rank(band) > _band_rank(worst):
            worst = band
        if s.magnitude_g > max_magnitude:
            max_magnitude = s.magnitude_g
        if s.stillness_after_s > max_stillness:
            max_stillness = s.stillness_after_s

    if worst == "candidate":
        return 1.0, worst
    if worst == "borderline":
        # Partial credit scaled by how close the stillness is
        # to the threshold.
        frac = min(1.0, max_stillness / stillness_threshold_s)
        return max(0.0, min(1.0, 0.4 + 0.4 * frac)), worst
    return 0.0, worst


def _band_rank(band: FallBand) -> int:
    return {"none": 0, "borderline": 1, "candidate": 2}[band]
