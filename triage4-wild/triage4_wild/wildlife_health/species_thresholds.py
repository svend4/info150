"""Per-species engine-level tuning.

Wildlife species differ in how quickly a visible signal
becomes an urgent finding: rhinos + elephants are
high-value conservation subjects where even mild signals
warrant escalation, prey species (buffalo, zebra) show
more natural injury patterns from predation-pressure and
scale back escalation thresholds, lions / cheetahs sit
somewhere between.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.enums import Species


@dataclass(frozen=True)
class SpeciesProfile:
    """Engine tuning per species."""

    species: Species
    overall_urgent_threshold: float
    overall_watch_threshold: float
    # If True, the engine applies a +10 % escalation bias
    # when upstream threat_signals fire — high-value
    # conservation subjects (rhino, elephant) see faster
    # escalation on snare / horn / tusk flags.
    high_value_escalation: bool


_REGISTRY: dict[Species, SpeciesProfile] = {
    "elephant": SpeciesProfile(
        species="elephant",
        overall_urgent_threshold=0.55,
        overall_watch_threshold=0.75,
        high_value_escalation=True,
    ),
    "rhino": SpeciesProfile(
        species="rhino",
        overall_urgent_threshold=0.60,
        overall_watch_threshold=0.80,
        high_value_escalation=True,
    ),
    "lion": SpeciesProfile(
        species="lion",
        overall_urgent_threshold=0.45,
        overall_watch_threshold=0.70,
        high_value_escalation=False,
    ),
    "buffalo": SpeciesProfile(
        species="buffalo",
        overall_urgent_threshold=0.40,
        overall_watch_threshold=0.65,
        high_value_escalation=False,
    ),
    "giraffe": SpeciesProfile(
        species="giraffe",
        overall_urgent_threshold=0.45,
        overall_watch_threshold=0.70,
        high_value_escalation=False,
    ),
    "zebra": SpeciesProfile(
        species="zebra",
        overall_urgent_threshold=0.40,
        overall_watch_threshold=0.65,
        high_value_escalation=False,
    ),
    "cheetah": SpeciesProfile(
        species="cheetah",
        overall_urgent_threshold=0.50,
        overall_watch_threshold=0.72,
        high_value_escalation=True,
    ),
    "unknown": SpeciesProfile(
        species="unknown",
        overall_urgent_threshold=0.45,
        overall_watch_threshold=0.70,
        high_value_escalation=False,
    ),
}


def profile_for(species: Species) -> SpeciesProfile:
    if species not in _REGISTRY:
        raise KeyError(f"no profile for species {species!r}")
    return _REGISTRY[species]
