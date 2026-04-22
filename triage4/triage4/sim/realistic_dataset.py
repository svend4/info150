"""Richer synthetic triage dataset for calibration and benchmarking.

Part of Phase 9b. The ``sim/casualty_profiles.py`` helpers produce 3
neat archetypes (immediate / delayed / minimal) with clean signals.
That's fine for smoke tests but too easy for calibration — every
reasonable classifier scores 100%.

This module generates a **labelled synthetic dataset with edge cases**:

- isolated mortal signs (critical bleeding / posture / no breathing)
  without support from other channels;
- occluded observations (low visibility, partial data);
- mixed / ambiguous mid-range signals;
- degraded sensor readings via :mod:`triage4.sim.sensor_degradation`.

Used by :mod:`triage4.triage_reasoning.calibration` to fit weights and
thresholds, and by any future Phase 9c validation harness.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Literal

from triage4.core.models import CasualtySignature
from triage4.sim.sensor_degradation import (
    DegradationConfig,
    SensorDegradationSimulator,
)


Priority = Literal["immediate", "delayed", "minimal"]


@dataclass(frozen=True)
class LabelledCase:
    """One labelled synthetic casualty — signature plus ground-truth priority."""

    casualty_id: str
    signature: CasualtySignature
    priority: Priority
    trauma_kinds: frozenset[str]
    scenario_tag: str  # 'clean_immediate', 'isolated_bleeding', etc.


def _clean_immediate(rng: random.Random) -> CasualtySignature:
    return CasualtySignature(
        breathing_curve=[0.01, 0.02, 0.01, 0.02, 0.01, 0.02],
        chest_motion_fd=rng.uniform(0.05, 0.12),
        perfusion_drop_score=rng.uniform(0.75, 0.95),
        bleeding_visual_score=rng.uniform(0.85, 0.98),
        thermal_asymmetry_score=rng.uniform(0.40, 0.65),
        posture_instability_score=rng.uniform(0.65, 0.85),
        visibility_score=rng.uniform(0.85, 1.0),
    )


def _clean_delayed(rng: random.Random) -> CasualtySignature:
    return CasualtySignature(
        breathing_curve=[0.10, 0.13, 0.11, 0.14, 0.12, 0.13],
        chest_motion_fd=rng.uniform(0.15, 0.25),
        perfusion_drop_score=rng.uniform(0.40, 0.60),
        bleeding_visual_score=rng.uniform(0.30, 0.55),
        thermal_asymmetry_score=rng.uniform(0.15, 0.35),
        posture_instability_score=rng.uniform(0.35, 0.55),
        visibility_score=rng.uniform(0.80, 1.0),
    )


def _clean_minimal(rng: random.Random) -> CasualtySignature:
    return CasualtySignature(
        breathing_curve=[0.22, 0.26, 0.24, 0.27, 0.25, 0.28],
        chest_motion_fd=rng.uniform(0.25, 0.40),
        perfusion_drop_score=rng.uniform(0.10, 0.25),
        bleeding_visual_score=rng.uniform(0.05, 0.20),
        thermal_asymmetry_score=rng.uniform(0.05, 0.15),
        posture_instability_score=rng.uniform(0.05, 0.25),
        visibility_score=rng.uniform(0.85, 1.0),
    )


def _isolated_bleeding(rng: random.Random) -> CasualtySignature:
    # Everything quiet except a strong bleeding channel — Larrey case.
    return CasualtySignature(
        breathing_curve=[0.22, 0.26, 0.24, 0.27, 0.25, 0.28],
        chest_motion_fd=rng.uniform(0.25, 0.35),
        perfusion_drop_score=rng.uniform(0.10, 0.25),
        bleeding_visual_score=rng.uniform(0.86, 0.98),
        thermal_asymmetry_score=rng.uniform(0.05, 0.20),
        posture_instability_score=rng.uniform(0.05, 0.20),
        visibility_score=rng.uniform(0.85, 1.0),
    )


def _isolated_no_breathing(rng: random.Random) -> CasualtySignature:
    # No visible chest motion — rest of channels look fine.
    # chest_motion_fd stays strictly below the mortal-sign threshold.
    return CasualtySignature(
        breathing_curve=[0.005, 0.004, 0.005, 0.004, 0.005, 0.004],
        chest_motion_fd=rng.uniform(0.005, 0.035),
        perfusion_drop_score=rng.uniform(0.15, 0.30),
        bleeding_visual_score=rng.uniform(0.05, 0.20),
        thermal_asymmetry_score=rng.uniform(0.10, 0.25),
        posture_instability_score=rng.uniform(0.05, 0.25),
        visibility_score=rng.uniform(0.80, 1.0),
    )


def _isolated_collapsed_posture(rng: random.Random) -> CasualtySignature:
    return CasualtySignature(
        breathing_curve=[0.22, 0.26, 0.24, 0.27, 0.25, 0.28],
        chest_motion_fd=rng.uniform(0.25, 0.40),
        perfusion_drop_score=rng.uniform(0.15, 0.30),
        bleeding_visual_score=rng.uniform(0.05, 0.20),
        thermal_asymmetry_score=rng.uniform(0.10, 0.25),
        posture_instability_score=rng.uniform(0.87, 0.97),
        visibility_score=rng.uniform(0.80, 1.0),
    )


def _ambiguous_mid(rng: random.Random) -> CasualtySignature:
    # Everything around the band boundary → genuinely hard case.
    return CasualtySignature(
        breathing_curve=[0.15, 0.18, 0.14, 0.17, 0.16, 0.18],
        chest_motion_fd=rng.uniform(0.15, 0.22),
        perfusion_drop_score=rng.uniform(0.45, 0.65),
        bleeding_visual_score=rng.uniform(0.40, 0.60),
        thermal_asymmetry_score=rng.uniform(0.30, 0.50),
        posture_instability_score=rng.uniform(0.40, 0.60),
        visibility_score=rng.uniform(0.70, 0.95),
    )


_SigFactory = Callable[[random.Random], CasualtySignature]

_SCENARIOS: dict[str, tuple[Priority, frozenset[str], _SigFactory]] = {
    "clean_immediate":
        ("immediate", frozenset({"hemorrhage", "shock_risk"}), _clean_immediate),
    "clean_delayed":
        ("delayed", frozenset({"respiratory_distress"}), _clean_delayed),
    "clean_minimal":
        ("minimal", frozenset(), _clean_minimal),
    "isolated_bleeding":
        ("immediate", frozenset({"hemorrhage"}), _isolated_bleeding),
    "isolated_no_breathing":
        ("immediate", frozenset({"respiratory_distress"}), _isolated_no_breathing),
    "isolated_collapsed":
        ("immediate", frozenset({"unresponsive"}), _isolated_collapsed_posture),
    "ambiguous_mid":
        ("delayed", frozenset({"shock_risk"}), _ambiguous_mid),
}


def generate_labelled_dataset(
    n_per_scenario: int = 10,
    seed: int = 42,
    apply_degradation: bool = True,
) -> list[LabelledCase]:
    """Generate a labelled triage dataset covering all scenarios.

    Each case is derived from one of the seven scenarios above and
    optionally routed through :class:`SensorDegradationSimulator` with
    a light noise profile so calibration sees non-trivial variance.
    """
    rng = random.Random(seed)
    degrader = SensorDegradationSimulator(
        DegradationConfig(noise_sigma=0.05, visibility_drop=0.05),
        seed=seed,
    )

    cases: list[LabelledCase] = []
    for tag, (priority, trauma, factory) in _SCENARIOS.items():
        for i in range(n_per_scenario):
            sig = factory(rng)
            if apply_degradation:
                sig = degrader.apply(sig)
            cases.append(
                LabelledCase(
                    casualty_id=f"{tag}_{i}",
                    signature=sig,
                    priority=priority,
                    trauma_kinds=trauma,
                    scenario_tag=tag,
                )
            )
    rng.shuffle(cases)
    return cases
