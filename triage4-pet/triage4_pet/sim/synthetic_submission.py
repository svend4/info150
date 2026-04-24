"""Deterministic synthetic pet-video submission generator.

Real veterinary video is IACUC-gated and cannot be
committed to an open-source repo. The library is exercised
against synthetic ``PetObservation`` records tunable per
signal axis.

Seeds use ``zlib.crc32`` for cross-run stability.
"""

from __future__ import annotations

import random
import zlib
from typing import cast

from ..core.enums import (
    PainBehaviorKind,
    SpeciesKind,
    VideoQuality,
)
from ..core.models import (
    BreathingSample,
    GaitSample,
    PainBehaviorSample,
    PetObservation,
    PoseSample,
    VitalHRSample,
)


_DEFAULT_WINDOW_S = 60.0


# Resting RR midpoint per species (for synthetic baseline).
_RESTING_RR: dict[SpeciesKind, float] = {
    "dog":    18.0,
    "cat":    25.0,
    "horse":  12.0,
    "rabbit": 45.0,
}

# Resting HR midpoint per species.
_RESTING_HR: dict[SpeciesKind, float] = {
    "dog":    100.0,
    "cat":    180.0,
    "horse":  38.0,
    "rabbit": 220.0,
}


# Pain-behavior picks per species (highest-weight behaviors).
_SPECIES_PAIN_BEHAVIORS: dict[SpeciesKind, tuple[PainBehaviorKind, ...]] = {
    "dog":    ("panting_at_rest", "hunched_posture", "tucked_tail"),
    "cat":    ("hiding", "ear_position", "hunched_posture"),
    "horse":  ("weight_shifting", "ear_position", "hunched_posture"),
    "rabbit": ("hiding", "hunched_posture", "ear_position"),
}


def _rng(seed_source: tuple[str, int]) -> random.Random:
    seed_bytes = f"{seed_source[0]}|{seed_source[1]}".encode("utf-8")
    return random.Random(zlib.crc32(seed_bytes))


