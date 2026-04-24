"""PoolWatchEngine — the main aquatic-safety engine.

Sibling of the prior monitoring engines. Takes a list of
``SwimmerObservation`` records and produces a ``PoolReport``
with per-swimmer ``AquaticScore`` and zero-or-more
``LifeguardAlert`` records per swimmer.

Observation-only, advisory-only. The library's action space
stops at the lifeguard's pendant. See docs/PHILOSOPHY.md
for the seven boundaries — especially no-false-reassurance,
the new one in this sibling.
"""

from __future__ import annotations

from ..core.enums import AlertKind, AlertLevel, PoolCondition
from ..core.models import (
    AquaticScore,
    LifeguardAlert,
    PoolReport,
    SwimmerObservation,
)
from ..signatures.absent_swimmer import compute_absence_safety
from ..signatures.idr_posture import compute_idr_safety
from ..signatures.submersion_duration import compute_submersion_safety
from ..signatures.surface_distress import compute_distress_safety
from .drowning_bands import DEFAULT_BANDS, DrowningBands


# Channel weights for overall fusion. Submersion is the
# dominant signal in the drowning literature so it's weighted
# highest; IDR is the confirming pattern; absent-swimmer is
# a high-reliability channel when it fires; surface-distress
# is the early-warning channel, weighted lowest to avoid
# false-positive over-sensitivity.
_CHANNEL_WEIGHTS: dict[str, float] = {
    "submersion": 0.4,
    "idr": 0.25,
    "absent": 0.2,
    "distress": 0.15,
}


# Pool-condition confidence scale. Turbid water + sun glare
# + crowded pools all reduce the engine's confidence in the
# visible-light channels; the library compensates by blending
# the IDR + distress + submersion scores toward neutral when
# conditions degrade. Note: this does NOT make the pool
# "safer" — it means the library has less to say, which is
# precisely why the no-false-reassurance boundary matters.
_CONDITION_CONFIDENCE: dict[PoolCondition, float] = {
    "clear": 1.0,
    "turbid": 0.75,
    "sun_glare": 0.7,
    "crowded": 0.85,
}


