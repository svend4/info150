"""AvianHealthEngine — the main avian-monitoring engine.

Sibling of the prior monitoring engines. Takes one
``BirdObservation`` and produces a per-station
``StationReport`` with one ``AvianHealthScore`` and
zero-or-more ``OrnithologistAlert`` records.

Acoustic-first weighting (call-presence + distress > visual
+ thermal). Mortality-cluster + thermal channels
deliberately pair into a single combined alert when both
fire, surfaced as a "candidate mortality cluster — sampling
recommended" framing — never as flu / outbreak language.

See docs/PHILOSOPHY.md.
"""

from __future__ import annotations

from ..core.enums import (
    AlertKind,
    AlertLevel,
    MAX_AVIAN_SMS_CHARS,
)
from ..core.models import (
    BirdObservation,
    OrnithologistAlert,
    StationReport,
)
from ..core.models import AvianHealthScore
from ..signatures.call_presence import compute_call_presence_safety
from ..signatures.distress_rate import compute_distress_safety
from ..signatures.febrile_thermal import compute_febrile_thermal_safety
from ..signatures.mortality_cluster import compute_mortality_cluster_safety
from ..signatures.wingbeat_vitals import compute_wingbeat_safety


# Acoustic-first weighting.
_CHANNEL_WEIGHTS: dict[str, float] = {
    "call_presence":     0.30,
    "distress":          0.25,
    "vitals":            0.15,
    "thermal":           0.15,
    "mortality_cluster": 0.15,
}


# Per-channel alert thresholds.
_CHANNEL_URGENT: float = 0.35
_CHANNEL_WATCH: float = 0.65


# Overall fused thresholds.
_OVERALL_URGENT: float = 0.45
_OVERALL_WATCH: float = 0.70


