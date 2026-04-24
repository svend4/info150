"""Unsafe-lifting-posture signature.

Back-hip flexion angle at peak lift is the canonical signal
for unsafe lifts (NIOSH Lifting Equation, 1994; OSHA
Ergonomics guidelines). Safe lifts stay below ~30° flexion
even at peak load; unsafe lifts reach 60° or more.

Returns a posture-safety score in [0, 1]: 1.0 = textbook-
safe lifts across the window, 0.0 = repeated deep flexion
at meaningful load.

NB: a steep back angle at zero load is a minor signal
(bending over to tie a shoelace); the signature scales by
load_kg so only loaded lifts contribute meaningfully.
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import LiftingSample


# Flexion bands (degrees). Below safe_cap is fine; between
# safe and unsafe caps is marginal; above unsafe_cap is the
# unsafe-lift signal.
_SAFE_CAP_DEG = 30.0
_UNSAFE_CAP_DEG = 60.0

# Loaded-lift mass threshold — below this the lift is
# treated as effectively unloaded and doesn't contribute
# to the score.
_LOAD_SENSITIVITY_KG = 5.0


def compute_lifting_safety(
    samples: Iterable[LiftingSample],
) -> float:
    """Return the lifting-safety score in [0, 1].

    With no loaded lifts in the window, the score is 1.0.
    """
    sample_list = list(samples)
    if not sample_list:
        return 1.0

    per_sample_safety: list[tuple[float, float]] = []
    for s in sample_list:
        weight = min(1.0, s.load_kg / _LOAD_SENSITIVITY_KG)
        if weight <= 0:
            continue
        if s.back_angle_deg <= _SAFE_CAP_DEG:
            sample_safety = 1.0
        elif s.back_angle_deg >= _UNSAFE_CAP_DEG:
            sample_safety = 0.0
        else:
            span = _UNSAFE_CAP_DEG - _SAFE_CAP_DEG
            sample_safety = 1.0 - (s.back_angle_deg - _SAFE_CAP_DEG) / span
        per_sample_safety.append((weight, sample_safety))

    if not per_sample_safety:
        return 1.0

    # Weighted average — heavy-load unsafe lifts dominate
    # the score over many empty-handed deep-flexion samples.
    total_w = sum(w for w, _ in per_sample_safety)
    return max(0.0, min(1.0, sum(w * v for w, v in per_sample_safety) / total_w))
