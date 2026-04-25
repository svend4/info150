"""Threshold bands for the sport-performance engine.

Sport-agnostic defaults. Real deployments tune per-sport +
per-position with a partner team's labelled data.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PerformanceBands:
    """Threshold bands."""

    # Per-channel safety thresholds.
    channel_monitor: float = 0.70
    channel_hold: float = 0.45

    # Overall fused thresholds.
    overall_monitor: float = 0.70
    overall_hold: float = 0.45

    # PhysicianAlert threshold — only fires when overall
    # AND baseline-deviation safety both cross this. The
    # extra gate keeps the physician's queue narrow.
    physician_alert_overall: float = 0.50
    physician_alert_baseline_deviation: float = 0.55


DEFAULT_BANDS = PerformanceBands()
