"""Respiratory-readings signature.

Scores adult RR against the reference resting band and
combines with cough-frequency from the acoustic window.
Returns a score + grounded alternatives.
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import (
    AlternativeExplanation,
    ChannelReading,
    CoughSample,
    VitalsSample,
)


SIGNATURE_VERSION = "respiratory_readings@1.0.0"


# Adult reference band for stand-off RR — literature
# consensus 12-20 bpm at rest.
_RESTING_LOW = 12.0
_RESTING_HIGH = 20.0
_HIGH_CAP = 40.0
_LOW_CAP = 6.0

# Cough-frequency thresholds (counts per minute from the
# acoustic window). Any cough is noted; sustained cough
# frequency drives the score down.
_COUGH_PER_MIN_HIGH = 6.0


def compute_respiratory(
    vitals_samples: Iterable[VitalsSample],
    cough_samples: Iterable[CoughSample],
    window_duration_s: float,
) -> tuple[ChannelReading, tuple[AlternativeExplanation, ...]]:
    """Return respiratory reading + grounded alternatives."""
    reliable = [s for s in vitals_samples if s.reliable]

    # RR portion of the score.
    if not reliable:
        rr_score = 1.0
        median_rr: float | None = None
    else:
        sorted_rrs = sorted(s.rr_bpm for s in reliable)
        mid = len(sorted_rrs) // 2
        if len(sorted_rrs) % 2:
            median_rr = sorted_rrs[mid]
        else:
            median_rr = (sorted_rrs[mid - 1] + sorted_rrs[mid]) / 2
        if _RESTING_LOW <= median_rr <= _RESTING_HIGH:
            rr_score = 1.0
        elif median_rr >= _HIGH_CAP:
            rr_score = 0.0
        elif median_rr <= _LOW_CAP:
            rr_score = 0.0
        elif median_rr > _RESTING_HIGH:
            rr_score = max(0.0, 1.0 - (median_rr - _RESTING_HIGH) / (_HIGH_CAP - _RESTING_HIGH))
        else:
            rr_score = max(0.0, 1.0 - (_RESTING_LOW - median_rr) / (_RESTING_LOW - _LOW_CAP))

    # Cough portion.
    cough_list = [s for s in cough_samples if s.confidence >= 0.5]
    cough_count = len(cough_list)
    if window_duration_s > 0:
        cough_per_min = cough_count / (window_duration_s / 60.0)
    else:
        cough_per_min = 0.0
    if cough_per_min == 0:
        cough_score = 1.0
    elif cough_per_min >= _COUGH_PER_MIN_HIGH:
        cough_score = 0.0
    else:
        cough_score = max(0.0, 1.0 - cough_per_min / _COUGH_PER_MIN_HIGH)

    # Fuse: worst-of-two (either channel going low pulls
    # the composite down — a patient with normal RR but
    # persistent cough still warrants respiratory
    # attention).
    score = min(rr_score, cough_score)

    reading = ChannelReading(
        channel="respiratory",
        value=round(score, 3),
        signature_version=SIGNATURE_VERSION,
    )

    alts: list[AlternativeExplanation] = []
    if median_rr is not None and median_rr > _RESTING_HIGH:
        alts.append(AlternativeExplanation(
            text="Could reflect recent physical exertion affecting the "
                 "respiratory sample window.",
            likelihood="plausible",
        ))
        alts.append(AlternativeExplanation(
            text="Could reflect an anxiety or stress state during the "
                 "self-report capture.",
            likelihood="plausible",
        ))
        alts.append(AlternativeExplanation(
            text="Could reflect a lower-respiratory finding a clinical "
                 "exam can evaluate.",
            likelihood="possible",
        ))
    if cough_per_min >= 2.0:
        alts.append(AlternativeExplanation(
            text="Could reflect an upper-respiratory illness in its "
                 "early or resolving phase.",
            likelihood="plausible",
        ))
        alts.append(AlternativeExplanation(
            text="Could reflect an allergic or environmental irritant "
                 "response — worth noting seasonal context in review.",
            likelihood="plausible",
        ))
        alts.append(AlternativeExplanation(
            text="Could reflect a lower-respiratory finding a clinical "
                 "exam can evaluate.",
            likelihood="possible",
        ))

    return reading, tuple(alts)
