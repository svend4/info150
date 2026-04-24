"""Per-species welfare scoring profiles.

Each profile captures:
- Which bilateral joint pairs the lameness signature reads.
- Welfare-flag thresholds for the overall score (concern /
  urgent).
- Per-channel minor / severe cue thresholds.

Thresholds are stubs drawn from general dairy / swine / poultry
welfare-assessment literature (AHDB Mobility Score for dairy,
EFSA 2009 Scientific Opinion on pig welfare, RSPCA broiler
welfare outcomes). They are NOT calibrated against farm data —
treat them as placeholders until a paired-deployment study
lands.

See docs/PHILOSOPHY.md — these thresholds influence WHEN an
alert surfaces, never WHAT treatment to recommend.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.enums import Species


@dataclass(frozen=True)
class SpeciesProfile:
    """Scoring / alert thresholds for one species."""

    species: Species
    # Bilateral joint pairs the lameness signature reads. Empty
    # tuple means "lameness is not a primary channel for this
    # species" (e.g. chickens — gait is assessed but not via
    # left/right hock asymmetry alone).
    lameness_pairs: tuple[tuple[str, str], ...]
    # Overall score thresholds that map continuous score → flag.
    # flag = "urgent" below urgent_threshold,
    # "concern" below concern_threshold, else "well".
    urgent_threshold: float
    concern_threshold: float
    # Per-channel thresholds for surfacing an alert at each flag.
    lameness_concern: float
    lameness_urgent: float
    respiratory_concern: float
    respiratory_urgent: float
    thermal_concern: float
    thermal_urgent: float


DAIRY_COW = SpeciesProfile(
    species="dairy_cow",
    lameness_pairs=(
        ("hock_l", "hock_r"),
        ("fetlock_l", "fetlock_r"),
        ("hoof_l", "hoof_r"),
    ),
    urgent_threshold=0.45,
    concern_threshold=0.70,
    lameness_concern=0.70,
    lameness_urgent=0.45,
    respiratory_concern=0.70,
    respiratory_urgent=0.40,
    thermal_concern=0.70,
    thermal_urgent=0.40,
)

PIG = SpeciesProfile(
    species="pig",
    lameness_pairs=(
        ("hock_l", "hock_r"),
        ("hoof_l", "hoof_r"),
    ),
    urgent_threshold=0.45,
    concern_threshold=0.70,
    lameness_concern=0.70,
    lameness_urgent=0.45,
    respiratory_concern=0.70,
    respiratory_urgent=0.40,
    thermal_concern=0.70,
    thermal_urgent=0.40,
)

CHICKEN = SpeciesProfile(
    species="chicken",
    # Chickens: primary lameness indicator is gait *cadence* and
    # keel-vs-shank asymmetry, not left/right hock offset. Empty
    # pair set here means the welfare engine will fall back to a
    # neutral 1.0 score for the lameness channel and rely on
    # respiratory + thermal + the stockperson note. A future
    # chicken-specific signature would live next to
    # lameness_gait.py as lameness_gait_avian.py.
    lameness_pairs=(),
    urgent_threshold=0.45,
    concern_threshold=0.70,
    lameness_concern=0.70,
    lameness_urgent=0.45,
    respiratory_concern=0.70,
    respiratory_urgent=0.40,
    thermal_concern=0.70,
    thermal_urgent=0.40,
)


_REGISTRY: dict[Species, SpeciesProfile] = {
    "dairy_cow": DAIRY_COW,
    "pig": PIG,
    "chicken": CHICKEN,
}


def profile_for(species: Species) -> SpeciesProfile:
    if species not in _REGISTRY:
        raise KeyError(f"no profile for species {species!r}")
    return _REGISTRY[species]
