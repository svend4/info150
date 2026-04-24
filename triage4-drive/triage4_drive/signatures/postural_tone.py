"""Postural-tone score — head-drop / slumping detection.

Sudden incapacitation (syncope, medical event) is the rarest
but most consequential signal this library reads. The tell is
loss of postural tone: the head falls forward / to the side
faster than a normal relaxation posture allows.

Signature reads the vertical gap between nose and
shoulder-midline keypoints across the window:
- Small gap, steady = upright driving.
- Growing gap over a short window = slumping.
- Growing gap + sustained ≥ ``incapacitation_hold_s`` =
  incapacitation candidate.

Returns a score in [0, 1] where 0.0 = textbook upright posture
and 1.0 = clear slump-and-hold pattern. The engine combines
this with eye-closure and gaze signals — a single-signature
incapacitation call never happens in isolation.
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import PostureSample


# If the nose sits this far below the shoulder midline, the
# driver has effectively lost postural tone. 0.15 ≈ 15 % of
# the normalised image height — conservative to avoid false
# positives on steering-wheel leans.
_SEVERE_DROP = 0.15
_MILD_DROP = 0.05

# Minimum time a slumped posture must be held to count.
DEFAULT_INCAPACITATION_HOLD_S = 2.0


def compute_postural_tone_score(
    samples: Iterable[PostureSample],
    incapacitation_hold_s: float = DEFAULT_INCAPACITATION_HOLD_S,
) -> float:
    """Return an incapacitation-risk score in [0, 1].

    0.0 = upright throughout. 1.0 = severe head-drop held
    longer than ``incapacitation_hold_s``. Intermediate values
    scale linearly with the held duration.
    """
    sample_list = sorted(samples, key=lambda s: s.t_s)
    if len(sample_list) < 2:
        return 0.0

    # Compute per-sample "drop" = nose_y - shoulder_midline_y.
    # Positive drop = nose is BELOW shoulders (image coords
    # have y growing downward), which is the slumped state.
    drops = [(s.t_s, s.nose_y - s.shoulder_midline_y) for s in sample_list]

    # Find the longest run of consecutive drops above the
    # severe threshold.
    longest_severe_s = _longest_run_above(drops, _SEVERE_DROP)
    if longest_severe_s >= incapacitation_hold_s:
        return 1.0

    # Partial credit for sustained severe drop shorter than
    # the hold threshold.
    severe_frac = min(1.0, longest_severe_s / incapacitation_hold_s)

    # And partial credit for sustained mild drops — suggestive
    # of the onset phase.
    longest_mild_s = _longest_run_above(drops, _MILD_DROP)
    total_s = sample_list[-1].t_s - sample_list[0].t_s
    mild_frac = 0.0
    if total_s > 0:
        mild_frac = min(1.0, longest_mild_s / total_s)

    # Severe dominates; mild adds at most ~0.3 to the score.
    return max(0.0, min(1.0, severe_frac * 0.7 + mild_frac * 0.3))


def _longest_run_above(
    drops: list[tuple[float, float]],
    threshold: float,
) -> float:
    longest = 0.0
    run_start: float | None = None
    for t, d in drops:
        if d >= threshold:
            if run_start is None:
                run_start = t
        else:
            if run_start is not None:
                longest = max(longest, t - run_start)
                run_start = None
    if run_start is not None:
        longest = max(longest, drops[-1][0] - run_start)
    return longest