def generate_observation(
    pet_token: str = "P-001",
    species: SpeciesKind = "dog",
    window_duration_s: float = _DEFAULT_WINDOW_S,
    age_years: float | None = 5.0,
    gait_asymmetry: float = 0.0,
    respiratory_elevation: float = 0.0,
    cardiac_elevation: float = 0.0,
    pain_behavior_count: int = 0,
    video_quality: VideoQuality = "good",
    seed: int = 0,
) -> PetObservation:
    """Build one synthetic PetObservation."""
    for name, val in (
        ("gait_asymmetry", gait_asymmetry),
        ("respiratory_elevation", respiratory_elevation),
        ("cardiac_elevation", cardiac_elevation),
    ):
        if not 0.0 <= val <= 1.0:
            raise ValueError(f"{name} must be in [0, 1], got {val}")
    if pain_behavior_count < 0 or pain_behavior_count > 5:
        raise ValueError(
            f"pain_behavior_count must be in [0, 5], got "
            f"{pain_behavior_count}"
        )
    if window_duration_s <= 0:
        raise ValueError("window_duration_s must be positive")

    rng = _rng((pet_token, seed))

    # --- Pose samples (every ~2 s) ---
    pose_samples: list[PoseSample] = []
    n_pose = max(4, int(window_duration_s / 2.0))
    for i in range(n_pose):
        t = i * (window_duration_s / (n_pose - 1))
        visible = int(rng.uniform(12, 24))
        conf = 0.8 + rng.uniform(-0.1, 0.1)
        pose_samples.append(PoseSample(
            t_s=round(t, 3),
            visible_keypoints=max(0, min(50, visible)),
            detection_confidence=round(max(0.0, min(1.0, conf)), 3),
        ))

    # --- Gait samples (every ~3 s) ---
    gait_samples: list[GaitSample] = []
    n_gait = max(3, int(window_duration_s / 3.0))
    for i in range(n_gait):
        t = i * (window_duration_s / (n_gait - 1))
        asym = gait_asymmetry + rng.uniform(-0.05, 0.05)
        consistency = 0.9 - gait_asymmetry * 0.3 + rng.uniform(-0.05, 0.05)
        gait_samples.append(GaitSample(
            t_s=round(t, 3),
            limb_asymmetry=round(max(0.0, min(1.0, asym)), 3),
            pace_consistency=round(max(0.0, min(1.0, consistency)), 3),
        ))

    # --- Breathing samples (every ~5 s) ---
    breathing_samples: list[BreathingSample] = []
    n_br = max(2, int(window_duration_s / 5.0))
    base_rr = _RESTING_RR[species]
    # Elevated RR scales toward species cap.
    elevated_rr = base_rr + (base_rr * 1.5) * respiratory_elevation
    for i in range(n_br):
        t = i * (window_duration_s / (n_br - 1))
        rate = elevated_rr + rng.uniform(-2.0, 2.0)
        # at_rest True for every sample (synthetic pet is calm).
        breathing_samples.append(BreathingSample(
            t_s=round(t, 3),
            rate_bpm=round(max(2.0, min(200.0, rate)), 2),
            at_rest=True,
        ))

    # --- HR samples (every ~5 s) ---
    hr_samples: list[VitalHRSample] = []
    n_hr = max(2, int(window_duration_s / 5.0))
    base_hr = _RESTING_HR[species]
    elevated_hr = base_hr + base_hr * 0.6 * cardiac_elevation
    for i in range(n_hr):
        t = i * (window_duration_s / (n_hr - 1))
        hr = elevated_hr + rng.uniform(-5.0, 5.0)
        # Reliable 70 % of the time under good conditions.
        reliable = video_quality == "good" and rng.random() < 0.7
        hr_samples.append(VitalHRSample(
            t_s=round(t, 3),
            hr_bpm=round(max(20.0, min(400.0, hr)), 2),
            reliable=reliable,
        ))

    # --- Pain-behavior samples ---
    pain_samples: list[PainBehaviorSample] = []
    if pain_behavior_count > 0:
        candidates = _SPECIES_PAIN_BEHAVIORS[species]
        for i in range(min(pain_behavior_count, len(candidates))):
            kind = cast(PainBehaviorKind, candidates[i])
            t = (i + 0.5) * (window_duration_s / pain_behavior_count)
            conf = 0.75 + rng.uniform(-0.1, 0.2)
            pain_samples.append(PainBehaviorSample(
                t_s=round(t, 3),
                kind=kind,
                confidence=round(max(0.0, min(1.0, conf)), 3),
            ))

    return PetObservation(
        pet_token=pet_token,
        species=species,
        window_duration_s=window_duration_s,
        age_years=age_years,
        video_quality=video_quality,
        pose_samples=pose_samples,
        gait_samples=gait_samples,
        breathing_samples=breathing_samples,
        hr_samples=hr_samples,
        pain_samples=pain_samples,
    )


def demo_submissions() -> list[PetObservation]:
    """Five demo submissions covering each recommendation band.

    1. Calm dog — can_wait.
    2. Limping dog — routine_visit via gait.
    3. Cat showing multiple pain behaviors — see_today.
    4. Horse with elevated RR + weight shifting — see_today.
    5. Rabbit hiding with hunched posture — see_today (cats +
       rabbits have the most conservative escalation).
    """
    return [
        generate_observation(
            pet_token="P-001", species="dog",
            age_years=5.0, seed=1,
        ),
        generate_observation(
            pet_token="P-002", species="dog",
            age_years=8.0, gait_asymmetry=0.45,
            pain_behavior_count=1, seed=2,
        ),
        generate_observation(
            pet_token="P-003", species="cat",
            age_years=10.0, pain_behavior_count=3,
            respiratory_elevation=0.7, gait_asymmetry=0.40,
            seed=3,
        ),
        generate_observation(
            pet_token="P-004", species="horse",
            age_years=12.0, respiratory_elevation=0.6,
            pain_behavior_count=2, seed=4,
        ),
        generate_observation(
            pet_token="P-005", species="rabbit",
            age_years=3.0, pain_behavior_count=2,
            gait_asymmetry=0.2, seed=5,
        ),
    ]
