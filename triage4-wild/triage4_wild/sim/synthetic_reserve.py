"""Deterministic synthetic camera-trap / drone-pass generator.

Real reserve footage is partnership-protected. The library is
exercised against synthetic ``WildlifeObservation`` records
tunable per signal axis.

Seeds use ``zlib.crc32`` for cross-run stability.
"""

from __future__ import annotations

import random

from biocore.seeds import crc32_seed

from ..core.enums import CaptureQuality, Species, ThreatKind
from ..core.models import (
    BodyConditionSample,
    GaitSample,
    LocationHandle,
    QuadrupedPoseSample,
    ThermalSample,
    ThreatConfidence,
    WildlifeObservation,
)


_DEFAULT_WINDOW_S = 30.0


def _rng(seed_source: tuple[str, int]) -> random.Random:
    """Build a deterministic ``random.Random`` from a token tuple.

    Delegates to ``biocore.seeds.crc32_seed`` — extracted in
    biocore tier-1 because twelve siblings share this shape.
    """
    return random.Random(crc32_seed(*seed_source))


def generate_observation(
    obs_token: str = "O-001",
    species: Species = "elephant",
    species_confidence: float = 0.9,
    location_handle: str = "grid-A7",
    window_duration_s: float = _DEFAULT_WINDOW_S,
    limb_asymmetry: float = 0.0,
    thermal_hotspot: float = 0.0,
    postural_down_fraction: float = 0.0,
    body_condition: float = 0.85,
    threat_kind: ThreatKind | None = None,
    threat_confidence: float = 0.0,
    capture_quality: CaptureQuality = "good",
    seed: int = 0,
) -> WildlifeObservation:
    """Build one synthetic WildlifeObservation."""
    for name, val in (
        ("limb_asymmetry", limb_asymmetry),
        ("thermal_hotspot", thermal_hotspot),
        ("postural_down_fraction", postural_down_fraction),
        ("body_condition", body_condition),
        ("threat_confidence", threat_confidence),
    ):
        if not 0.0 <= val <= 1.0:
            raise ValueError(f"{name} must be in [0, 1], got {val}")
    if window_duration_s <= 0:
        raise ValueError("window_duration_s must be positive")

    rng = _rng((obs_token, seed))

    # --- Pose samples (every 0.5 s) ---
    pose_samples: list[QuadrupedPoseSample] = []
    n_pose = max(4, int(window_duration_s / 0.5))
    for i in range(n_pose):
        t = i * (window_duration_s / (n_pose - 1))
        asym = max(0.0, min(1.0,
            limb_asymmetry + rng.uniform(-0.05, 0.05),
        ))
        # body_upright = 1 - postural_down_fraction, with
        # the downward frames concentrated mid-window.
        progress = i / (n_pose - 1)
        is_down = (
            progress >= 0.5 - postural_down_fraction * 0.5
            and progress <= 0.5 + postural_down_fraction * 0.5
            and postural_down_fraction > 0
        )
        upright = 0.15 + rng.uniform(-0.05, 0.05) if is_down else 0.85 + rng.uniform(-0.05, 0.05)
        pose_samples.append(QuadrupedPoseSample(
            t_s=round(t, 3),
            limb_asymmetry=round(asym, 3),
            body_upright=round(max(0.0, min(1.0, upright)), 3),
        ))

    # --- Thermal samples (every 1 s) ---
    thermal: list[ThermalSample] = []
    n_thermal = max(4, int(window_duration_s / 1.0))
    for i in range(n_thermal):
        t = i * (window_duration_s / (n_thermal - 1))
        hot = max(0.0, min(1.0,
            thermal_hotspot + rng.uniform(-0.05, 0.05),
        ))
        thermal.append(ThermalSample(
            t_s=round(t, 3),
            hotspot=round(hot, 3),
        ))

    # --- Gait samples (every 3 s) ---
    gait: list[GaitSample] = []
    n_gait = max(3, int(window_duration_s / 3.0))
    for i in range(n_gait):
        t = i * (window_duration_s / (n_gait - 1))
        pace = 1.5 + rng.uniform(-0.3, 0.3)
        steadiness = max(0.0, min(1.0,
            0.9 - limb_asymmetry * 0.4 + rng.uniform(-0.05, 0.05),
        ))
        gait.append(GaitSample(
            t_s=round(t, 3),
            pace_mps=round(max(0.0, pace), 3),
            cadence_steadiness=round(steadiness, 3),
        ))

    # --- Body-condition samples (every 5 s) ---
    bc: list[BodyConditionSample] = []
    n_bc = max(2, int(window_duration_s / 5.0))
    for i in range(n_bc):
        t = i * (window_duration_s / (n_bc - 1))
        v = max(0.0, min(1.0,
            body_condition + rng.uniform(-0.03, 0.03),
        ))
        bc.append(BodyConditionSample(
            t_s=round(t, 3),
            condition_score=round(v, 3),
        ))

    # --- Threat confidences ---
    threats: list[ThreatConfidence] = []
    if threat_kind is not None and threat_confidence > 0:
        threats.append(ThreatConfidence(
            kind=threat_kind,
            confidence=round(threat_confidence, 3),
        ))

    return WildlifeObservation(
        obs_token=obs_token,
        species=species,
        species_confidence=species_confidence,
        window_duration_s=window_duration_s,
        location=LocationHandle(handle=location_handle),
        capture_quality=capture_quality,
        pose_samples=pose_samples,
        thermal_samples=thermal,
        gait_samples=gait,
        body_condition_samples=bc,
        threat_signals=threats,
    )


def demo_observations() -> list[WildlifeObservation]:
    """Five demo observations across species + signal axes.

    1. Calm elephant, grid-A7 → no alerts.
    2. Zebra with gait asymmetry → watch via gait.
    3. Buffalo with thermal hotspot → urgent via thermal.
    4. Rhino with upstream snare_injury threat flag →
       urgent via high-value escalation + threat channel.
    5. Giraffe in sustained down-posture + low body
       condition → urgent via collapse + body_condition.
    """
    return [
        generate_observation(
            obs_token="O-001", species="elephant",
            location_handle="grid-A7",
            seed=1,
        ),
        generate_observation(
            obs_token="O-002", species="zebra",
            location_handle="zone-central",
            limb_asymmetry=0.40,
            seed=2,
        ),
        generate_observation(
            obs_token="O-003", species="buffalo",
            location_handle="grid-B3",
            thermal_hotspot=0.55,
            seed=3,
        ),
        generate_observation(
            obs_token="O-004", species="rhino",
            location_handle="zone-north",
            limb_asymmetry=0.20,
            threat_kind="snare_injury",
            threat_confidence=0.80,
            seed=4,
        ),
        generate_observation(
            obs_token="O-005", species="giraffe",
            location_handle="grid-C5",
            postural_down_fraction=0.80,
            body_condition=0.35,
            seed=5,
        ),
    ]
