"""Acoustic-strain signature — vocal strain from sustained 'aah'.

Mean strain across acoustic samples, weighted by clarity
(low-clarity samples count less). Returns score + grounded
alternatives.
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import (
    AcousticSample,
    AlternativeExplanation,
    ChannelReading,
)


SIGNATURE_VERSION = "acoustic_strain@1.0.0"


def compute_acoustic(
    samples: Iterable[AcousticSample],
) -> tuple[ChannelReading, tuple[AlternativeExplanation, ...]]:
    """Return acoustic-strain reading + grounded alternatives."""
    sample_list = [s for s in samples if s.clarity >= 0.3]
    if not sample_list:
        return (
            ChannelReading(
                channel="acoustic",
                value=1.0,
                signature_version=SIGNATURE_VERSION,
            ),
            (),
        )

    # Clarity-weighted mean of 1 - strain_score (so safety
    # stays consistent: 1.0 = low strain).
    weighted_safety = 0.0
    total_weight = 0.0
    for s in sample_list:
        weight = s.clarity
        weighted_safety += weight * (1.0 - s.strain_score)
        total_weight += weight
    if total_weight == 0:
        score = 1.0
    else:
        score = max(0.0, min(1.0, weighted_safety / total_weight))

    reading = ChannelReading(
        channel="acoustic",
        value=round(score, 3),
        signature_version=SIGNATURE_VERSION,
    )

    alts: list[AlternativeExplanation] = []
    if score < 0.7:
        alts.extend([
            AlternativeExplanation(
                text="Could reflect recent voice overuse or dehydration "
                     "rather than an underlying clinical finding.",
                likelihood="plausible",
            ),
            AlternativeExplanation(
                text="Could reflect a mild upper-respiratory irritation "
                     "that self-resolves in a few days.",
                likelihood="plausible",
            ),
            AlternativeExplanation(
                text="Could reflect a vocal-tract or airway finding a "
                     "clinical exam can evaluate.",
                likelihood="possible",
            ),
        ])

    return reading, tuple(alts)
