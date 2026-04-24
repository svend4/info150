"""Deterministic synthetic mass-casualty incident generator.

No real disaster footage exists ethically at scale — simulated-
exercise data is the primary calibration source. This module
builds a fixed, reproducible population of casualties across the
START tag mix a typical earthquake-scale incident produces (see
Bar-El et al. 2007 for empirical ratios; implementation here is
stylised for demo / test use, not calibrated against any dataset).

Reproducibility: the same ``seed`` always produces the same
casualties — critical for test determinism.
"""

from __future__ import annotations

import random
from typing import Literal

from ..core.models import CivilianCasualty, VitalSignsObservation


ProfileKind = Literal[
    "minor_adult",
    "delayed_adult",
    "immediate_adult_rr",
    "immediate_adult_perfusion",
    "deceased_adult",
    "minor_pediatric",
    "immediate_pediatric_rr",
]


def _profile_vitals(
    profile: ProfileKind,
    rng: random.Random,
) -> VitalSignsObservation:
    """Build vitals matching a named casualty profile."""
    if profile == "minor_adult":
        return VitalSignsObservation(
            can_walk=True,
            respiratory_bpm=round(16 + rng.uniform(-2, 4), 1),
            airway_repositioned=False,
            capillary_refill_s=round(rng.uniform(0.8, 1.5), 1),
            radial_pulse=True,
            follows_commands=True,
        )
    if profile == "delayed_adult":
        return VitalSignsObservation(
            can_walk=False,
            respiratory_bpm=round(20 + rng.uniform(-4, 6), 1),
            airway_repositioned=False,
            capillary_refill_s=round(rng.uniform(1.0, 1.8), 1),
            radial_pulse=True,
            follows_commands=True,
        )
    if profile == "immediate_adult_rr":
        return VitalSignsObservation(
            can_walk=False,
            respiratory_bpm=round(34 + rng.uniform(-2, 8), 1),
            airway_repositioned=False,
            capillary_refill_s=round(rng.uniform(1.0, 1.8), 1),
            radial_pulse=True,
            follows_commands=True,
        )
    if profile == "immediate_adult_perfusion":
        return VitalSignsObservation(
            can_walk=False,
            respiratory_bpm=round(24 + rng.uniform(-4, 4), 1),
            airway_repositioned=False,
            capillary_refill_s=round(3.0 + rng.uniform(0, 2.0), 1),
            radial_pulse=True,
            follows_commands=True,
        )
    if profile == "deceased_adult":
        return VitalSignsObservation(
            can_walk=False,
            respiratory_bpm=None,
            airway_repositioned=True,
            capillary_refill_s=None,
            radial_pulse=False,
            follows_commands=False,
        )
    if profile == "minor_pediatric":
        return VitalSignsObservation(
            can_walk=True,
            respiratory_bpm=round(25 + rng.uniform(-3, 5), 1),
            airway_repositioned=False,
            capillary_refill_s=round(rng.uniform(0.8, 1.5), 1),
            radial_pulse=True,
            follows_commands=True,
        )
    # immediate_pediatric_rr — out-of-band respiratory rate for a child.
    return VitalSignsObservation(
        can_walk=False,
        respiratory_bpm=round(50 + rng.uniform(0, 8), 1),
        airway_repositioned=False,
        capillary_refill_s=round(rng.uniform(1.0, 1.8), 1),
        radial_pulse=True,
        follows_commands=True,
    )


def generate_casualty(
    casualty_id: str,
    profile: ProfileKind,
    seed: int = 0,
    age_years: float | None = None,
) -> CivilianCasualty:
    """Build one casualty matching the named profile."""
    rng = random.Random(hash((casualty_id, profile, seed)) & 0xFFFFFFFF)
    vitals = _profile_vitals(profile, rng)

    # Default age inferred from profile, but caller can override.
    if age_years is None:
        if profile.endswith("_pediatric") or profile.startswith("immediate_pediatric"):
            age_years = round(rng.uniform(2, 7), 0)
        else:
            age_years = round(rng.uniform(20, 60), 0)

    return CivilianCasualty(
        casualty_id=casualty_id,
        age_years=age_years,
        vitals=vitals,
    )


def demo_incident(
    incident_id: str = "DEMO_INCIDENT",
    seed: int = 0,
) -> list[CivilianCasualty]:
    """Build a demo incident — roughly earthquake-scale triage mix.

    Ratios are stylised: ~50 % minor (walking-wounded dominate
    every real incident), ~20 % delayed, ~20 % immediate, ~10 %
    deceased. Emits ten casualties — enough to exercise every
    protocol branch without being so large the demo output
    overflows a terminal.
    """
    mix: list[tuple[str, ProfileKind, float | None]] = [
        (f"{incident_id}-001", "minor_adult", None),
        (f"{incident_id}-002", "minor_adult", None),
        (f"{incident_id}-003", "minor_adult", None),
        (f"{incident_id}-004", "minor_pediatric", 5),
        (f"{incident_id}-005", "minor_pediatric", 7),
        (f"{incident_id}-006", "delayed_adult", None),
        (f"{incident_id}-007", "delayed_adult", None),
        (f"{incident_id}-008", "immediate_adult_rr", None),
        (f"{incident_id}-009", "immediate_adult_perfusion", None),
        (f"{incident_id}-010", "immediate_pediatric_rr", 4),
        (f"{incident_id}-011", "deceased_adult", None),
    ]
    return [
        generate_casualty(cid, profile, seed=seed + i, age_years=age)
        for i, (cid, profile, age) in enumerate(mix)
    ]
