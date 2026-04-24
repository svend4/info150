"""Threshold bands for mapping signature scores → alert levels.

Defaults are OSHA / NIOSH / ACGIH / NIOSH-lifting-equation
reference numbers. They are protocol-authentic starting
values, NOT field-validated against any specific site.
Real deployments calibrate with a pilot.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SafetyBands:
    """Threshold bands used by the site-safety engine."""

    # PPE compliance fraction (1.0 = perfect).
    ppe_watch: float = 0.85
    ppe_urgent: float = 0.60

    # Lifting-safety score.
    lifting_watch: float = 0.70
    lifting_urgent: float = 0.45

    # Heat-safety score.
    heat_watch: float = 0.60
    heat_urgent: float = 0.30

    # Fatigue-safety score.
    fatigue_watch: float = 0.60
    fatigue_urgent: float = 0.30

    # Overall score → level thresholds.
    overall_watch: float = 0.70
    overall_urgent: float = 0.45


DEFAULT_BANDS = SafetyBands()
