"""SiteSafetyEngine — the main site-monitoring engine.

Sibling of the prior monitoring engines. Takes a list of
``WorkerObservation`` records + site conditions and produces
a ``SiteReport`` with a ``SafetyScore`` and zero-or-more
``SafetyOfficerAlert`` entries per observation.

Observation-only, advisory-only. Never commands work
stoppage, dispatches emergency services, diagnoses clinical
conditions, pathologizes the worker, or produces
performance-metric / discipline-pipeline output. See
docs/PHILOSOPHY.md for the five boundaries.
"""

from __future__ import annotations

from ..core.enums import AlertKind, AlertLevel, SiteCondition
from ..core.models import (
    SafetyOfficerAlert,
    SafetyScore,
    SiteReport,
    WorkerObservation,
)
from ..signatures.fatigue_gait import compute_fatigue_safety
from ..signatures.heat_stress import compute_heat_safety
from ..signatures.lifting_posture import compute_lifting_safety
from ..signatures.ppe_compliance import compute_ppe_compliance
from .safety_bands import DEFAULT_BANDS, SafetyBands


# Channel weights. PPE weighted highest because it's the
# most reliable signal + the most regulated; heat + lifting
# weighted moderately; fatigue is noisier so lowest.
_CHANNEL_WEIGHTS: dict[str, float] = {
    "ppe": 0.4,
    "lifting": 0.25,
    "heat": 0.2,
    "fatigue": 0.15,
}


# Site conditions scale the weight of channels that depend
# on good visibility.
_CONDITION_CONFIDENCE: dict[SiteCondition, float] = {
    "clear": 1.0,
    "dusty": 0.8,
    "rainy": 0.7,
    "low_light": 0.6,
}


