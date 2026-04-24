"""Per-species engine-level tuning.

Signatures already carry species-specific thresholds inside
their own modules; this file adds engine-level tuning that
varies per species — e.g. how aggressively to recommend a
same-day visit for a cat with a given respiratory score vs.
a horse with the same score (cats hide distress, so the
library escalates faster for cats).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.enums import SpeciesKind


@dataclass(frozen=True)
class SpeciesProfile:
    """Engine-level tuning per species."""

    species: SpeciesKind
    # Overall-score threshold that maps to "see_today".
    # Lower (more conservative) for species that hide pain
    # aggressively.
    see_today_threshold: float
    # Overall-score threshold that maps to "routine_visit".
    routine_visit_threshold: float
    # When to emit a panting-at-rest-specific owner
    # message. Dogs pant more freely than cats, so dog
    # threshold is higher (more confident) before firing.
    panting_alert_fraction: float


DOG = SpeciesProfile(
    species="dog",
    see_today_threshold=0.45,
    routine_visit_threshold=0.75,
    panting_alert_fraction=0.35,
)
CAT = SpeciesProfile(
    species="cat",
    # Cats hide pain aggressively — any signal deserves a
    # same-day escalation earlier than for dogs.
    see_today_threshold=0.55,
    routine_visit_threshold=0.80,
    panting_alert_fraction=0.20,
)
HORSE = SpeciesProfile(
    species="horse",
    see_today_threshold=0.40,
    routine_visit_threshold=0.70,
    panting_alert_fraction=0.30,
)
RABBIT = SpeciesProfile(
    species="rabbit",
    # Rabbits are prey animals and mask illness severely —
    # same-day threshold is the most conservative in the
    # library.
    see_today_threshold=0.60,
    routine_visit_threshold=0.85,
    panting_alert_fraction=0.25,
)


_REGISTRY: dict[SpeciesKind, SpeciesProfile] = {
    "dog": DOG,
    "cat": CAT,
    "horse": HORSE,
    "rabbit": RABBIT,
}


def profile_for(species: SpeciesKind) -> SpeciesProfile:
    if species not in _REGISTRY:
        raise KeyError(f"no profile for species {species!r}")
    return _REGISTRY[species]
