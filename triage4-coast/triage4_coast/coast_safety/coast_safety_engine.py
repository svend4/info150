"""CoastSafetyEngine — review zones, produce a CoastReport.

Channel rules (deliberately simple thresholds, not ML):

- **density_safety**: 1 − density_pressure.
- **drowning_safety**: in water-zones, (1 − in_water_motion) ×
  density is the risk; everywhere else 1.0.
- **sun_safety**: 1 − sun_intensity, weighted by zone_kind.
- **lost_child_safety**: 0 if ``lost_child_flag`` else 1.
- **overall**: weighted average — drowning 0.35, density 0.25,
  sun 0.25, lost_child 0.15.

Operational posture: alert text never names a medical condition.
"""

from __future__ import annotations

from ..core.enums import AlertLevel, ZoneKind
from ..core.models import (
    CoastOpsAlert,
    CoastReport,
    CoastScore,
    CoastZoneObservation,
)
from .coast_safety_bands import band_for


class CoastSafetyEngine:
    """Coast-strip safety advisor."""

    def review(
        self, *, coast_id: str, zones: list[CoastZoneObservation],
    ) -> CoastReport:
        report = CoastReport(coast_id=coast_id)
        for obs in zones:
            score, alerts = self._review_zone(obs)
            report.scores.append(score)
            report.alerts.extend(alerts)
        return report

    # -- per-zone ----------------------------------------------------------

    def _review_zone(
        self, obs: CoastZoneObservation,
    ) -> tuple[CoastScore, list[CoastOpsAlert]]:
        bands = band_for(obs.zone_kind)

        density_safety = max(0.0, 1.0 - obs.density_pressure)
        drowning_safety = self._drowning_safety(obs)
        sun_safety = self._sun_safety(obs)
        lost_child_safety = 0.0 if obs.lost_child_flag else 1.0
        fall_event_safety = 0.0 if obs.fall_event_flag else 1.0
        stationary_person_safety = max(0.0, 1.0 - obs.stationary_person_signal)
        flow_anomaly_safety = max(0.0, 1.0 - obs.flow_anomaly_signal)
        slip_risk_safety = max(0.0, 1.0 - obs.slip_risk_signal)

        overall = (
            0.25 * drowning_safety
            + 0.20 * density_safety
            + 0.15 * sun_safety
            + 0.10 * lost_child_safety
            + 0.10 * fall_event_safety
            + 0.07 * stationary_person_safety
            + 0.07 * flow_anomaly_safety
            + 0.06 * slip_risk_safety
        )
        overall = max(0.0, min(1.0, overall))

        level: AlertLevel = "ok"
        alerts: list[CoastOpsAlert] = []

        if obs.lost_child_flag:
            level = "urgent"
            alerts.append(CoastOpsAlert(
                zone_id=obs.zone_id, kind="lost_child", level="urgent",
                text="Possible unaccompanied child — visual check requested.",
            ))

        if drowning_safety < bands.drowning_urgent:
            level = "urgent"
            alerts.append(CoastOpsAlert(
                zone_id=obs.zone_id, kind="drowning", level="urgent",
                text=(
                    f"Low in-water motion ({obs.in_water_motion:.2f}) with "
                    f"crowd density ({obs.density_pressure:.2f}) - "
                    "lifeguard scan requested."
                ),
            ))
        elif drowning_safety < bands.drowning_watch:
            level = _max_level(level, "watch")
            alerts.append(CoastOpsAlert(
                zone_id=obs.zone_id, kind="drowning", level="watch",
                text=(
                    f"In-water activity {obs.in_water_motion:.2f} below band "
                    "for the current crowd - keep eyes on the water."
                ),
            ))

        if density_safety < bands.density_urgent:
            level = "urgent"
            alerts.append(CoastOpsAlert(
                zone_id=obs.zone_id, kind="density", level="urgent",
                text=(
                    f"Crowd density {obs.density_pressure:.2f} above urgent "
                    f"band for {obs.zone_kind} zone."
                ),
            ))
        elif density_safety < bands.density_watch:
            level = _max_level(level, "watch")
            alerts.append(CoastOpsAlert(
                zone_id=obs.zone_id, kind="density", level="watch",
                text=(
                    f"Crowd density {obs.density_pressure:.2f} entering watch "
                    f"band for {obs.zone_kind}."
                ),
            ))

        if sun_safety < bands.sun_urgent:
            level = _max_level(level, "watch")
            alerts.append(CoastOpsAlert(
                zone_id=obs.zone_id, kind="sun", level="watch",
                text=(
                    f"Sun intensity {obs.sun_intensity:.2f} high on "
                    f"{obs.zone_kind} - encourage shade / hydration breaks."
                ),
            ))

        # --- Stage-2B channels --------------------------------------
        if obs.fall_event_flag:
            level = "urgent"
            alerts.append(CoastOpsAlert(
                zone_id=obs.zone_id, kind="fall_event", level="urgent",
                text="Fall event reported - send a responder to check.",
            ))

        if stationary_person_safety < bands.stationary_urgent:
            level = "urgent"
            alerts.append(CoastOpsAlert(
                zone_id=obs.zone_id, kind="stationary_person", level="urgent",
                text=(
                    f"Person motionless signal {obs.stationary_person_signal:.2f} - "
                    "visual welfare check requested."
                ),
            ))
        elif stationary_person_safety < bands.stationary_watch:
            level = _max_level(level, "watch")
            alerts.append(CoastOpsAlert(
                zone_id=obs.zone_id, kind="stationary_person", level="watch",
                text=(
                    f"Stationary-person signal {obs.stationary_person_signal:.2f} "
                    "- keep watch on the area."
                ),
            ))

        if flow_anomaly_safety < bands.flow_anomaly_urgent:
            level = "urgent"
            alerts.append(CoastOpsAlert(
                zone_id=obs.zone_id, kind="flow_anomaly", level="urgent",
                text=(
                    f"Sudden flow change {obs.flow_anomaly_signal:.2f} - "
                    "scan for a cause (incident, panic, rip current)."
                ),
            ))
        elif flow_anomaly_safety < bands.flow_anomaly_watch:
            level = _max_level(level, "watch")
            alerts.append(CoastOpsAlert(
                zone_id=obs.zone_id, kind="flow_anomaly", level="watch",
                text=(
                    f"Flow pattern shifting {obs.flow_anomaly_signal:.2f} "
                    "- worth a glance."
                ),
            ))

        if slip_risk_safety < bands.slip_risk_urgent:
            level = "urgent"
            alerts.append(CoastOpsAlert(
                zone_id=obs.zone_id, kind="slip_risk", level="urgent",
                text=(
                    f"High slip risk {obs.slip_risk_signal:.2f} - "
                    "request a wet-surface mitigation pass."
                ),
            ))
        elif slip_risk_safety < bands.slip_risk_watch:
            level = _max_level(level, "watch")
            alerts.append(CoastOpsAlert(
                zone_id=obs.zone_id, kind="slip_risk", level="watch",
                text=(
                    f"Surface slippery {obs.slip_risk_signal:.2f} - "
                    "post a sign / clear the puddle."
                ),
            ))

        score = CoastScore(
            zone_id=obs.zone_id,
            zone_kind=obs.zone_kind,
            alert_level=level,
            density_safety=round(density_safety, 3),
            drowning_safety=round(drowning_safety, 3),
            sun_safety=round(sun_safety, 3),
            lost_child_safety=round(lost_child_safety, 3),
            fall_event_safety=round(fall_event_safety, 3),
            stationary_person_safety=round(stationary_person_safety, 3),
            flow_anomaly_safety=round(flow_anomaly_safety, 3),
            slip_risk_safety=round(slip_risk_safety, 3),
            overall=round(overall, 3),
        )
        return score, alerts

    @staticmethod
    def _drowning_safety(obs: CoastZoneObservation) -> float:
        if obs.zone_kind != "water":
            return 1.0
        risk = (1.0 - obs.in_water_motion) * obs.density_pressure
        return max(0.0, 1.0 - risk)

    @staticmethod
    def _sun_safety(obs: CoastZoneObservation) -> float:
        weights: dict[ZoneKind, float] = {
            "water": 1.0,
            "beach": 1.0,
            "pier": 0.7,
            "promenade": 0.5,
        }
        scale = weights.get(obs.zone_kind, 0.7)
        risk = obs.sun_intensity * scale
        return max(0.0, 1.0 - risk)


_LEVEL_RANK: dict[AlertLevel, int] = {"ok": 0, "watch": 1, "urgent": 2}


def _max_level(a: AlertLevel, b: AlertLevel) -> AlertLevel:
    return a if _LEVEL_RANK[a] >= _LEVEL_RANK[b] else b


__all__ = ["CoastSafetyEngine"]
