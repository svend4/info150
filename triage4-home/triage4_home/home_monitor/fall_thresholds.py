"""Threshold bands for mapping signature scores → alert levels.

Defaults follow the Bourke 2007 + Kangas 2008 two-factor
fall-detection literature and the Studenski 2011 gait-speed
gerontology work. They are protocol-authentic starting
numbers, NOT field-calibrated against any specific deployment.
Real deployments tune these with paired-sensor data; out of
MVP scope.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FallThresholds:
    """Threshold bands used by the monitoring engine."""

    # Impact magnitude in g. 2.0 g is the conventional "fall
    # candidate" cut-off for wearable accelerometers in the
    # Bourke 2007 paper; 3.5 g is the "high-magnitude" band.
    impact_threshold_g: float = 2.0
    impact_high_g: float = 3.5
    # Stillness window after impact in seconds. 8 s is
    # conservative (caregiver-facing products use 10-15 s in
    # the field to avoid alerting on "I got right back up").
    stillness_threshold_s: float = 8.0

    # Activity-alignment thresholds.
    activity_check_in: float = 0.6
    activity_urgent: float = 0.3

    # Mobility-pace decline thresholds.
    mobility_check_in: float = 0.6
    mobility_urgent: float = 0.3

    # Overall wellness thresholds — higher = better here
    # (matches fit/farm, opposite of drive's risk framing).
    overall_check_in: float = 0.70
    overall_urgent: float = 0.45


DEFAULT_THRESHOLDS = FallThresholds()
