"""Cardiac-readings signature.

Scores adult HR against a reference resting band and, when
elevated, produces a tuple of grounded alternative
explanations for the engine to attach to any emitted
ClinicianAlert.

Returns a pair ``(ChannelReading, tuple[AlternativeExplanation, ...])``.
The engine decides whether the reading warrants an alert;
this signature produces both the numeric score AND the
alternatives that would accompany an alert in one call,
keeping the audit trail tight.
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import (
    AlternativeExplanation,
    ChannelReading,
    VitalsSample,
)


SIGNATURE_VERSION = "cardiac_readings@1.0.0"


# Adult reference band for stand-off resting HR. Literature
# consensus sits around 60-100 bpm for healthy adults at
# rest.
_RESTING_LOW = 60.0
_RESTING_HIGH = 100.0
_HIGH_CAP = 140.0
_LOW_CAP = 40.0


def compute_cardiac(
    samples: Iterable[VitalsSample],
) -> tuple[ChannelReading, tuple[AlternativeExplanation, ...]]:
    """Return the cardiac reading + grounded alternatives.

    Score in [0, 1], 1.0 = HR in the resting band (or no
    reliable samples). 0.0 = HR at / above ``_HIGH_CAP`` or
    at / below ``_LOW_CAP``.
    """
    reliable = [s for s in samples if s.reliable]
    if not reliable:
        # No reliable vitals — neutral score. Engine's
        # calibration logic handles missing-channel cues.
        return (
            ChannelReading(
                channel="cardiac",
                value=1.0,
                signature_version=SIGNATURE_VERSION,
            ),
            (),
        )

    sorted_hrs = sorted(s.hr_bpm for s in reliable)
    mid = len(sorted_hrs) // 2
    if len(sorted_hrs) % 2:
        median = sorted_hrs[mid]
    else:
        median = (sorted_hrs[mid - 1] + sorted_hrs[mid]) / 2

    if _RESTING_LOW <= median <= _RESTING_HIGH:
        score = 1.0
    elif median >= _HIGH_CAP:
        score = 0.0
    elif median <= _LOW_CAP:
        score = 0.0
    elif median > _RESTING_HIGH:
        score = max(0.0, 1.0 - (median - _RESTING_HIGH) / (_HIGH_CAP - _RESTING_HIGH))
    else:
        score = max(0.0, 1.0 - (_RESTING_LOW - median) / (_RESTING_LOW - _LOW_CAP))

    reading = ChannelReading(
        channel="cardiac",
        value=round(score, 3),
        signature_version=SIGNATURE_VERSION,
    )

    # Build grounded alternatives. Every alert that fires
    # against this channel inherits a baseline set of
    # alternatives — the engine may add more if other
    # channels co-fire.
    alts: list[AlternativeExplanation] = []
    if median > _RESTING_HIGH:
        alts.extend([
            AlternativeExplanation(
                text="Could reflect recent physical exertion or a "
                     "stressful event shortly before the recording.",
                likelihood="plausible",
            ),
            AlternativeExplanation(
                text="Could reflect heightened anxiety state during "
                     "the self-report capture itself.",
                likelihood="plausible",
            ),
            AlternativeExplanation(
                text="Could reflect a cardiac finding that a clinical "
                     "exam can evaluate.",
                likelihood="possible",
            ),
        ])
    elif median < _RESTING_LOW:
        alts.extend([
            AlternativeExplanation(
                text="Could reflect aerobic fitness — trained athletes "
                     "commonly sit below the general-population band.",
                likelihood="plausible",
            ),
            AlternativeExplanation(
                text="Could reflect medication effect (beta blockers, "
                     "calcium-channel blockers) worth noting in review.",
                likelihood="plausible",
            ),
            AlternativeExplanation(
                text="Could reflect a cardiac finding that a clinical "
                     "exam can evaluate.",
                likelihood="possible",
            ),
        ])

    return reading, tuple(alts)
