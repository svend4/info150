"""Threshold bands for mapping signature scores → alert levels.

Numbers reflect the Wiki 2010 / Pia 2006 IDR literature,
WHO / Red Cross drowning-window data, and ILSF (International
Lifesaving Federation) guidance on breath-hold duration.
Protocol-authentic defaults; real-pool calibration requires
instructor-labelled events.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DrowningBands:
    """Threshold bands used by the pool-watch engine."""

    # Submersion safety bands. watch = rising attention;
    # urgent = lifeguard pendant buzz.
    submersion_watch: float = 0.70
    submersion_urgent: float = 0.45

    # IDR posture bands.
    idr_watch: float = 0.70
    idr_urgent: float = 0.40

    # Absent-swimmer bands.
    absent_watch: float = 0.70
    absent_urgent: float = 0.45

    # Surface-distress bands.
    distress_watch: float = 0.70
    distress_urgent: float = 0.45

    # Overall fused bands.
    overall_watch: float = 0.70
    overall_urgent: float = 0.45

    # Submersion thresholds (seconds) used by the
    # submersion_duration signature. Consumer apps can tune
    # per-zone by passing a modified bands instance.
    submersion_watch_s: float = 15.0
    submersion_urgent_s: float = 30.0


DEFAULT_BANDS = DrowningBands()
