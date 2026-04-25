"""Deterministic synthetic patient self-report generator.

Real PHI cannot be committed to an open-source repo. The
library is exercised against synthetic ``PatientObservation``
records tunable across the signal axes. Seeds use
``zlib.crc32`` for cross-run stability.
"""

from __future__ import annotations

import random
import zlib

from ..core.enums import CaptureQuality
from ..core.models import (
    AcousticSample,
    CoughSample,
    PatientObservation,
    PatientSelfReport,
    PostureSample,
    VitalsSample,
)


_DEFAULT_WINDOW_S = 90.0  # 1.5 min structured self-report


def _rng(seed_source: tuple[str, int]) -> random.Random:
    seed_bytes = f"{seed_source[0]}|{seed_source[1]}".encode("utf-8")
    return random.Random(zlib.crc32(seed_bytes))


def generate_observation(
    patient_token: str = "P-001",
    age_years: float | None = 45.0,
    window_duration_s: float = _DEFAULT_WINDOW_S,
    hr_elevation: float = 0.0,
    rr_elevation: float = 0.0,
    cough_frequency: float = 0.0,
    acoustic_strain: float = 0.0,
    postural_instability: float = 0.0,
    capture_quality: CaptureQuality = "good",
    self_report: PatientSelfReport | None = None,
    seed: int = 0,
) -> PatientObservation:
    """Build one synthetic PatientObservation."""
    for name, val in (
        ("hr_elevation", hr_elevation),
        ("rr_elevation", rr_elevation),
        ("cough_frequency", cough_frequency),
        ("acoustic_strain", acoustic_strain),
        ("postural_instability", postural_instability),
    ):
        if not 0.0 <= val <= 1.0:
            raise ValueError(f"{name} must be in [0, 1], got {val}")
    if window_duration_s <= 0:
        raise ValueError("window_duration_s must be positive")

    rng = _rng((patient_token, seed))

    # --- Vitals samples (every ~5 s) ---
    vitals: list[VitalsSample] = []
    n_vitals = max(4, int(window_duration_s / 5.0))
    base_hr = 72.0 + 70.0 * hr_elevation
    base_rr = 16.0 + 24.0 * rr_elevation
    for i in range(n_vitals):
        t = i * (window_duration_s / (n_vitals - 1))
        hr = base_hr + rng.uniform(-3.0, 3.0)
        rr = base_rr + rng.uniform(-2.0, 2.0)
        # Reliability rate depends on capture_quality.
        reliable_prob = {
            "good": 0.85,
            "noisy": 0.5,
            "partial": 0.3,
        }[capture_quality]
        reliable = rng.random() < reliable_prob
        vitals.append(VitalsSample(
            t_s=round(t, 3),
            hr_bpm=round(max(20.0, min(300.0, hr)), 2),
            rr_bpm=round(max(2.0, min(80.0, rr)), 2),
            reliable=reliable,
        ))

    # --- Acoustic samples — "aah" portion ≈ 10 s ---
    acoustic: list[AcousticSample] = []
    for i in range(10):
        t = (window_duration_s * 0.4) + i
        strain = min(1.0, max(0.0, acoustic_strain + rng.uniform(-0.05, 0.05)))
        clarity = 0.85 - (0.3 if capture_quality == "noisy" else 0.0)
        clarity += rng.uniform(-0.05, 0.05)
        acoustic.append(AcousticSample(
            t_s=round(t, 3),
            strain_score=round(max(0.0, min(1.0, strain)), 3),
            clarity=round(max(0.0, min(1.0, clarity)), 3),
        ))

    # --- Cough samples ---
    coughs: list[CoughSample] = []
    target_coughs = int(cough_frequency * 8)
    for i in range(target_coughs):
        t = (i + 1) * (window_duration_s / (target_coughs + 1))
        coughs.append(CoughSample(
            t_s=round(t, 3),
            confidence=round(0.75 + rng.uniform(-0.1, 0.1), 3),
        ))

    # --- Posture samples — "stand here" portion ≈ 15 s ---
    posture: list[PostureSample] = []
    for i in range(15):
        t = (window_duration_s * 0.1) + i
        sway = min(1.0, max(0.0,
            postural_instability + rng.uniform(-0.05, 0.05),
        ))
        steady = max(0.0, min(1.0,
            1.0 - postural_instability + rng.uniform(-0.05, 0.05),
        ))
        posture.append(PostureSample(
            t_s=round(t, 3),
            sway_magnitude=round(sway, 3),
            balance_steadiness=round(steady, 3),
        ))

    return PatientObservation(
        patient_token=patient_token,
        window_duration_s=window_duration_s,
        age_years=age_years,
        capture_quality=capture_quality,
        vitals_samples=vitals,
        acoustic_samples=acoustic,
        cough_samples=coughs,
        posture_samples=posture,
        self_report=self_report or PatientSelfReport(),
    )


def demo_submissions() -> list[PatientObservation]:
    """Five demo submissions covering each recommendation tier.

    1. Baseline adult, no elevations → self_care.
    2. Moderate elevations → schedule.
    3. Cough + elevated RR + self-reported fever → schedule.
    4. Markedly elevated HR + RR + self-reported chest pain →
       urgent_review.
    5. Elevated postural instability + dizziness report →
       schedule.
    """
    return [
        generate_observation(
            patient_token="P-001", age_years=34.0, seed=1,
        ),
        generate_observation(
            patient_token="P-002", age_years=52.0,
            hr_elevation=0.25, acoustic_strain=0.25, seed=2,
        ),
        generate_observation(
            patient_token="P-003", age_years=41.0,
            rr_elevation=0.30, cough_frequency=0.5,
            self_report=PatientSelfReport(
                reports_fever=True,
                reports_persistent_cough=True,
            ),
            seed=3,
        ),
        generate_observation(
            patient_token="P-004", age_years=68.0,
            hr_elevation=0.85, rr_elevation=0.85,
            self_report=PatientSelfReport(
                reports_chest_pain=True,
                reports_shortness_of_breath=True,
            ),
            seed=4,
        ),
        generate_observation(
            patient_token="P-005", age_years=72.0,
            postural_instability=0.55,
            self_report=PatientSelfReport(reports_dizziness=True),
            seed=5,
        ),
    ]
