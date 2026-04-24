"""ClinicalPreTriageEngine — the main telemedicine engine.

Sibling of the prior engines. Takes one ``PatientObservation``
and produces one ``PreTriageReport`` containing:
- a ``PreTriageAssessment`` (per-channel scores + escalation
  recommendation)
- zero-or-more ``ClinicianAlert`` records, each carrying
  grounded alternative explanations + a reasoning-trace
  string + references to signature_version tagged readings.

Default-to-schedule. No diagnosis. No treatment
recommendation. No regulatory over-claim. See
docs/PHILOSOPHY.md.
"""

from __future__ import annotations

from ..core.enums import CaptureQuality, ChannelKind, EscalationRecommendation
from ..core.models import (
    AlternativeExplanation,
    ChannelReading,
    ClinicianAlert,
    PatientObservation,
    PreTriageAssessment,
    PreTriageReport,
)
from ..signatures.acoustic_strain import compute_acoustic
from ..signatures.cardiac_readings import compute_cardiac
from ..signatures.postural_stability import compute_postural
from ..signatures.respiratory_readings import compute_respiratory
from .adult_clinical_bands import DEFAULT_BANDS, AdultClinicalBands


# Per-channel weights for the overall score fusion.
# Cardiac + respiratory weighted highest because they're
# the most reliable pre-screening signals; acoustic is
# supportive; postural is lowest (brief window, noisy).
_CHANNEL_WEIGHTS: dict[str, float] = {
    "cardiac":     0.35,
    "respiratory": 0.30,
    "acoustic":    0.20,
    "postural":    0.15,
}


_QUALITY_CONFIDENCE: dict[CaptureQuality, float] = {
    "good":    1.0,
    "noisy":   0.7,
    "partial": 0.5,
}


