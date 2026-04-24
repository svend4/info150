"""Post-set recovery quality from HR / breathing-rate.

Mirrors the triage4 ``UncertaintyModel`` confidence-aggregation
idea but with a very different meaning — here the output rates
how well the trainee recovered between sets, which informs the
"consider resting longer" cue.

Wellness framing note: this is a RECOVERY QUALITY score, not a
health status. A low recovery score suggests the trainee take
more rest before the next set. It does NOT diagnose fitness
level, cardiovascular health, or any medical condition.
"""

from __future__ import annotations


# Resting-range benchmarks (per minute) for a general adult
# population. These are reference bands, not clinical cut-offs.
# Customise via per-trainee baseline in a future iteration.
_RESTING_HR_BAND = (55, 75)
_RESTING_BREATHING_BAND = (10, 18)

# "Elevated but acceptable" caps — above these means the trainee
# is still clearly mid-recovery; the cue layer flags rest.
_ELEVATED_HR_CAP = 110
_ELEVATED_BREATHING_CAP = 30


def _band_score(value: float, band: tuple[float, float], cap: float) -> float:
    """Map a measurement to [0, 1]: 1.0 if inside the resting band,
    linearly decaying to 0 at ``cap`` and above.
    """
    lo, hi = band
    if value <= hi:
        if value >= lo:
            return 1.0
        # Below the resting band (rare, but possible for a very
        # conditioned athlete) — still a healthy recovery.
        return 1.0
    if value >= cap:
        return 0.0
    return 1.0 - (value - hi) / (cap - hi)


def estimate_recovery_quality(
    post_set_hr: float | None,
    post_set_breathing: float | None,
) -> float | None:
    """Return a recovery score in [0, 1] from post-set vitals.

    Returns ``None`` when neither HR nor breathing rate are
    provided — the caller (typically ``RapidFormEngine``) skips
    the recovery cue in that case rather than fabricating a
    score.
    """
    scores: list[float] = []
    if post_set_hr is not None:
        scores.append(
            _band_score(float(post_set_hr), _RESTING_HR_BAND, _ELEVATED_HR_CAP)
        )
    if post_set_breathing is not None:
        scores.append(
            _band_score(
                float(post_set_breathing),
                _RESTING_BREATHING_BAND,
                _ELEVATED_BREATHING_CAP,
            )
        )
    if not scores:
        return None
    # Weighted equally — both channels carry similar information.
    return sum(scores) / len(scores)
