"""VenueMonitorEngine — the main crowd-safety engine.

Sibling of the prior monitoring engines. Takes a list of
``ZoneObservation`` records and produces a ``VenueReport``
with per-zone ``CrowdScore`` and zero-or-more
``VenueOpsAlert`` per zone.

Observation-only. Advisory-only. Zone-level, never
individual-level. Never diagnoses, never dispatches, never
evacuates, never produces dramatic language. See
docs/PHILOSOPHY.md for the six boundaries.
"""

from __future__ import annotations

from ..core.enums import AlertKind, AlertLevel
from ..core.models import (
    CrowdScore,
    VenueOpsAlert,
    VenueReport,
    ZoneObservation,
)
from ..signatures.density_signature import compute_density_safety
from ..signatures.flow_signature import compute_flow_safety
from ..signatures.medical_in_crowd import compute_medical_safety
from ..signatures.pressure_wave import compute_pressure_safety
from .crowd_safety_bands import DEFAULT_BANDS, CrowdSafetyBands


# Channel weights for overall fusion. Pressure is the
# highest-confidence crush-precursor channel (Helbing 2007)
# so it's weighted highest; density alone is known to
# mislead, so it's weighted moderately; flow catches the
# specific compaction-into-choke-point pattern; medical-in-
# crowd is separate from crush risk but demands its own
# alert channel.
_CHANNEL_WEIGHTS: dict[str, float] = {
    "pressure": 0.35,
    "density": 0.25,
    "flow": 0.25,
    "medical": 0.15,
}


