"""Postural-stability signature — sway + balance steadiness."""

from __future__ import annotations

from typing import Iterable

from ..core.models import (
    AlternativeExplanation,
    ChannelReading,
    PostureSample,
)


SIGNATURE_VERSION = "postural_stability@1.0.0"


def compute_postural(
    samples: Iterable[PostureSample],
) -> tuple[ChannelReading, tuple[AlternativeExplanation, ...]]:
    """Return postural-stability reading + grounded alternatives."""
    sample_list = list(samples)
    if not sample_list:
        return (
            ChannelReading(
                channel="postural",
                value=1.0,
                signature_version=SIGNATURE_VERSION,
            ),
            (),
        )

    mean_sway = sum(s.sway_magnitude for s in sample_list) / len(sample_list)
    mean_steady = sum(s.balance_steadiness for s in sample_list) / len(sample_list)

    # Score: low sway + high steadiness = 1.0.
    score = max(0.0, min(1.0, (1.0 - mean_sway) * 0.5 + mean_steady * 0.5))

    reading = ChannelReading(
        channel="postural",
        value=round(score, 3),
        signature_version=SIGNATURE_VERSION,
    )

    alts: list[AlternativeExplanation] = []
    if score < 0.7:
        alts.extend([
            AlternativeExplanation(
                text="Could reflect general fatigue or recent poor "
                     "sleep rather than an underlying finding.",
                likelihood="plausible",
            ),
            AlternativeExplanation(
                text="Could reflect a vestibular (inner-ear) "
                     "disturbance — worth noting recent ear symptoms.",
                likelihood="possible",
            ),
            AlternativeExplanation(
                text="Could reflect a medication-related balance "
                     "side-effect — worth reviewing current "
                     "medications in the pre-consult.",
                likelihood="plausible",
            ),
        ])

    return reading, tuple(alts)
