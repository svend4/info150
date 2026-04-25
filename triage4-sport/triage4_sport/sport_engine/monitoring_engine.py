"""SportPerformanceEngine — three-audience output engine.

Produces ONE PerformanceAssessment + zero-or-more
CoachMessage / TrainerNote entries + zero-or-one
PhysicianAlert from one AthleteObservation.

The PhysicianAlert is gated by a higher threshold: it only
fires when overall safety AND baseline-deviation safety
both cross their physician-alert thresholds. This keeps
the physician's queue narrow — single-channel watch-band
signals reach the trainer but not the physician.

See docs/PHILOSOPHY.md.
"""

from __future__ import annotations

from ..core.enums import RiskBand
from ..core.models import (
    AthleteBaseline,
    AthleteObservation,
    CoachMessage,
    PerformanceAssessment,
    PhysicianAlert,
    SessionReport,
    TrainerNote,
)
from ..signatures.baseline_deviation import (
    compute_baseline_deviation_safety,
)
from ..signatures.form_asymmetry import (
    SIGNATURE_VERSION as FORM_SIG_VERSION,
    compute_form_asymmetry_safety,
)
from ..signatures.recovery_hr import (
    SIGNATURE_VERSION as RECOVERY_SIG_VERSION,
    compute_recovery_hr_safety,
)
from ..signatures.workload_load import (
    SIGNATURE_VERSION as WORKLOAD_SIG_VERSION,
    compute_workload_safety,
)
from .performance_bands import DEFAULT_BANDS, PerformanceBands


_CHANNEL_WEIGHTS: dict[str, float] = {
    "form_asymmetry":     0.30,
    "workload_load":      0.30,
    "recovery_hr":        0.20,
    "baseline_deviation": 0.20,
}


