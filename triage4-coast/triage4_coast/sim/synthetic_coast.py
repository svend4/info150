"""Deterministic synthetic coast generator for tests + demos."""

from __future__ import annotations

from ..core.enums import ZoneKind, VALID_ZONE_KINDS
from ..core.models import CoastZoneObservation


_DEFAULT_WINDOW_S = 60.0


def generate_zone_observation(
    zone_id: str = "Z-coast",
    zone_kind: ZoneKind = "beach",
    window_duration_s: float = _DEFAULT_WINDOW_S,
    density_pressure: float = 0.0,
    in_water_motion: float = 0.0,
    sun_intensity: float = 0.0,
    lost_child_flag: bool = False,
    fall_event_flag: bool = False,
    stationary_person_signal: float = 0.0,
    flow_anomaly_signal: float = 0.0,
    slip_risk_signal: float = 0.0,
    seed: int = 0,  # API parity; engine is deterministic
) -> CoastZoneObservation:
    """Build one synthetic CoastZoneObservation."""
    if zone_kind not in VALID_ZONE_KINDS:
        raise ValueError(f"unknown zone_kind {zone_kind!r}")
    return CoastZoneObservation(
        zone_id=zone_id,
        zone_kind=zone_kind,
        window_duration_s=window_duration_s,
        density_pressure=density_pressure,
        in_water_motion=in_water_motion,
        sun_intensity=sun_intensity,
        lost_child_flag=lost_child_flag,
        fall_event_flag=fall_event_flag,
        stationary_person_signal=stationary_person_signal,
        flow_anomaly_signal=flow_anomaly_signal,
        slip_risk_signal=slip_risk_signal,
    )


def demo_coast() -> list[CoastZoneObservation]:
    """Four-zone demo touching ok, watch, urgent bands."""
    return [
        generate_zone_observation(
            zone_id="Z1-beach-quiet", zone_kind="beach",
            density_pressure=0.20, sun_intensity=0.45,
        ),
        generate_zone_observation(
            zone_id="Z2-promenade-busy", zone_kind="promenade",
            density_pressure=0.65, sun_intensity=0.60,
        ),
        generate_zone_observation(
            zone_id="Z3-water-swim", zone_kind="water",
            density_pressure=0.55, in_water_motion=0.15,
            sun_intensity=0.70,
        ),
        generate_zone_observation(
            zone_id="Z4-pier-end", zone_kind="pier",
            density_pressure=0.30, sun_intensity=0.50,
            lost_child_flag=True,
        ),
    ]
