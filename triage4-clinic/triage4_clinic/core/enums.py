"""String-literal enums for the telemedicine-pre-screening domain."""

from __future__ import annotations

from typing import Literal


# Escalation recommendation for the reviewing clinician.
# Deliberately no "emergency" tier — that's a clinician
# call, not a pre-screening call.
EscalationRecommendation = Literal[
    "self_care",
    "schedule",
    "urgent_review",
]


# Channel this reading / alert came from.
ChannelKind = Literal[
    "cardiac",
    "respiratory",
    "acoustic",
    "postural",
    "reporting",
]


# Relative strength of an alternative explanation the
# library attaches to an alert. Three qualitative tiers —
# deliberately non-numeric, because quantitative likelihoods
# in a pre-screening tool produce the diagnostic-illusion
# risk the grounded-alternatives pattern exists to prevent.
ExplanationLikelihood = Literal["possible", "plausible", "likely"]


# Capture-quality meta the consumer app reports. Poor
# capture blends the signature channels toward neutral —
# when the library can't see or hear clearly, it defaults
# back to `schedule` rather than producing a confident
# call either way.
CaptureQuality = Literal["good", "noisy", "partial"]


VALID_ESCALATIONS: tuple[EscalationRecommendation, ...] = (
    "self_care",
    "schedule",
    "urgent_review",
)
VALID_CHANNEL_KINDS: tuple[ChannelKind, ...] = (
    "cardiac",
    "respiratory",
    "acoustic",
    "postural",
    "reporting",
)
VALID_LIKELIHOODS: tuple[ExplanationLikelihood, ...] = (
    "possible",
    "plausible",
    "likely",
)
VALID_CAPTURE_QUALITIES: tuple[CaptureQuality, ...] = (
    "good",
    "noisy",
    "partial",
)