class VenueMonitorEngine:
    """Score a list of zone observations + emit venue-ops alerts."""

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        bands: CrowdSafetyBands | None = None,
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
        venue_id: str,
        zones: list[ZoneObservation],
    ) -> VenueReport:
        if not zones:
            return VenueReport(
                venue_id=venue_id,
                scores=[],
                alerts=[
                    VenueOpsAlert(
                        zone_id="-",
                        kind="calibration",
                        level="watch",
                        text=(
                            "No zone observations recorded on this "
                            "pass. Venue-ops: verify the zone "
                            "sensor hub is online before the next "
                            "pass."
                        ),
                    )
                ],
            )

        scores: list[CrowdScore] = []
        alerts: list[VenueOpsAlert] = []
        for zone in zones:
            score, zone_alerts = self._review_zone(zone)
            scores.append(score)
            alerts.extend(zone_alerts)
        return VenueReport(venue_id=venue_id, scores=scores, alerts=alerts)

    # -- internals ------------------------------------------------------

    def _review_zone(
        self,
        zone: ZoneObservation,
    ) -> tuple[CrowdScore, list[VenueOpsAlert]]:
        zid = zone.zone_id

        density = compute_density_safety(
            zone.density_readings, zone.zone_kind,
        )
        flow = compute_flow_safety(zone.flow_samples)
        pressure = compute_pressure_safety(zone.pressure_readings)
        medical = compute_medical_safety(zone.medical_candidates)

        overall = (
            self._weights["pressure"] * pressure
            + self._weights["density"] * density
            + self._weights["flow"] * flow
            + self._weights["medical"] * medical
        )

        # Mortal-sign-style override: any channel in urgent
        # band forces overall to urgent. A single urgent
        # channel should not be masked by compensating
        # channels in a weighted mean.
        b = self._bands
        channel_urgent = (
            density < b.density_urgent
            or flow < b.flow_urgent
            or pressure < b.pressure_urgent
            or medical < b.medical_urgent
        )
        if channel_urgent:
            overall = min(overall, b.overall_urgent - 0.01)

        alert_level = self._overall_to_level(overall)
        score = CrowdScore(
            zone_id=zid,
            density_safety=round(density, 3),
            flow_safety=round(flow, 3),
            pressure_safety=round(pressure, 3),
            medical_safety=round(medical, 3),
            overall=round(max(0.0, min(1.0, overall)), 3),
            alert_level=alert_level,
        )

        alerts = self._alerts_for(zone, score)

        # Calibration case: all channels empty.
        if (
            not zone.density_readings
            and not zone.flow_samples
            and not zone.pressure_readings
            and not zone.medical_candidates
        ):
            alerts.append(self._alert(
                zid, "calibration", "watch",
                "No sensor channels recorded for this zone in the "
                "current window. Venue-ops: check the zone's camera "
                "+ pressure-sensor hub.",
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
        zone: ZoneObservation,
        score: CrowdScore,
    ) -> list[VenueOpsAlert]:
        alerts: list[VenueOpsAlert] = []
        b = self._bands
        zid = zone.zone_id

        if zone.density_readings:
            if score.density_safety < b.density_urgent:
                alerts.append(self._alert(
                    zid, "density", "urgent",
                    f"Zone {zid} density in the near-critical band "
                    f"({self._density_text(zone)}). Venue-ops: "
                    "consider metering entry and reviewing the "
                    "pressure + flow channels.",
                    observed_value=score.density_safety,
                ))
            elif score.density_safety < b.density_watch:
                alerts.append(self._alert(
                    zid, "density", "watch",
                    f"Zone {zid} density elevated "
                    f"({self._density_text(zone)}). Venue-ops: "
                    "keep the zone in view.",
                    observed_value=score.density_safety,
                ))

        if zone.flow_samples:
            if score.flow_safety < b.flow_urgent:
                alerts.append(self._alert(
                    zid, "flow", "urgent",
                    f"Zone {zid} shows sustained unidirectional flow "
                    "with high compaction. Venue-ops: consider "
                    "metering entry at the upstream gate.",
                    observed_value=score.flow_safety,
                ))
            elif score.flow_safety < b.flow_watch:
                alerts.append(self._alert(
                    zid, "flow", "watch",
                    f"Zone {zid} flow compacting. Venue-ops: keep "
                    "the zone in view.",
                    observed_value=score.flow_safety,
                ))

        if zone.pressure_readings:
            if score.pressure_safety < b.pressure_urgent:
                alerts.append(self._alert(
                    zid, "pressure", "urgent",
                    f"Zone {zid} pressure elevated across the "
                    "window. Venue-ops: this is the strongest "
                    "precursor signal the library tracks — "
                    "review density + flow and consider metering "
                    "entry upstream.",
                    observed_value=score.pressure_safety,
                ))
            elif score.pressure_safety < b.pressure_watch:
                alerts.append(self._alert(
                    zid, "pressure", "watch",
                    f"Zone {zid} pressure intermittently elevated. "
                    "Venue-ops: keep the zone in view.",
                    observed_value=score.pressure_safety,
                ))

        if zone.medical_candidates:
            if score.medical_safety < b.medical_urgent:
                alerts.append(self._alert(
                    zid, "medical", "urgent",
                    f"Zone {zid} — one or more anonymous collapsed-"
                    "person candidates. Venue-ops: medic review "
                    "recommended.",
                    observed_value=score.medical_safety,
                ))
            elif score.medical_safety < b.medical_watch:
                alerts.append(self._alert(
                    zid, "medical", "watch",
                    f"Zone {zid} — anonymous medical candidate(s) "
                    "flagged at lower confidence. Venue-ops: "
                    "consider a medic review at the next pass.",
                    observed_value=score.medical_safety,
                ))

        return alerts

    @staticmethod
    def _density_text(zone: ZoneObservation) -> str:
        if not zone.density_readings:
            return "density unknown"
        vals = sorted(r.persons_per_m2 for r in zone.density_readings)
        mid = len(vals) // 2
        if len(vals) % 2:
            median = vals[mid]
        else:
            median = (vals[mid - 1] + vals[mid]) / 2
        return f"median {median:.1f} p/m²"

    @staticmethod
    def _alert(
        zone_id: str,
        kind: AlertKind,
        level: AlertLevel,
        text: str,
        observed_value: float | None = None,
    ) -> VenueOpsAlert:
        return VenueOpsAlert(
            zone_id=zone_id,
            kind=kind,
            level=level,
            text=text,
            observed_value=observed_value,
        )
