"""Instinctive Drowning Response (IDR) posture signature.

Wiki 2010 / Pia 2006 identify the IDR pattern — a silent,
vertical, head-low posture — as the dominant visual signature
of drowning. Contrary to popular expectation, IDR does NOT
involve shouting or rhythmic splashing; the response is
mute and brief (typically 20-60 s above water before
submersion).

The signature reads three surface-sample channels:
- ``body_vertical`` — high when the swimmer's torso is
  upright in the water (IDR-like).
- ``head_height_rel`` — low when the head is near the
  water line.
- ``motion_rhythm`` — low when splashing is non-rhythmic
  (flailing, not swim strokes).

When all three are in their risk bands simultaneously over
a non-trivial fraction of the window, that's the IDR
signature.

Returns a unit-interval safety score. 1.0 = no IDR
pattern; 0.0 = clear IDR for the majority of the window.
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import SurfacePoseSample


# Per-sample risk band cut-offs. body_vertical above cut →
# vertical; head_height_rel below cut → head low;
# motion_rhythm below cut → non-rhythmic.
_VERTICAL_RISK = 0.70
_HEAD_LOW_RISK = 0.30
_NON_RHYTHMIC_RISK = 0.30


def _is_idr_sample(sample: SurfacePoseSample) -> bool:
    return (
        sample.body_vertical >= _VERTICAL_RISK
        and sample.head_height_rel <= _HEAD_LOW_RISK
        and sample.motion_rhythm <= _NON_RHYTHMIC_RISK
    )


def compute_idr_safety(
    samples: Iterable[SurfacePoseSample],
) -> float:
    """Return IDR safety score in [0, 1]."""
    sample_list = list(samples)
    if not sample_list:
        return 1.0

    idr_count = sum(1 for s in sample_list if _is_idr_sample(s))
    idr_fraction = idr_count / len(sample_list)

    # Any IDR samples matter — IDR is brief but high-
    # information. Score drops fast with fraction.
    # fraction 0.0  → 1.0
    # fraction 0.25 → ~0.25
    # fraction 0.5  → 0.0
    if idr_fraction == 0:
        return 1.0
    return max(0.0, min(1.0, 1.0 - idr_fraction * 2.0))
