"""Pain-behavior signature.

Scores confidence-weighted counts of species-specific pain-
behavior observations. A dog panting at rest and tucking
its tail is a much stronger pain signal than either alone;
the signature sums weighted behaviors across the window.

Per-species weights capture the relative diagnostic
strength of each behavior in that species' pain-assessment
literature (Glasgow Composite Pain Score for dogs, Feline
Grimace Scale for cats, Horse Grimace Scale for horses,
Rabbit Grimace Scale for rabbits). Weights sum to 1.0
within each species; a fully-weighted set of behaviors
drives the safety score to 0.
"""

from __future__ import annotations

from typing import Iterable

from ..core.enums import PainBehaviorKind, SpeciesKind
from ..core.models import PainBehaviorSample


_SPECIES_WEIGHTS: dict[SpeciesKind, dict[PainBehaviorKind, float]] = {
    "dog": {
        "panting_at_rest": 0.30,
        "hunched_posture": 0.25,
        "tucked_tail":     0.20,
        "hiding":          0.15,
        "weight_shifting": 0.10,
        # ear_position not a strong dog-pain signal — 0
    },
    "cat": {
        "hiding":          0.30,
        "ear_position":    0.25,
        "hunched_posture": 0.20,
        "panting_at_rest": 0.15,
        "weight_shifting": 0.10,
        # tucked_tail ambiguous in cats
    },
    "horse": {
        "weight_shifting": 0.35,
        "ear_position":    0.25,
        "hunched_posture": 0.20,
        "panting_at_rest": 0.15,
        "hiding":          0.05,
    },
    "rabbit": {
        "hiding":          0.30,
        "hunched_posture": 0.25,
        "ear_position":    0.20,
        "panting_at_rest": 0.15,
        "weight_shifting": 0.10,
    },
}


def compute_pain_safety(
    samples: Iterable[PainBehaviorSample],
    species: SpeciesKind,
) -> float:
    """Return pain safety score in [0, 1]."""
    sample_list = list(samples)
    if not sample_list:
        return 1.0
    if species not in _SPECIES_WEIGHTS:
        raise KeyError(f"no pain-behavior weights for species {species!r}")

    weights = _SPECIES_WEIGHTS[species]
    total_weight = 0.0
    seen_kinds: set[PainBehaviorKind] = set()
    for s in sample_list:
        weight = weights.get(s.kind, 0.0) * s.confidence
        # Each behavior kind counts at most once per
        # submission — multiple hiding observations don't
        # stack — matching how a vet reads a submission.
        if s.kind in seen_kinds:
            continue
        seen_kinds.add(s.kind)
        total_weight += weight

    return max(0.0, min(1.0, 1.0 - total_weight))
