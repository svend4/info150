"""HomeMonitoringEngine — the main engine.

Sibling of the triage4 / triage4-fit / triage4-farm /
triage4-rescue / triage4-drive engines. Takes one
``ResidentObservation`` window and optional per-resident
baseline, and produces:
- a ``WellnessScore`` (per-channel + fused overall +
  alert level)
- zero-or-more ``CaregiverAlert`` records.

Observation-only. Never diagnoses. Never dispatches
emergency services. Never pathologizes the resident. See
docs/PHILOSOPHY.md for the four boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.enums import AlertKind, AlertLevel
from ..core.models import (
    CaregiverAlert,
    ResidentObservation,
    WellnessScore,
)
from ..signatures.activity_pattern import (
    ActivityFractions,
    compute_activity_alignment,
)
from ..signatures.fall_signature import compute_fall_risk
from ..signatures.mobility_pace import compute_mobility_trend
from .fall_thresholds import DEFAULT_THRESHOLDS, FallThresholds


@dataclass(frozen=True)
class ResidentBaseline:
    """Per-resident rolling baseline, computed by the caller.

    All fields optional — the engine falls back to neutral
    scoring when a channel's baseline is missing and
    surfaces a "baseline pending" cue.
    """

    activity: ActivityFractions | None = None
    mobility_median_mps: float | None = None


# Channel weights for the overall wellness fusion. Fall-risk
# is inverted (1 - fall_risk) before fusing — all three
# channels are on the "1.0 = good" convention inside the
# overall score.
_CHANNEL_WEIGHTS: dict[str, float] = {
    "fall": 0.5,
    "activity": 0.3,
    "mobility": 0.2,
}


class HomeMonitoringEngine:
    """Score one observation window + emit caregiver alerts."""

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        thresholds: FallThresholds | None = None,
    ) -> None:
        w = dict(weights or _CHANNEL_WEIGHTS)
        total = sum(w.values())
        if total <= 0:
            raise ValueError("weight total must be positive")
        self._weights = {k: v / total for k, v in w.items()}
        self._thresholds = thresholds or DEFAULT_THRESHOLDS

    # -- public API -----------------------------------------------------

    def review(
        self,
        observation: ResidentObservation,
        baseline: ResidentBaseline | None = None,
    ) -> tuple[WellnessScore, list[CaregiverAlert]]:
        wid = observation.window_id
        thr = self._thresholds
        baseline = baseline or ResidentBaseline()

        # --- Signatures ---
        fall_risk, fall_band = compute_fall_risk(
            observation.impacts,
            impact_threshold_g=thr.impact_threshold_g,
            stillness_threshold_s=thr.stillness_threshold_s,
        )
        activity_alignment = compute_activity_alignment(
            observation.activity_samples,
            baseline.activity,
        )
        median_pace, mobility_trend = compute_mobility_trend(
            observation.transitions,
            baseline.mobility_median_mps,
        )

        # --- Fusion. Fall-risk is inverted so all three are
        # "higher = better" inside the overall.
        overall = (
            self._weights["fall"] * (1.0 - fall_risk)
            + self._weights["activity"] * activity_alignment
            + self._weights["mobility"] * mobility_trend
        )
        # Mortal-sign-style override: a clear fall candidate
        # dominates the overall, floored at urgent.
        if fall_band == "candidate":
            overall = min(overall, thr.overall_urgent - 0.01)

        alert_level = self._overall_to_level(overall)
        score = WellnessScore(
            window_id=wid,
            fall_risk=round(fall_risk, 3),
            activity_alignment=round(activity_alignment, 3),
            mobility_trend=round(mobility_trend, 3),
            overall=round(max(0.0, min(1.0, overall)), 3),
            alert_level=alert_level,
        )

        alerts = self._alerts_for(
            wid, fall_risk, fall_band,
            activity_alignment, mobility_trend, median_pace,
            baseline,
        )

        # Calibration alert when the window is essentially
        # empty.
        if (
            not observation.impacts
            and not observation.activity_samples
            and not observation.transitions
        ):
            alerts.append(CaregiverAlert(
                window_id=wid,
                kind="baseline",
                level="check_in",
                text=(
                    "No sensor data recorded in this window. "
                    "Caregiver: verify the home sensor hub is "
                    "online before relying on the next window's "
                    "wellness score."
                ),
            ))

        return score, alerts

    # -- internals ------------------------------------------------------

    def _overall_to_level(self, overall: float) -> AlertLevel:
        thr = self._thresholds
        if overall < thr.overall_urgent:
            return "urgent"
        if overall < thr.overall_check_in:
            return "check_in"
        return "ok"

    def _alerts_for(
        self,
        window_id: str,
        fall_risk: float,
        fall_band: str,
        activity_alignment: float,
        mobility_trend: float,
        median_pace: float,
        baseline: ResidentBaseline,
    ) -> list[CaregiverAlert]:
        alerts: list[CaregiverAlert] = []
        thr = self._thresholds

        # Fall channel.
        if fall_band == "candidate":
            alerts.append(self._alert(
                window_id, "fall", "urgent",
                "Impact event followed by sustained stillness "
                "detected. Caregiver: contact the resident or "
                "their designated escalation path.",
                observed_value=fall_risk,
            ))
        elif fall_band == "borderline":
            alerts.append(self._alert(
                window_id, "fall", "check_in",
                "Impact event detected; post-impact movement was "
                "ambiguous. Caregiver: a check-in call is "
                "warranted.",
                observed_value=fall_risk,
            ))

        # Activity channel — thresholds only apply when a
        # baseline exists.
        if baseline.activity is not None:
            if activity_alignment < thr.activity_urgent:
                alerts.append(self._alert(
                    window_id, "activity", "urgent",
                    "Daily activity pattern deviates strongly from "
                    "the baseline. Caregiver: a check-in call is "
                    "warranted.",
                    observed_value=activity_alignment,
                ))
            elif activity_alignment < thr.activity_check_in:
                alerts.append(self._alert(
                    window_id, "activity", "check_in",
                    "Daily activity pattern deviates from the "
                    "baseline. Caregiver: consider a check-in call.",
                    observed_value=activity_alignment,
                ))
        else:
            alerts.append(self._alert(
                window_id, "baseline", "check_in",
                "Activity baseline not yet established. Alignment "
                "score is neutral by default until at least seven "
                "days of observations accumulate.",
                observed_value=activity_alignment,
            ))

        # Mobility channel — only when baseline is available.
        if baseline.mobility_median_mps is not None:
            if mobility_trend < thr.mobility_urgent:
                alerts.append(self._alert(
                    window_id, "mobility", "urgent",
                    f"Walking-pace trend is well below the resident's "
                    f"own baseline (today: {median_pace:.2f} m/s, "
                    f"baseline: {baseline.mobility_median_mps:.2f} m/s). "
                    "Caregiver: a check-in call is warranted.",
                    observed_value=mobility_trend,
                ))
            elif mobility_trend < thr.mobility_check_in:
                alerts.append(self._alert(
                    window_id, "mobility", "check_in",
                    f"Walking-pace trend is below the resident's own "
                    f"baseline (today: {median_pace:.2f} m/s, "
                    f"baseline: {baseline.mobility_median_mps:.2f} m/s). "
                    "Caregiver: consider a check-in call.",
                    observed_value=mobility_trend,
                ))

        return alerts

    @staticmethod
    def _alert(
        window_id: str,
        kind: AlertKind,
        level: AlertLevel,
        text: str,
        observed_value: float | None = None,
    ) -> CaregiverAlert:
        return CaregiverAlert(
            window_id=window_id,
            kind=kind,
            level=level,
            text=text,
            observed_value=observed_value,
        )