class AvianHealthEngine:
    """Score one observation + emit ornithologist alerts."""

    def __init__(
        self,
        weights: dict[str, float] | None = None,
    ) -> None:
        w = dict(weights or _CHANNEL_WEIGHTS)
        total = sum(w.values())
        if total <= 0:
            raise ValueError("weight total must be positive")
        self._weights = {k: v / total for k, v in w.items()}

    # -- public API -----------------------------------------------------

    def review(self, observation: BirdObservation) -> StationReport:
        call = compute_call_presence_safety(
            observation.call_samples,
            observation.expected_species,
        )
        distress = compute_distress_safety(observation.call_samples)
        vitals = compute_wingbeat_safety(observation.wingbeat_samples)
        thermal = compute_febrile_thermal_safety(
            observation.thermal_samples,
        )
        mortality = compute_mortality_cluster_safety(
            observation.dead_bird_candidates,
        )

        overall = (
            self._weights["call_presence"] * call
            + self._weights["distress"] * distress
            + self._weights["vitals"] * vitals
            + self._weights["thermal"] * thermal
            + self._weights["mortality_cluster"] * mortality
        )
        overall = max(0.0, min(1.0, overall))

        # Mortal-sign-style override: any channel below the
        # urgent band forces overall into the urgent band.
        channel_urgent = (
            call < _CHANNEL_URGENT
            or distress < _CHANNEL_URGENT
            or vitals < _CHANNEL_URGENT
            or thermal < _CHANNEL_URGENT
            or mortality < _CHANNEL_URGENT
        )
        if channel_urgent:
            overall = min(overall, _OVERALL_URGENT - 0.01)

        if overall < _OVERALL_URGENT:
            level: AlertLevel = "urgent"
        elif overall < _OVERALL_WATCH:
            level = "watch"
        else:
            level = "ok"

        score = AvianHealthScore(
            obs_token=observation.obs_token,
            call_presence_safety=round(call, 3),
            distress_safety=round(distress, 3),
            vitals_safety=round(vitals, 3),
            thermal_safety=round(thermal, 3),
            mortality_cluster_safety=round(mortality, 3),
            overall=round(overall, 3),
            alert_level=level,
        )

        alerts = self._alerts_for(observation, score)
        return StationReport(
            station_id=observation.station_id,
            scores=[score],
            alerts=alerts,
        )

    # -- internals ------------------------------------------------------

    def _alerts_for(
        self,
        obs: BirdObservation,
        score: AvianHealthScore,
    ) -> list[OrnithologistAlert]:
        alerts: list[OrnithologistAlert] = []
        loc = obs.location_handle
        sid = obs.station_id

        # Call-presence channel.
        if score.call_presence_safety < _CHANNEL_URGENT:
            alerts.append(self._alert(
                obs.obs_token, "call_presence", "urgent",
                self._format(
                    "URGENT", sid, loc,
                    "expected calls largely absent across this window",
                ),
                loc, score.call_presence_safety,
            ))
        elif score.call_presence_safety < _CHANNEL_WATCH:
            alerts.append(self._alert(
                obs.obs_token, "call_presence", "watch",
                self._format(
                    "WATCH", sid, loc,
                    "expected calls partially absent across this window",
                ),
                loc, score.call_presence_safety,
            ))

        # Distress channel.
        if score.distress_safety < _CHANNEL_URGENT:
            alerts.append(self._alert(
                obs.obs_token, "distress", "urgent",
                self._format(
                    "URGENT", sid, loc,
                    "distress vocalisations frequent across this window",
                ),
                loc, score.distress_safety,
            ))
        elif score.distress_safety < _CHANNEL_WATCH:
            alerts.append(self._alert(
                obs.obs_token, "distress", "watch",
                self._format(
                    "WATCH", sid, loc,
                    "distress vocalisations elevated this window",
                ),
                loc, score.distress_safety,
            ))

        # Wing-beat-vitals channel.
        if score.vitals_safety < _CHANNEL_URGENT:
            alerts.append(self._alert(
                obs.obs_token, "vitals", "urgent",
                self._format(
                    "URGENT", sid, loc,
                    "wing-beat frequency outside reference band",
                ),
                loc, score.vitals_safety,
            ))
        elif score.vitals_safety < _CHANNEL_WATCH:
            alerts.append(self._alert(
                obs.obs_token, "vitals", "watch",
                self._format(
                    "WATCH", sid, loc,
                    "wing-beat frequency near edge of reference band",
                ),
                loc, score.vitals_safety,
            ))

        # Thermal + mortality channels — combined when both
        # fire to surface the surveillance-trigger framing.
        thermal_urgent = score.thermal_safety < _CHANNEL_URGENT
        mortality_urgent = score.mortality_cluster_safety < _CHANNEL_URGENT
        if thermal_urgent and mortality_urgent:
            alerts.append(self._alert(
                obs.obs_token, "mortality_cluster", "urgent",
                self._format(
                    "URGENT", sid, loc,
                    "candidate mortality cluster — sampling recommended",
                ),
                loc, score.mortality_cluster_safety,
            ))
        else:
            if score.thermal_safety < _CHANNEL_URGENT:
                alerts.append(self._alert(
                    obs.obs_token, "thermal", "urgent",
                    self._format(
                        "URGENT", sid, loc,
                        "elevated body-temp readings across the window",
                    ),
                    loc, score.thermal_safety,
                ))
            elif score.thermal_safety < _CHANNEL_WATCH:
                alerts.append(self._alert(
                    obs.obs_token, "thermal", "watch",
                    self._format(
                        "WATCH", sid, loc,
                        "intermittent elevated body-temp readings",
                    ),
                    loc, score.thermal_safety,
                ))
            if score.mortality_cluster_safety < _CHANNEL_URGENT:
                alerts.append(self._alert(
                    obs.obs_token, "mortality_cluster", "urgent",
                    self._format(
                        "URGENT", sid, loc,
                        "candidate mortality cluster — sampling recommended",
                    ),
                    loc, score.mortality_cluster_safety,
                ))
            elif score.mortality_cluster_safety < _CHANNEL_WATCH:
                alerts.append(self._alert(
                    obs.obs_token, "mortality_cluster", "watch",
                    self._format(
                        "WATCH", sid, loc,
                        "elevated dead-bird candidate count this window",
                    ),
                    loc, score.mortality_cluster_safety,
                ))

        return alerts

    @staticmethod
    def _format(
        tier: str,
        station_id: str,
        location_handle: str,
        body: str,
    ) -> str:
        """Build SMS-budgeted alert text."""
        # Include the station + handle as a short prefix; the
        # body is the channel-specific descriptor.
        prefix = f"{tier} ({station_id}, {location_handle}): "
        suffix = "" if "sampling recommended" in body else (
            " Ornithologist + reserve-vet review."
        )
        msg = f"{prefix}{body}.{suffix}"
        if len(msg) > MAX_AVIAN_SMS_CHARS:
            msg = msg[: MAX_AVIAN_SMS_CHARS - 1] + "…"
        return msg

    @staticmethod
    def _alert(
        obs_token: str,
        kind: AlertKind,
        level: AlertLevel,
        text: str,
        location_handle: str,
        observed_value: float,
    ) -> OrnithologistAlert:
        return OrnithologistAlert(
            obs_token=obs_token,
            kind=kind,
            level=level,
            text=text,
            location_handle=location_handle,
            observed_value=observed_value,
        )