class PoolWatchEngine:
    """Score a list of swimmer observations + emit lifeguard alerts."""

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        bands: DrowningBands | None = None,
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
        pool_id: str,
        observations: list[SwimmerObservation],
    ) -> PoolReport:
        if not observations:
            return PoolReport(
                pool_id=pool_id,
                scores=[],
                alerts=[
                    LifeguardAlert(
                        swimmer_token="-",
                        kind="calibration",
                        level="watch",
                        text=(
                            "No swimmer observations recorded on "
                            "this cycle. Lifeguard: verify the pool "
                            "sensor hub is online before the next "
                            "cycle."
                        ),
                    )
                ],
            )

        scores: list[AquaticScore] = []
        alerts: list[LifeguardAlert] = []
        for obs in observations:
            score, obs_alerts = self._review_one(obs)
            scores.append(score)
            alerts.extend(obs_alerts)
        return PoolReport(pool_id=pool_id, scores=scores, alerts=alerts)

    # -- internals ------------------------------------------------------

    def _review_one(
        self,
        obs: SwimmerObservation,
    ) -> tuple[AquaticScore, list[LifeguardAlert]]:
        stok = obs.swimmer_token
        b = self._bands

        submersion = compute_submersion_safety(
            obs.submersion_samples,
            watch_threshold_s=b.submersion_watch_s,
            urgent_threshold_s=b.submersion_urgent_s,
        )
        idr = compute_idr_safety(obs.surface_samples)
        absent = compute_absence_safety(obs.presence_samples)
        distress = compute_distress_safety(obs.surface_samples)

        # Condition confidence blends visible-light channels
        # (idr + distress) toward neutral 1.0 when water /
        # light conditions degrade. Submersion + absence
        # come from tracker state, less condition-sensitive.
        conf = _CONDITION_CONFIDENCE[obs.pool_condition]
        idr_adj = idr * conf + 1.0 * (1.0 - conf)
        distress_adj = distress * conf + 1.0 * (1.0 - conf)

        overall = (
            self._weights["submersion"] * submersion
            + self._weights["idr"] * idr_adj
            + self._weights["absent"] * absent
            + self._weights["distress"] * distress_adj
        )
        overall = max(0.0, min(1.0, overall))

        # Mortal-sign-style override: submersion past the
        # critical band dominates everything. A swimmer
        # submerged 30+ s should never register "ok" overall
        # because other channels look fine.
        channel_urgent = (
            submersion < b.submersion_urgent
            or idr < b.idr_urgent
            or absent < b.absent_urgent
            or distress < b.distress_urgent
        )
        if channel_urgent:
            overall = min(overall, b.overall_urgent - 0.01)

        alert_level = self._overall_to_level(overall)
        score = AquaticScore(
            swimmer_token=stok,
            submersion_safety=round(submersion, 3),
            idr_safety=round(idr, 3),
            absent_safety=round(absent, 3),
            distress_safety=round(distress, 3),
            overall=round(max(0.0, min(1.0, overall)), 3),
            alert_level=alert_level,
        )

        alerts = self._alerts_for(obs, score)

        # Calibration: all channels empty.
        if (
            not obs.submersion_samples
            and not obs.surface_samples
            and not obs.presence_samples
        ):
            alerts.append(self._alert(
                stok, "calibration", "watch",
                f"No sensor data for swimmer {stok} in this cycle. "
                "Lifeguard: check the zone's sensor coverage before "
                "the next cycle.",
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
        obs: SwimmerObservation,
        score: AquaticScore,
    ) -> list[LifeguardAlert]:
        alerts: list[LifeguardAlert] = []
        b = self._bands
        stok = obs.swimmer_token

        # Submersion channel.
        if obs.submersion_samples:
            if score.submersion_safety < b.submersion_urgent:
                alerts.append(self._alert(
                    stok, "submersion", "urgent",
                    f"Swimmer {stok} zone {obs.zone}: sustained "
                    "submersion across this cycle. Lifeguard: "
                    "immediate attention warranted.",
                    observed_value=score.submersion_safety,
                ))
            elif score.submersion_safety < b.submersion_watch:
                alerts.append(self._alert(
                    stok, "submersion", "watch",
                    f"Swimmer {stok} zone {obs.zone}: submersion "
                    "approaching the watch band. Lifeguard: "
                    "keep the zone in view.",
                    observed_value=score.submersion_safety,
                ))

        # IDR channel.
        if obs.surface_samples:
            if score.idr_safety < b.idr_urgent:
                alerts.append(self._alert(
                    stok, "idr", "urgent",
                    f"Swimmer {stok} zone {obs.zone}: IDR-consistent "
                    "posture across the cycle (vertical body, head "
                    "low, non-rhythmic motion). Lifeguard: "
                    "immediate attention warranted.",
                    observed_value=score.idr_safety,
                ))
            elif score.idr_safety < b.idr_watch:
                alerts.append(self._alert(
                    stok, "idr", "watch",
                    f"Swimmer {stok} zone {obs.zone}: intermittent "
                    "IDR-consistent posture. Lifeguard: keep the "
                    "zone in view.",
                    observed_value=score.idr_safety,
                ))

        # Absent-swimmer channel.
        if obs.presence_samples:
            if score.absent_safety < b.absent_urgent:
                alerts.append(self._alert(
                    stok, "absent", "urgent",
                    f"Swimmer {stok} zone {obs.zone}: extended "
                    "tracker absence — entered the zone but has "
                    "not been observed for an unexpectedly long "
                    "window. Lifeguard: immediate attention "
                    "warranted.",
                    observed_value=score.absent_safety,
                ))
            elif score.absent_safety < b.absent_watch:
                alerts.append(self._alert(
                    stok, "absent", "watch",
                    f"Swimmer {stok} zone {obs.zone}: tracker gap "
                    "rising. Lifeguard: keep the zone in view.",
                    observed_value=score.absent_safety,
                ))

        # Surface-distress channel.
        if obs.surface_samples:
            if score.distress_safety < b.distress_urgent:
                alerts.append(self._alert(
                    stok, "distress", "urgent",
                    f"Swimmer {stok} zone {obs.zone}: sustained "
                    "low head-above-water across the cycle. "
                    "Lifeguard: immediate attention warranted.",
                    observed_value=score.distress_safety,
                ))
            elif score.distress_safety < b.distress_watch:
                alerts.append(self._alert(
                    stok, "distress", "watch",
                    f"Swimmer {stok} zone {obs.zone}: head is low "
                    "on the water line intermittently. Lifeguard: "
                    "keep the zone in view.",
                    observed_value=score.distress_safety,
                ))

        return alerts

    @staticmethod
    def _alert(
        swimmer_token: str,
        kind: AlertKind,
        level: AlertLevel,
        text: str,
        observed_value: float | None = None,
    ) -> LifeguardAlert:
        return LifeguardAlert(
            swimmer_token=swimmer_token,
            kind=kind,
            level=level,
            text=text,
            observed_value=observed_value,
        )