class SiteSafetyEngine:
    """Score a list of worker-observations + emit officer alerts."""

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        bands: SafetyBands | None = None,
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
        site_id: str,
        observations: list[WorkerObservation],
    ) -> SiteReport:
        if not observations:
            return SiteReport(
                site_id=site_id,
                scores=[],
                alerts=[
                    SafetyOfficerAlert(
                        worker_token="-",
                        kind="calibration",
                        level="watch",
                        text=(
                            "No worker observations recorded on this "
                            "pass. Safety officer: verify the site "
                            "sensor hub is online before relying on "
                            "the next pass."
                        ),
                    )
                ],
            )

        scores: list[SafetyScore] = []
        alerts: list[SafetyOfficerAlert] = []
        for obs in observations:
            score, obs_alerts = self._review_one(obs)
            scores.append(score)
            alerts.extend(obs_alerts)
        return SiteReport(site_id=site_id, scores=scores, alerts=alerts)

    # -- internals ------------------------------------------------------

    def _review_one(
        self,
        obs: WorkerObservation,
    ) -> tuple[SafetyScore, list[SafetyOfficerAlert]]:
        wtok = obs.worker_token

        ppe = compute_ppe_compliance(obs.ppe_samples, obs.required_ppe)
        lifting = compute_lifting_safety(obs.lifting_samples)
        heat = compute_heat_safety(obs.thermal_samples)
        fatigue = compute_fatigue_safety(obs.gait_samples)

        # Site-condition confidence weighting — reduces the
        # influence of channels that need clear sight lines
        # (PPE, lifting) when conditions degrade. Heat and
        # fatigue come from wearables, so they stay intact.
        condition_weight = _CONDITION_CONFIDENCE[obs.site_condition]
        # Blend toward neutral 1.0 by (1 - condition_weight).
        ppe_adj = ppe * condition_weight + 1.0 * (1.0 - condition_weight)
        lifting_adj = lifting * condition_weight + 1.0 * (1.0 - condition_weight)

        overall = (
            self._weights["ppe"] * ppe_adj
            + self._weights["lifting"] * lifting_adj
            + self._weights["heat"] * heat
            + self._weights["fatigue"] * fatigue
        )
        overall = max(0.0, min(1.0, overall))

        # Mortal-sign-style override: any channel sitting
        # below its urgent band forces the overall level to
        # urgent (capped at threshold-minus-epsilon). A
        # worker in a single urgent channel should never
        # read as "ok" overall just because other channels
        # compensate in the weighted average.
        b = self._bands
        channel_urgent = (
            (obs.required_ppe and ppe < b.ppe_urgent)
            or (obs.lifting_samples and lifting < b.lifting_urgent)
            or (obs.thermal_samples and heat < b.heat_urgent)
            or (obs.gait_samples and fatigue < b.fatigue_urgent)
        )
        if channel_urgent:
            overall = min(overall, b.overall_urgent - 0.01)

        alert_level = self._overall_to_level(overall)

        score = SafetyScore(
            worker_token=wtok,
            ppe_compliance=round(ppe, 3),
            lifting_safety=round(lifting, 3),
            heat_safety=round(heat, 3),
            fatigue_safety=round(fatigue, 3),
            overall=round(overall, 3),
            alert_level=alert_level,
        )

        alerts = self._alerts_for(obs, score)

        # Calibration / no-data alert.
        if (
            not obs.ppe_samples
            and not obs.lifting_samples
            and not obs.thermal_samples
            and not obs.gait_samples
        ):
            alerts.append(self._alert(
                wtok, "calibration", "watch",
                "No sensor channels recorded for this observation "
                "window. Safety officer: check the zone's camera + "
                "wearable hub before the next pass.",
            ))

        return score, alerts

    def _overall_to_level(self, overall: float) -> AlertLevel:
        b = self._bands
        if overall < b.overall_urgent:
            return "urgent"
        if overall < b.overall_watch:
            return "watch"
        return "ok"

    def _alerts_for(
        self,
        obs: WorkerObservation,
        score: SafetyScore,
    ) -> list[SafetyOfficerAlert]:
        alerts: list[SafetyOfficerAlert] = []
        b = self._bands
        wtok = obs.worker_token

        # PPE channel — only surface if the zone actually
        # required PPE (empty required_ppe = no alert).
        if obs.required_ppe:
            if score.ppe_compliance < b.ppe_urgent:
                alerts.append(self._alert(
                    wtok, "ppe", "urgent",
                    f"PPE compliance in this observation window is "
                    f"{score.ppe_compliance:.0%}. Safety officer: "
                    "consider a zone briefing before the next cycle.",
                    observed_value=score.ppe_compliance,
                ))
            elif score.ppe_compliance < b.ppe_watch:
                alerts.append(self._alert(
                    wtok, "ppe", "watch",
                    f"PPE compliance at {score.ppe_compliance:.0%} — "
                    "below the comfort band. Safety officer: keep an "
                    "eye on this zone.",
                    observed_value=score.ppe_compliance,
                ))

        # Lifting channel.
        if obs.lifting_samples:
            if score.lifting_safety < b.lifting_urgent:
                alerts.append(self._alert(
                    wtok, "lifting", "urgent",
                    "Repeated unsafe back-flexion at load observed. "
                    "Safety officer: consider a tailgate reminder on "
                    "lift mechanics for this zone.",
                    observed_value=score.lifting_safety,
                ))
            elif score.lifting_safety < b.lifting_watch:
                alerts.append(self._alert(
                    wtok, "lifting", "watch",
                    "Occasional deep back-flexion at load observed. "
                    "Safety officer: monitor lifting form.",
                    observed_value=score.lifting_safety,
                ))

        # Heat channel.
        if obs.thermal_samples:
            if score.heat_safety < b.heat_urgent:
                alerts.append(self._alert(
                    wtok, "heat", "urgent",
                    "Marked heat-stress signature: elevated skin "
                    "temperature with a small skin-ambient "
                    "differential. Safety officer: arrange a cooling "
                    "break for this zone.",
                    observed_value=score.heat_safety,
                ))
            elif score.heat_safety < b.heat_watch:
                alerts.append(self._alert(
                    wtok, "heat", "watch",
                    "Heat-stress signature present. Safety officer: "
                    "consider rotating rest intervals for this zone.",
                    observed_value=score.heat_safety,
                ))

        # Fatigue channel.
        if obs.gait_samples:
            if score.fatigue_safety < b.fatigue_urgent:
                alerts.append(self._alert(
                    wtok, "fatigue", "urgent",
                    "Fatigue signature — pace decline and gait "
                    "asymmetry rising across the shift. Safety "
                    "officer: consider a rotation or break.",
                    observed_value=score.fatigue_safety,
                ))
            elif score.fatigue_safety < b.fatigue_watch:
                alerts.append(self._alert(
                    wtok, "fatigue", "watch",
                    "Mild fatigue signature — gait slightly slower "
                    "and less symmetric than early shift. Safety "
                    "officer: keep in view.",
                    observed_value=score.fatigue_safety,
                ))

        return alerts

    @staticmethod
    def _alert(
        worker_token: str,
        kind: AlertKind,
        level: AlertLevel,
        text: str,
        observed_value: float | None = None,
    ) -> SafetyOfficerAlert:
        return SafetyOfficerAlert(
            worker_token=worker_token,
            kind=kind,
            level=level,
            text=text,
            observed_value=observed_value,
        )
