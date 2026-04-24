"""Deterministic synthetic herd generator for tests + demos.

Produces believable ``AnimalObservation`` records without
needing a real pose estimator, IR camera, or stockperson.
Used by Makefile ``demo`` and by the Stage 3 test suite.

Mirrors triage4-fit's ``synthetic_session`` in spirit but with
livestock vocabulary. Copy-fork, no cross-import.
"""

from __future__ import annotations

import math
import random
from typing import Iterable

from ..core.enums import Species, VALID_SPECIES
from ..core.models import AnimalObservation, JointPoseSample


# Per-species upright-at-rest pose, side-on camera, normalised
# [0, 1]. Only a subset of joints matters for each species — we
# still emit the full set so tests can exercise the pair-lookup
# logic across species without overfitting to one anatomy.
_BASE_POSES: dict[Species, dict[str, tuple[float, float]]] = {
    "dairy_cow": {
        "wither":      (0.30, 0.30),
        "rump":        (0.70, 0.30),
        "hock_l":      (0.68, 0.70),
        "hock_r":      (0.72, 0.70),
        "fetlock_l":   (0.68, 0.82),
        "fetlock_r":   (0.72, 0.82),
        "hoof_l":      (0.68, 0.92),
        "hoof_r":      (0.72, 0.92),
    },
    "pig": {
        "shoulder":    (0.30, 0.40),
        "rump":        (0.70, 0.40),
        "hock_l":      (0.68, 0.70),
        "hock_r":      (0.72, 0.70),
        "hoof_l":      (0.68, 0.90),
        "hoof_r":      (0.72, 0.90),
    },
    "chicken": {
        "keel":        (0.50, 0.50),
        "shank_l":     (0.48, 0.80),
        "shank_r":     (0.52, 0.80),
        "toe_l":       (0.48, 0.95),
        "toe_r":       (0.52, 0.95),
    },
}


# Resting respiratory bpm per species — what the sim emits for a
# healthy animal by default. The welfare engine's thresholds
# (respiratory_rate.py) live in a different module so we can
# tune them independently.
_HEALTHY_RESPIRATORY_BPM: dict[Species, float] = {
    "dairy_cow": 30.0,
    "pig": 35.0,
    "chicken": 30.0,
}


def generate_observation(
    animal_id: str,
    species: Species,
    duration_s: float = 2.0,
    lameness_severity: float = 0.0,
    respiratory_elevation: float = 0.0,
    thermal_hotspot: float | None = None,
    seed: int = 0,
    n_frames: int = 10,
) -> AnimalObservation:
    """Build one animal's pose frames + optional vitals.

    ``lameness_severity`` in [0, 1] biases the left-side
    hind-limb joints downward so the lameness signature drops
    predictably. ``respiratory_elevation`` in [0, 1] scales the
    emitted respiratory rate from healthy toward the species cap.
    ``thermal_hotspot`` is passed through unchanged (None =
    no IR signal on this pass).
    """
    if species not in VALID_SPECIES:
        raise ValueError(f"unknown species {species!r}")
    if duration_s <= 0:
        raise ValueError("duration_s must be positive")
    if not 0.0 <= lameness_severity <= 1.0:
        raise ValueError("lameness_severity must be in [0, 1]")
    if not 0.0 <= respiratory_elevation <= 1.0:
        raise ValueError("respiratory_elevation must be in [0, 1]")
    if n_frames < 4:
        raise ValueError("n_frames must be >= 4")

    rng = random.Random(hash((animal_id, species, seed)) & 0xFFFFFFFF)
    base = _BASE_POSES[species]
    pose_frames: list[list[JointPoseSample]] = []

    # Joints whose vertical position oscillates with the stride —
    # the hind limbs for quadrupeds, the shanks for birds. Used
    # only by the sim; the welfare engine doesn't care.
    stride_joints: tuple[str, ...]
    if species == "chicken":
        stride_joints = ("shank_l", "shank_r", "toe_l", "toe_r")
    else:
        stride_joints = ("hock_l", "hock_r", "fetlock_l", "fetlock_r", "hoof_l", "hoof_r")

    for i in range(n_frames):
        t = i / (n_frames - 1)
        # Stride has two full cycles across the pass.
        phase = math.sin(2 * math.pi * 2 * t)
        frame: list[JointPoseSample] = []
        for joint, (x, y) in base.items():
            dy = 0.0
            if joint in stride_joints:
                dy = 0.03 * phase
            # Lameness bias: left-side stride amplitude shrinks
            # as severity → 1. That pulls left hoof lower on
            # average relative to right, driving the |Δy| mean
            # up.
            if lameness_severity > 0 and joint.endswith("_l") and joint in stride_joints:
                dy *= max(0.0, 1.0 - lameness_severity)
                # Constant vertical offset — a lame animal's
                # weak side drags behind the sound side, which
                # is what the pair-wise |Δy| signature reads.
                dy += 0.08 * lameness_severity
            noise = rng.uniform(-0.003, 0.003)
            frame.append(
                JointPoseSample(
                    joint=joint,
                    x=min(1.0, max(0.0, x + rng.uniform(-0.002, 0.002))),
                    y=min(1.0, max(0.0, y + dy + noise)),
                    confidence=1.0,
                )
            )
        pose_frames.append(frame)

    healthy = _HEALTHY_RESPIRATORY_BPM[species]
    # Elevation → toward (but never past) the cap for the
    # welfare engine. Caps: cow 60, pig 70, chicken 80.
    caps = {"dairy_cow": 60.0, "pig": 70.0, "chicken": 80.0}
    resp = healthy + (caps[species] - healthy) * respiratory_elevation
    resp = round(resp, 1)

    return AnimalObservation(
        animal_id=animal_id,
        species=species,
        pose_frames=pose_frames,
        duration_s=duration_s,
        respiratory_bpm=resp,
        thermal_hotspot=thermal_hotspot,
    )


def demo_herd(
    n_animals: int = 6,
    n_lame: int = 2,
    species: Species = "dairy_cow",
    seed: int = 0,
) -> list[AnimalObservation]:
    """Build a demo herd — ``n_lame`` of the ``n_animals`` are lame."""
    if n_lame > n_animals:
        raise ValueError("n_lame must be <= n_animals")
    obs: list[AnimalObservation] = []
    for i in range(n_animals):
        lame = i < n_lame
        obs.append(
            generate_observation(
                animal_id=f"{species[:1].upper()}{100 + i}",
                species=species,
                # Healthy animals: no asymmetry bias, mild
                # respiratory elevation (within resting band).
                # Lame animals: severity tuned so the gait
                # signature drops below the concern threshold
                # (0.70) and the respiratory elevation reaches
                # the concern range for demo purposes.
                duration_s=2.0 + 0.1 * i,
                lameness_severity=0.90 if lame else 0.0,
                respiratory_elevation=0.70 if lame else 0.1,
                thermal_hotspot=0.30 if lame else None,
                seed=seed + i,
            )
        )
    return obs


# Silence the unused-import warning.
_ = Iterable
