"""String-literal enums for the sports-performance domain."""

from __future__ import annotations

from typing import Literal


# Sports the library has reference profiles for. A "general"
# category covers anything the consumer app hasn't categorised.
Sport = Literal[
    "soccer",
    "basketball",
    "tennis",
    "baseball",
    "sprint",
    "swim",
    "general",
]


# Risk band the engine surfaces. NOT a clinical severity —
# "hold" means "trainer should consider holding the athlete
# from the next high-load session", NOT "clinical clearance
# withheld".
RiskBand = Literal["steady", "monitor", "hold"]


ChannelKind = Literal[
    "form_asymmetry",
    "workload_load",
    "recovery_hr",
    "baseline_deviation",
    "calibration",
]


# Sport-specific movement labels. Each ``MovementSample`` is
# tagged with its kind so the engine can apply per-movement
# baselines.
MovementKind = Literal[
    "kick",
    "throw",
    "serve",
    "stride",
    "jump",
    "stroke",
    "general",
]


VALID_SPORTS: tuple[Sport, ...] = (
    "soccer", "basketball", "tennis", "baseball",
    "sprint", "swim", "general",
)
VALID_RISK_BANDS: tuple[RiskBand, ...] = ("steady", "monitor", "hold")
VALID_CHANNEL_KINDS: tuple[ChannelKind, ...] = (
    "form_asymmetry",
    "workload_load",
    "recovery_hr",
    "baseline_deviation",
    "calibration",
)
VALID_MOVEMENT_KINDS: tuple[MovementKind, ...] = (
    "kick", "throw", "serve", "stride", "jump", "stroke", "general",
)
