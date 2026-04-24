"""Deterministic synthetic zone-observation generator.

Real venue footage with crush conditions is rare + legally
contested (Hillsborough 1989, Love Parade 2010, Itaewon 2022
are the studied cases, and committing any footage is both
contested and unethical at scale). The engine is exercised
against synthetic ``ZoneObservation`` windows tunable across
the four signal axes:

- ``density_pressure`` ∈ [0, 1] — scales density-per-m²
  readings from comfortable to critical.
- ``flow_compaction``  ∈ [0, 1] — scales flow magnitude +
  compaction toward the precursor pattern.
- ``pressure_level``   ∈ [0, 1] — raises crowd-pressure RMS
  readings through the elevated + high bands.
- ``medical_rate``     ∈ [0, 1] — probability per-sample that
  an anonymous collapsed-person candidate fires.

Seeds use ``zlib.crc32`` — deterministic across processes,
unlike the stdlib ``hash()``.
"""

from __future__ import annotations

import random
import zlib

from ..core.enums import CrowdDirection, ZoneKind
from ..core.models import (
    DensityReading,
    FlowSample,
    MedicalCandidate,
    PressureReading,
    ZoneObservation,
)


_DEFAULT_WINDOW_S = 180.0     # three-minute aggregation window
_DENSITY_INTERVAL_S = 10.0    # density sample every 10 s
_FLOW_INTERVAL_S = 15.0
_PRESSURE_INTERVAL_S = 5.0


def _rng(seed_source: tuple[str, int]) -> random.Random:
    seed_bytes = f"{seed_source[0]}|{seed_source[1]}".encode("utf-8")
    return random.Random(zlib.crc32(seed_bytes))


def generate_zone_observation(
    zone_id: str = "Z-001",
    zone_kind: ZoneKind = "standing",
    window_duration_s: float = _DEFAULT_WINDOW_S,
    density_pressure: float = 0.0,
    flow_compaction: float = 0.0,
    pressure_level: float = 0.0,
    medical_rate: float = 0.0,
    seed: int = 0,
) -> ZoneObservation:
    """Build one synthetic zone-observation window."""
    for name, val in (
        ("density_pressure", density_pressure),
        ("flow_compaction", flow_compaction),
        ("pressure_level", pressure_level),
        ("medical_rate", medical_rate),
    ):
        if not 0.0 <= val <= 1.0:
            raise ValueError(f"{name} must be in [0, 1], got {val}")
    if window_duration_s <= 0:
        raise ValueError("window_duration_s must be positive")

    rng = _rng((zone_id, seed))

    # --- Density readings ---
    density_readings: list[DensityReading] = []
    n_dens = max(2, int(window_duration_s / _DENSITY_INTERVAL_S))
    # Map density_pressure 0.0 → 1.5 p/m², 1.0 → 6.5 p/m².
    base_density = 1.5 + 5.0 * density_pressure
    for i in range(n_dens):
        t = i * (window_duration_s / (n_dens - 1))
        val = max(0.0, min(12.0, base_density + rng.uniform(-0.2, 0.2)))
        density_readings.append(DensityReading(
            t_s=round(t, 3),
            persons_per_m2=round(val, 3),
        ))

    # --- Flow samples ---
    flow_samples: list[FlowSample] = []
    n_flow = max(2, int(window_duration_s / _FLOW_INTERVAL_S))
    # Direction: static if no compaction, "in" if compacting.
    net_dir: CrowdDirection = "static" if flow_compaction < 0.2 else "in"
    for i in range(n_flow):
        t = i * (window_duration_s / (n_flow - 1))
        mag = max(0.0, min(1.0, flow_compaction + rng.uniform(-0.05, 0.05)))
        comp = max(0.0, min(1.0, flow_compaction + rng.uniform(-0.05, 0.05)))
        flow_samples.append(FlowSample(
            t_s=round(t, 3),
            net_direction=net_dir,
            magnitude=round(mag, 3),
            compaction=round(comp, 3),
        ))

    # --- Pressure readings ---
    pressure_readings: list[PressureReading] = []
    n_press = max(2, int(window_duration_s / _PRESSURE_INTERVAL_S))
    # Pressure_level 0.0 → ~0.10 (normal), 1.0 → ~0.85 (clearly elevated).
    base_press = 0.10 + 0.75 * pressure_level
    for i in range(n_press):
        t = i * (window_duration_s / (n_press - 1))
        val = max(0.0, min(1.0, base_press + rng.uniform(-0.05, 0.05)))
        pressure_readings.append(PressureReading(
            t_s=round(t, 3),
            pressure_rms=round(val, 3),
        ))

    # --- Medical candidates ---
    medical_candidates: list[MedicalCandidate] = []
    n_candidate_slots = max(1, int(window_duration_s / 20.0))
    for i in range(n_candidate_slots):
        if rng.random() < medical_rate:
            # High-confidence candidate at this slot.
            cand_id = f"{zone_id}-C{i:02d}"
            t = (i + 0.5) * (window_duration_s / n_candidate_slots)
            conf = min(1.0, 0.75 + rng.uniform(-0.1, 0.2))
            medical_candidates.append(MedicalCandidate(
                candidate_id=cand_id,
                t_s=round(t, 3),
                confidence=round(conf, 3),
            ))

    return ZoneObservation(
        zone_id=zone_id,
        zone_kind=zone_kind,
        window_duration_s=window_duration_s,
        density_readings=density_readings,
        flow_samples=flow_samples,
        pressure_readings=pressure_readings,
        medical_candidates=medical_candidates,
    )


def demo_venue() -> list[ZoneObservation]:
    """Five-zone demo covering each channel's bands.

    1. Empty concourse  — quiet baseline.
    2. Busy seating     — density watch band.
    3. Egress compaction — flow urgent.
    4. Near-stage pressure — pressure urgent.
    5. Medical candidate — medical urgent.
    """
    return [
        generate_zone_observation(
            zone_id="Z1-concourse",
            zone_kind="concourse",
            density_pressure=0.15,
            seed=1,
        ),
        generate_zone_observation(
            zone_id="Z2-seating",
            zone_kind="seating",
            density_pressure=0.50,
            seed=2,
        ),
        generate_zone_observation(
            zone_id="Z3-egress",
            zone_kind="egress",
            flow_compaction=0.90,
            density_pressure=0.40,
            seed=3,
        ),
        generate_zone_observation(
            zone_id="Z4-near-stage",
            zone_kind="standing",
            density_pressure=0.70,
            pressure_level=0.85,
            seed=4,
        ),
        generate_zone_observation(
            zone_id="Z5-transit",
            zone_kind="transit_platform",
            medical_rate=1.0,
            seed=5,
        ),
    ]
