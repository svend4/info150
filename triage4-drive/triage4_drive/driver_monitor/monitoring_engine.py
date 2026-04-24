"""DriverMonitoringEngine — the main engine.

Sibling of the triage4 / triage4-fit / triage4-farm /
triage4-rescue engines. Takes one ``DriverObservation`` window
and produces:
- a ``FatigueScore`` (per-channel risk + fused overall +
  alert level)
- zero-or-more ``DispatcherAlert`` records.

Observation → score → alert. No vehicle-control commands.
No cross-session identification. No clinical diagnoses. See
docs/PHILOSOPHY.md for the three boundaries.
"""

from __future__ import annotations

from ..core.enums import AlertKind, AlertLevel
from ..core.models import (
    DispatcherAlert,
    DriverObservation,
    FatigueScore,
)
from ..signatures.eye_closure import compute_perclos, count_microsleeps
from ..signatures.gaze_deviation import compute_distraction_index
from ..signatures.postural_tone import compute_postural_tone_score
from .fatigue_bands import DEFAULT_BANDS, FatigueBands


# Per-channel weights for the overall risk fusion. Drowsiness
# weighted highest because PERCLOS is the most validated
# channel in the literature; incapacitation is rare but a
# positive reading dominates via the mortal-sign-override
# pattern (below).
_CHANNEL_WEIGHTS: dict[str, float] = {
    "perclos": 0.5,
    "distraction": 0.3,
    "incapacitation": 0.2,
}


class DriverMonitoringEngine:
    """Score a single observation window + emit dispatcher alerts."""

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        bands: FatigueBands | None = None,
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
        observation: DriverObservation,
    ) -> tuple[FatigueScore, list[DispatcherAlert]]:
        sid = observation.session_id
        bands = self._bands

        perclos = compute_perclos(observation.eye_samples)
        microsleep_count = count_microsleeps(observation.eye_samples)
        distraction = compute_distraction_index(observation.gaze_samples)
        incapacitation = compute_postural_tone_score(observation.posture_samples)

        overall = (
            self._weights["perclos"] * perclos
            + self._weights["distraction"] * distraction
            + self._weights["incapacitation"] * incapacitation
        )
        # Mortal-sign-style override: a clear incapacitation
        # signal (>= critical threshold) floors the overall at
        # that level regardless of the other channels, because
        # "driver is slumped" is never OK.
        if incapacitation >= bands.incapacitation_critical:
            overall = max(overall, 0.9)
        # Microsleeps are a similar dominant signal — any
        # count elevates overall risk past the critical band.
        if microsleep_count >= bands.microsleep_critical_count:
            overall = max(overall, bands.overall_critical)

        alert_level = self._overall_to_level(overall)
        score = FatigueScore(
            session_id=sid,
            perclos=round(perclos, 3),
            distraction=round(distraction, 3),
            incapacitation=round(incapacitation, 3),
            overall=round(max(0.0, min(1.0, overall)), 3),
            alert_level=alert_level,
        )

        alerts = self._alerts_for(
            sid, perclos, microsleep_count, distraction, incapacitation,
        )

        # If every channel returned 0.0, the upstream calibration
        # layer is empty — surface a calibration info alert so
        # the dispatcher doesn't mistake "no data" for "all OK".
        if (
            not observation.eye_samples
            and not observation.gaze_samples
            and not observation.posture_samples
        ):
            alerts.append(DispatcherAlert(
                session_id=sid,
                kind="calibration",
                level="caution",
                text=(
                    "No sensor channels recorded in this window. "
                    "Check the in-cab camera calibration before relying "
                    "on the next window's fatigue score."
                ),
            ))

        return score, alerts

    # -- internals ------------------------------------------------------

    def _overall_to_level(self, overall: float) -> AlertLevel:
        if overall >= self._bands.overall_critical:
            return "critical"
        if overall >= self._bands.overall_caution:
            return "caution"
        return "ok"

    def _alerts_for(
        self,
        session_id: str,
        perclos: float,
        microsleeps: int,
        distraction: float,
        incapacitation: float,
    ) -> list[DispatcherAlert]:
        alerts: list[DispatcherAlert] = []
        b = self._bands

        # Drowsiness channel — microsleep events escalate to
        # critical directly; otherwise use the PERCLOS bands.
        if microsleeps >= b.microsleep_critical_count:
            alerts.append(self._alert(
                session_id, "drowsiness", "critical",
                f"{microsleeps} microsleep event"
                f"{'' if microsleeps == 1 else 's'} detected in this "
                "window. Strong drowsiness signature — consider a "
                "driver rest break.",
                observed_value=float(microsleeps),
            ))
        elif perclos >= b.perclos_critical:
            alerts.append(self._alert(
                session_id, "drowsiness", "critical",
                f"PERCLOS {perclos:.2f} over this window — well above "
                "the caution band. Consider a driver rest break.",
                observed_value=perclos,
            ))
        elif perclos >= b.perclos_caution:
            alerts.append(self._alert(
                session_id, "drowsiness", "caution",
                f"PERCLOS {perclos:.2f} over this window — into the "
                "caution band. Dispatcher: check in with the driver.",
                observed_value=perclos,
            ))

        # Distraction channel.
        if distraction >= b.distraction_critical:
            alerts.append(self._alert(
                session_id, "distraction", "critical",
                f"Gaze off-road {distraction * 100:.0f} % of this "
                "window. Strong distraction signature — dispatcher "
                "should check in with the driver.",
                observed_value=distraction,
            ))
        elif distraction >= b.distraction_caution:
            alerts.append(self._alert(
                session_id, "distraction", "caution",
                f"Gaze off-road {distraction * 100:.0f} % of this "
                "window. Caution — consider a check-in.",
                observed_value=distraction,
            ))

        # Incapacitation channel.
        if incapacitation >= b.incapacitation_critical:
            alerts.append(self._alert(
                session_id, "incapacitation", "critical",
                "Sustained loss of postural tone detected. "
                "Dispatcher-in-the-loop confirmation required; do "
                "not infer a clinical cause from this channel "
                "alone.",
                observed_value=incapacitation,
            ))
        elif incapacitation >= b.incapacitation_caution:
            alerts.append(self._alert(
                session_id, "incapacitation", "caution",
                "Postural-tone signature suggests possible slump. "
                "Dispatcher: check in with the driver.",
                observed_value=incapacitation,
            ))

        return alerts

    @staticmethod
    def _alert(
        session_id: str,
        kind: AlertKind,
        level: AlertLevel,
        text: str,
        observed_value: float | None = None,
    ) -> DispatcherAlert:
        return DispatcherAlert(
            session_id=session_id,
            kind=kind,
            level=level,
            text=text,
            observed_value=observed_value,
        )
