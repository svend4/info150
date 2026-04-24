"""Threshold bands for mapping signature scores → alert levels.

Numbers are drawn from published PERCLOS / distraction /
incapacitation literature (NHTSA DOT-HS-808-762, Wierwille
1994, SAE J2944, DROZY / DMD dataset conventions). They are
protocol-authentic baselines, NOT calibrated against a
specific deployment. Real fleet calibration would tune these
with a paired-deployment study — out of MVP scope.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FatigueBands:
    """Signature-score thresholds for alert-level escalation."""

    # PERCLOS: fraction of time eyes closed ≥ 80 %.
    # Wierwille 1994 reports crash-risk onset at ~0.15 and
    # severe drowsiness at ~0.30.
    perclos_caution: float = 0.15
    perclos_critical: float = 0.30

    # Distraction index: fraction of window off-task.
    distraction_caution: float = 0.3
    distraction_critical: float = 0.5

    # Incapacitation: postural-tone score.
    incapacitation_caution: float = 0.5
    incapacitation_critical: float = 0.9

    # Microsleep: any count elevates to critical directly
    # regardless of averaged PERCLOS (per Wierwille).
    microsleep_critical_count: int = 1

    # Overall-risk thresholds for the fused score.
    overall_caution: float = 0.30
    overall_critical: float = 0.55


DEFAULT_BANDS = FatigueBands()