class ClinicalPreTriageEngine:
    """Produce a pre-triage report from one patient submission."""

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        bands: AdultClinicalBands | None = None,
    ) -> None:
        w = dict(weights or _CHANNEL_WEIGHTS)
        total = sum(w.values())
        if total <= 0:
            raise ValueError("weight total must be positive")
        self._weights = {k: v / total for k, v in w.items()}
        self._bands = bands or DEFAULT_BANDS

    # -- public API -----------------------------------------------------

    def review(self, obs: PatientObservation) -> PreTriageReport:
        b = self._bands

        card_reading, card_alts = compute_cardiac(obs.vitals_samples)
        resp_reading, resp_alts = compute_respiratory(
            obs.vitals_samples, obs.cough_samples, obs.window_duration_s,
        )
        acou_reading, acou_alts = compute_acoustic(obs.acoustic_samples)
        post_reading, post_alts = compute_postural(obs.posture_samples)

        conf = _QUALITY_CONFIDENCE[obs.capture_quality]
        cardiac = card_reading.value * conf + 1.0 * (1.0 - conf)
        respiratory = resp_reading.value * conf + 1.0 * (1.0 - conf)
        acoustic = acou_reading.value * conf + 1.0 * (1.0 - conf)
        postural = post_reading.value * conf + 1.0 * (1.0 - conf)

        overall = (
            self._weights["cardiac"] * cardiac
            + self._weights["respiratory"] * respiratory
            + self._weights["acoustic"] * acoustic
            + self._weights["postural"] * postural
        )
        overall = max(0.0, min(1.0, overall))

        # Mortal-sign-style override: any channel below the
        # urgent band forces overall into the urgent_review
        # tier. The library never masks an urgent channel
        # behind a high average.
        channel_urgent = (
            cardiac < b.channel_urgent
            or respiratory < b.channel_urgent
            or acoustic < b.channel_urgent
            or postural < b.channel_urgent
        )
        if channel_urgent:
            overall = min(overall, b.overall_urgent - 0.01)

        # Channel-schedule gate: any channel below the
        # schedule threshold prevents the self_care tier.
        # The library refuses to tell a clinician
        # "self_care" when any single channel is asking
        # for review.
        channel_schedule_fired = (
            cardiac < b.channel_schedule
            or respiratory < b.channel_schedule
            or acoustic < b.channel_schedule
            or postural < b.channel_schedule
        )

        # Self-report gate: any reported symptom (chest
        # pain, shortness of breath, dizziness, fever,
        # persistent cough) also prevents self_care. Self-
        # reported symptoms are the patient's own concern —
        # the library defers to the clinician.
        any_symptom = bool(obs.self_report.as_list())

        # Default-to-schedule — self_care only when the
        # overall is clearly in the high band AND no
        # channel fired AND the patient reported no symptoms.
        recommendation: EscalationRecommendation
        if overall < b.overall_urgent:
            recommendation = "urgent_review"
        elif (
            overall >= b.overall_self_care
            and not channel_schedule_fired
            and not any_symptom
        ):
            recommendation = "self_care"
        else:
            recommendation = "schedule"

        assessment = PreTriageAssessment(
            patient_token=obs.patient_token,
            cardiac_safety=round(card_reading.value, 3),
            respiratory_safety=round(resp_reading.value, 3),
            acoustic_safety=round(acou_reading.value, 3),
            postural_safety=round(post_reading.value, 3),
            overall=round(overall, 3),
            recommendation=recommendation,
        )

        alerts = self._alerts_for(
            obs,
            card_reading, card_alts,
            resp_reading, resp_alts,
            acou_reading, acou_alts,
            post_reading, post_alts,
        )

        return PreTriageReport(
            patient_token=obs.patient_token,
            assessment=assessment,
            alerts=alerts,
            readings=[card_reading, resp_reading, acou_reading, post_reading],
            reported_symptoms=obs.self_report.as_list(),
        )

    # -- internals ------------------------------------------------------

    def _alerts_for(
        self,
        obs: PatientObservation,
        card_reading: ChannelReading,
        card_alts: tuple[AlternativeExplanation, ...],
        resp_reading: ChannelReading,
        resp_alts: tuple[AlternativeExplanation, ...],
        acou_reading: ChannelReading,
        acou_alts: tuple[AlternativeExplanation, ...],
        post_reading: ChannelReading,
        post_alts: tuple[AlternativeExplanation, ...],
    ) -> list[ClinicianAlert]:
        alerts: list[ClinicianAlert] = []
        b = self._bands
        tok = obs.patient_token

        channels: list[tuple[
            ChannelKind, ChannelReading,
            tuple[AlternativeExplanation, ...], str,
        ]] = [
            ("cardiac", card_reading, card_alts,
             "cardiac_readings median HR outside adult reference band"),
            ("respiratory", resp_reading, resp_alts,
             "respiratory_readings median RR or cough frequency outside band"),
            ("acoustic", acou_reading, acou_alts,
             "acoustic_strain clarity-weighted mean strain elevated"),
            ("postural", post_reading, post_alts,
             "postural_stability sway elevated / balance steadiness low"),
        ]

        for kind, reading, alts, trace_tail in channels:
            if reading.value < b.channel_urgent:
                # Urgent — the library only fires urgent when
                # it also has grounded alternatives to attach.
                # Defensive: if the signature produced no
                # alternatives (shouldn't happen for a
                # below-urgent reading), the engine refuses
                # to fire rather than construct a guard-
                # violating alert.
                if not alts:
                    continue
                alerts.append(self._alert(
                    tok, kind, "urgent_review",
                    self._text_for(kind, reading, "urgent"),
                    alts,
                    self._reasoning_trace(reading, trace_tail),
                    reading.value,
                ))
            elif reading.value < b.channel_schedule:
                # Schedule — same grounded-alternative
                # contract.
                if not alts:
                    continue
                alerts.append(self._alert(
                    tok, kind, "schedule",
                    self._text_for(kind, reading, "schedule"),
                    alts,
                    self._reasoning_trace(reading, trace_tail),
                    reading.value,
                ))
        return alerts

    @staticmethod
    def _text_for(
        kind: ChannelKind,
        reading: ChannelReading,
        tier: str,
    ) -> str:
        urgency = (
            "clearly outside reference band"
            if tier == "urgent"
            else "below typical reference band"
        )
        if kind == "cardiac":
            return (
                f"Cardiac readings {urgency} in this pre-consult "
                f"window (signature safety {reading.value:.2f}). "
                "Grounded alternatives follow; clinician review "
                "before the teleconsult."
            )
        if kind == "respiratory":
            return (
                f"Respiratory readings {urgency} in this window "
                f"(signature safety {reading.value:.2f}). Grounded "
                "alternatives follow; clinician review before the "
                "teleconsult."
            )
        if kind == "acoustic":
            return (
                f"Acoustic-strain readings {urgency} during the "
                f"sustained-vowel portion (signature safety "
                f"{reading.value:.2f}). Grounded alternatives "
                "follow."
            )
        # postural
        return (
            f"Postural-stability readings {urgency} during the "
            f"stand-steady portion (signature safety "
            f"{reading.value:.2f}). Grounded alternatives follow."
        )

    @staticmethod
    def _reasoning_trace(reading: ChannelReading, trace_tail: str) -> str:
        return (
            f"{reading.signature_version} → value {reading.value:.3f}; "
            f"{trace_tail}."
        )

    @staticmethod
    def _alert(
        patient_token: str,
        channel: ChannelKind,
        recommendation: EscalationRecommendation,
        text: str,
        alts: tuple[AlternativeExplanation, ...],
        reasoning_trace: str,
        observed_value: float,
    ) -> ClinicianAlert:
        return ClinicianAlert(
            patient_token=patient_token,
            channel=channel,
            recommendation=recommendation,
            text=text,
            alternative_explanations=alts,
            reasoning_trace=reasoning_trace,
            observed_value=observed_value,
        )
