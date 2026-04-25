"""String-literal enums for the avian-wildlife domain."""

from __future__ import annotations

from typing import Literal


# Common bird species the library has reference acoustic
# bands for. Upstream BirdNET-class classifier produces
# species labels; unknown species fall through to a
# generic profile.
Species = Literal[
    "mallard",
    "robin",
    "sparrow",
    "raven",
    "hawk",
    "finch",
    "swift",
    "unknown",
]


AlertLevel = Literal["ok", "watch", "urgent"]


AlertKind = Literal[
    "call_presence",
    "distress",
    "vitals",
    "thermal",
    "mortality_cluster",
    "calibration",
]


# Coarse call-kind classifier output. ``song`` = territorial
# / mate calls; ``chip`` = contact / location calls; ``alarm``
# = predator-warning calls; ``distress`` = injury / capture
# vocalisations.
CallKind = Literal["song", "chip", "alarm", "distress"]


VALID_SPECIES: tuple[Species, ...] = (
    "mallard",
    "robin",
    "sparrow",
    "raven",
    "hawk",
    "finch",
    "swift",
    "unknown",
)
VALID_ALERT_LEVELS: tuple[AlertLevel, ...] = ("ok", "watch", "urgent")
VALID_ALERT_KINDS: tuple[AlertKind, ...] = (
    "call_presence",
    "distress",
    "vitals",
    "thermal",
    "mortality_cluster",
    "calibration",
)
VALID_CALL_KINDS: tuple[CallKind, ...] = (
    "song",
    "chip",
    "alarm",
    "distress",
)


# SMS-length cap for ornithologist alerts. Inherits the
# constraint from triage4-wild — ranger / ornithologist
# handoff often runs over the same Iridium satcom path.
MAX_AVIAN_SMS_CHARS: int = 200