class SportPerformanceEngine:
    """Score one athlete-session + emit three-audience output."""

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        bands: PerformanceBands | None = None,
    ) -> None:
        w = dict(weights or _CHANNEL_WEIGHTS)
        total = sum(w.values())
        if total <= 0:
            raise ValueError("weight total must be positive")
        self._weights = {k: v / total for k, v in w.items()}
        self._bands = bands or DEFAULT_BANDS

    # -- public API -----------------------------------------------------

    def review(
        self,
        observation: AthleteObservation,
        baseline: AthleteBaseline | None = None,
    ) -> SessionReport:
        b = self._bands

        form = compute_form_asymmetry_safety(
            observation.movement_samples,
            typical_baseline=(
                baseline.typical_form_asymmetry
                if baseline is not None else None
            ),
        )
        workload = compute_workload_safety(
            observation.workload_samples,
            typical_baseline=(
                baseline.typical_workload_index
                if baseline is not None else None
            ),
        )
        recovery = compute_recovery_hr_safety(
            observation.recovery_samples,
            typical_baseline_bpm=(
                baseline.typical_recovery_drop_bpm
                if baseline is not None else None
            ),
        )
        baseline_dev = compute_baseline_deviation_safety(
            form, workload, recovery,
        )

        overall = (
            self._weights["form_asymmetry"] * form
            + self._weights["workload_load"] * workload
            + self._weights["recovery_hr"] * recovery
            + self._weights["baseline_deviation"] * baseline_dev
        )
        overall = max(0.0, min(1.0, overall))

        # Channel-hold mortal-sign override.
        channel_hold_fired = (
            form < b.channel_hold
            or workload < b.channel_hold
            or recovery < b.channel_hold
        )
        if channel_hold_fired:
            overall = min(overall, b.overall_hold - 0.01)

        risk_band: RiskBand
        if overall < b.overall_hold:
            risk_band = "hold"
        elif overall < b.overall_monitor:
            risk_band = "monitor"
        else:
            risk_band = "steady"

        assessment = PerformanceAssessment(
            athlete_token=observation.athlete_token,
            form_asymmetry_safety=round(form, 3),
            workload_load_safety=round(workload, 3),
            recovery_hr_safety=round(recovery, 3),
            baseline_deviation_safety=round(baseline_dev, 3),
            overall=round(overall, 3),
            risk_band=risk_band,
        )

        coach_messages = self._build_coach_messages(
            observation, assessment,
        )
        trainer_notes = self._build_trainer_notes(
            observation, assessment, form, workload, recovery,
        )
        physician_alert = self._maybe_build_physician_alert(
            observation, assessment, form, workload, recovery,
            baseline_dev,
        )

        return SessionReport(
            athlete_token=observation.athlete_token,
            assessment=assessment,
            coach_messages=coach_messages,
            trainer_notes=trainer_notes,
            physician_alert=physician_alert,
        )

    # -- internals ------------------------------------------------------

    def _build_coach_messages(
        self,
        obs: AthleteObservation,
        a: PerformanceAssessment,
    ) -> list[CoachMessage]:
        msgs: list[CoachMessage] = []
        tok = obs.athlete_token
        if a.risk_band == "hold":
            msgs.append(CoachMessage(
                athlete_token=tok,
                text=(
                    "Form patterns deviating from the athlete's "
                    "own baseline this session. Consider holding "
                    "from the next high-load drill — trainer "
                    "review recommended."
                ),
            ))
        elif a.risk_band == "monitor":
            msgs.append(CoachMessage(
                athlete_token=tok,
                text=(
                    "Form asymmetry trending above baseline this "
                    "session. Monitor across the next few "
                    "sessions; trainer review recommended."
                ),
            ))
        return msgs

    def _build_trainer_notes(
        self,
        obs: AthleteObservation,
        a: PerformanceAssessment,
        form: float,
        workload: float,
        recovery: float,
    ) -> list[TrainerNote]:
        notes: list[TrainerNote] = []
        tok = obs.athlete_token
        b = self._bands

        if form < b.channel_hold:
            notes.append(TrainerNote(
                athlete_token=tok,
                text=(
                    f"Form asymmetry persisted across this session "
                    f"(safety {form:.2f}). Range of motion + "
                    f"loading review recommended before next "
                    f"high-intensity session."
                ),
            ))
        elif form < b.channel_monitor:
            notes.append(TrainerNote(
                athlete_token=tok,
                text=(
                    f"Form asymmetry above baseline "
                    f"(safety {form:.2f}). Monitor across upcoming "
                    f"sessions."
                ),
            ))

        if workload < b.channel_hold:
            notes.append(TrainerNote(
                athlete_token=tok,
                text=(
                    f"Acute workload spiked above chronic baseline "
                    f"(safety {workload:.2f}). Adjust loading for "
                    f"the next session."
                ),
            ))
        elif workload < b.channel_monitor:
            notes.append(TrainerNote(
                athlete_token=tok,
                text=(
                    f"Workload index above typical baseline "
                    f"(safety {workload:.2f}). RPE check + monitor."
                ),
            ))

        if recovery < b.channel_hold:
            notes.append(TrainerNote(
                athlete_token=tok,
                text=(
                    f"Post-effort HR-recovery weak this session "
                    f"(safety {recovery:.2f}). Consider lighter "
                    f"loading; fatigue level merits trainer "
                    f"attention."
                ),
            ))
        elif recovery < b.channel_monitor:
            notes.append(TrainerNote(
                athlete_token=tok,
                text=(
                    f"Recovery HR-drop trending below athlete "
                    f"baseline (safety {recovery:.2f}). Monitor."
                ),
            ))

        return notes

    def _maybe_build_physician_alert(
        self,
        obs: AthleteObservation,
        a: PerformanceAssessment,
        form: float,
        workload: float,
        recovery: float,
        baseline_dev: float,
    ) -> PhysicianAlert | None:
        b = self._bands

        # PhysicianAlert is gated: it only fires when the
        # overall AND baseline-deviation are both below
        # threshold. Single-channel signals reach the
        # trainer but not the physician.
        if (
            a.overall >= b.physician_alert_overall
            or baseline_dev >= b.physician_alert_baseline_deviation
        ):
            return None

        # Build a clinical-observation-grounded text and a
        # reasoning trace. The text uses physician-permissible
        # vocabulary (gait asymmetry, flexion, fatigue).
        text = (
            "Multi-channel deviation from athlete baseline "
            f"this session (overall safety {a.overall:.2f}, "
            f"baseline-deviation safety {baseline_dev:.2f}). "
            "Form asymmetry + workload + recovery patterns "
            "co-deviated. Clinical review before next high-"
            "load session."
        )
        trace = (
            f"{FORM_SIG_VERSION} → form {form:.3f}; "
            f"{WORKLOAD_SIG_VERSION} → workload {workload:.3f}; "
            f"{RECOVERY_SIG_VERSION} → recovery {recovery:.3f}; "
            f"baseline_deviation @ {baseline_dev:.3f}."
        )
        return PhysicianAlert(
            athlete_token=obs.athlete_token,
            text=text,
            reasoning_trace=trace,
        )
