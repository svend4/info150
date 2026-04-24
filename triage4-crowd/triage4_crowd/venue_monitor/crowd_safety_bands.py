"""Threshold bands for mapping signature scores → alert levels.

Defaults reflect Helbing 2007 + Fruin 1971 reference density
bands. Protocol-authentic starting values, NOT field-
calibrated against any specific venue. Real deployments tune
with paired-deployment data.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CrowdSafetyBands:
    """Threshold bands used by the venue-monitor engine."""

    density_watch: float = 0.70
    density_urgent: float = 0.45

    flow_watch: float = 0.65
    flow_urgent: float = 0.40

    pressure_watch: float = 0.65
    pressure_urgent: float = 0.35

    medical_watch: float = 0.75
    medical_urgent: float = 0.40

    overall_watch: float = 0.70
    overall_urgent: float = 0.45


DEFAULT_BANDS = CrowdSafetyBands()
