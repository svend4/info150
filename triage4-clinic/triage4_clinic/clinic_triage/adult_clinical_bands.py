"""Adult clinical-threshold bands.

Engine-level overall-score thresholds that map the fused
channel score into an ``EscalationRecommendation``. Bands
are deliberately conservative — default-to-schedule
behaviour when uncertain.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdultClinicalBands:
    """Engine thresholds for the telemedicine pre-screening pass."""

    # Per-channel alert thresholds. Below these, the engine
    # fires an alert on that channel.
    channel_schedule: float = 0.75
    channel_urgent: float = 0.45

    # Overall-score → recommendation tier thresholds.
    # NOTE: the default is `schedule`, not `self_care`.
    # self_care only fires when every channel is well
    # within its safety band.
    overall_self_care: float = 0.90
    overall_urgent: float = 0.55


DEFAULT_BANDS = AdultClinicalBands()
