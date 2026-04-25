"""AquacultureHealthEngine — multi-modal pen-welfare engine.

Produces one ``PenWelfareScore`` + zero-or-more
``FarmManagerAlert`` records from a multi-modal
``PenObservation``.

Multi-modal fusion architecture:
- The engine reads the water-chemistry signature's
  ``vision_confidence`` output and uses it to scale the
  weighted contribution of the visible-light channels
  (gill rate, school cohesion, sea lice, mortality
  floor) — turbid water → vision channels blend toward
  neutral.
- Water chemistry also contributes its own safety score
  as an independent channel.
- When a vision channel deviates AND water chemistry is
  ALSO degraded, the engine pairs them in a corroborative
  alert ("low DO co-occurring with reduced gill rate")
  rather than emitting two unrelated alerts.

Failure-cost-asymmetric posture: the alert text NEVER
uses reassurance vocabulary, NEVER recommends antibiotic
dosing (vet-handoff framing only), and NEVER claims
outbreak.

See docs/PHILOSOPHY.md.
"""

from __future__ import annotations

from biocore.fusion import (
    apply_channel_floor,
    normalise_weights,
    weighted_overall,
)

from ..core.enums import AlertKind, WelfareLevel
from ..core.models import (
    FarmManagerAlert,
    PenObservation,
    PenReport,
    PenWelfareScore,
)
from ..signatures.gill_rate import compute_gill_rate_safety
from ..signatures.mortality_floor import compute_mortality_safety
from ..signatures.school_cohesion import compute_school_cohesion_safety
from ..signatures.sea_lice_burden import compute_sea_lice_safety
from ..signatures.water_chemistry import compute_water_chemistry
from .species_aquatic_bands import profile_for


# Channel weights. Mortality + water-chemistry weighted
# highest because they're the most direct welfare signals.
_CHANNEL_WEIGHTS: dict[str, float] = {
    "gill_rate":        0.20,
    "school_cohesion":  0.15,
    "sea_lice":         0.15,
    "mortality_floor":  0.25,
    "water_chemistry":  0.25,
}


class AquacultureHealthEngine:
    """Score one multi-modal pen observation + emit alerts."""

    def __init__(
        self,
        weights: dict[str, float] | None = None,
    ) -> None:
        # biocore.fusion.normalise_weights — extracted in
        # tier-2 because the validate-and-rescale pattern
        # is identical across twelve engines.
        self._weights = normalise_weights(weights or _CHANNEL_WEIGHTS)

    # -- public API -----------------------------------------------------

    def review(
        self,
        observation: PenObservation,
        farm_id: str = "farm",
    ) -> PenReport:
        prof = profile_for(observation.species)

        gill = compute_gill_rate_safety(
            observation.gill_rate_samples, observation.species,
        )
        school = compute_school_cohesion_safety(observation.school_samples)
        lice = compute_sea_lice_safety(observation.sea_lice_samples)
        mortality = compute_mortality_safety(observation.mortality_samples)
        water = compute_water_chemistry(
            observation.water_chemistry_samples, observation.species,
        )

        # Multi-modal fusion: scale visible-light channels by
        # vision_confidence from the water-chemistry signature.
        # Turbid water → vision channels blend toward neutral.
        v = water.vision_confidence
        adjusted_channel_scores: dict[str, float] = {
            "gill_rate":        gill * v + 1.0 * (1.0 - v),
            "school_cohesion":  school * v + 1.0 * (1.0 - v),
            "sea_lice":         lice * v + 1.0 * (1.0 - v),
            "mortality_floor":  mortality * v + 1.0 * (1.0 - v),
            "water_chemistry":  water.safety,
        }

        # biocore.fusion.weighted_overall — extracted in
        # tier-2 because the weighted-sum-then-clamp shape
        # is identical across twelve engines.
        overall = weighted_overall(self._weights, adjusted_channel_scores)

        # biocore.fusion.apply_channel_floor — channel-urgent
        # mortal-sign override. Pass RAW (un-blended) channel
        # scores so silt-storm doesn't accidentally hide a
        # genuine vision-channel-urgent signal.
        raw_channel_scores: dict[str, float] = {
            "gill_rate":        gill,
            "school_cohesion":  school,
            "sea_lice":         lice,
            "mortality_floor":  mortality,
            "water_chemistry":  water.safety,
        }
        overall = apply_channel_floor(
            overall,
            raw_channel_scores,
            urgent_threshold=prof.channel_urgent,
            overall_floor=prof.overall_urgent,
        )

        if overall < prof.overall_urgent:
            level: WelfareLevel = "urgent"
        elif overall < prof.overall_watch:
            level = "watch"
        else:
            level = "steady"

        score = PenWelfareScore(
            pen_id=observation.pen_id,
            gill_rate_safety=round(gill, 3),
            school_cohesion_safety=round(school, 3),
            sea_lice_safety=round(lice, 3),
            mortality_safety=round(mortality, 3),
            water_chemistry_safety=round(water.safety, 3),
            overall=round(overall, 3),
            welfare_level=level,
        )

        alerts = self._alerts_for(
            observation, score,
            gill=gill, school=school, lice=lice,
            mortality=mortality, water_safety=water.safety,
            vision_confidence=water.vision_confidence,
        )

        return PenReport(
            farm_id=farm_id,
            scores=[score],
            alerts=alerts,
        )

    # -- internals ------------------------------------------------------

    def _alerts_for(
        self,
        obs: PenObservation,
        score: PenWelfareScore,
        gill: float,
        school: float,
        lice: float,
        mortality: float,
        water_safety: float,
        vision_confidence: float,
    ) -> list[FarmManagerAlert]:
        alerts: list[FarmManagerAlert] = []
        prof = profile_for(obs.species)
        loc = obs.location_handle
        pid = obs.pen_id

        # Cross-modal corroboration: when both mortality AND
        # water chemistry fire urgent, surface a SINGLE
        # combined alert with the candidate-disease-pattern
        # framing — surveillance-overreach safety, copied
        # in spirit from triage4-bird's combined-alert
        # pattern.
        mortality_urgent = mortality < prof.channel_urgent
        water_urgent = water_safety < prof.channel_urgent
        gill_urgent = gill < prof.channel_urgent

        if mortality_urgent and (water_urgent or gill_urgent):
            corroboration = []
            if water_urgent:
                corroboration.append("water-chemistry stress")
            if gill_urgent:
                corroboration.append("gill-rate deviation")
            corro_str = " + ".join(corroboration)
            alerts.append(self._alert(
                pid, "mortality_floor", "urgent",
                self._format(
                    "URGENT", obs.species, pid, loc,
                    f"candidate disease pattern (mortality cluster + {corro_str})",
                    extra="Vet review recommended.",
                ),
                loc, mortality,
            ))
        else:
            # Per-channel alerts — emitted independently when
            # the cross-modal pattern doesn't trigger.
            if mortality < prof.channel_urgent:
                alerts.append(self._alert(
                    pid, "mortality_floor", "urgent",
                    self._format(
                        "URGENT", obs.species, pid, loc,
                        "candidate mortality cluster",
                        extra="Vet review recommended.",
                    ),
                    loc, mortality,
                ))
            elif mortality < prof.channel_watch:
                alerts.append(self._alert(
                    pid, "mortality_floor", "watch",
                    self._format(
                        "WATCH", obs.species, pid, loc,
                        "elevated mortality-floor count",
                    ),
                    loc, mortality,
                ))

            if gill < prof.channel_urgent:
                alerts.append(self._alert(
                    pid, "gill_rate", "urgent",
                    self._format(
                        "URGENT", obs.species, pid, loc,
                        "gill-rate aggregate outside species reference band",
                        extra="Vet review recommended.",
                    ),
                    loc, gill,
                ))
            elif gill < prof.channel_watch:
                alerts.append(self._alert(
                    pid, "gill_rate", "watch",
                    self._format(
                        "WATCH", obs.species, pid, loc,
                        "gill-rate aggregate trending outside band",
                    ),
                    loc, gill,
                ))

            if water_safety < prof.channel_urgent:
                alerts.append(self._alert(
                    pid, "water_chemistry", "urgent",
                    self._format(
                        "URGENT", obs.species, pid, loc,
                        "water chemistry outside species range",
                        extra="Vet review recommended.",
                    ),
                    loc, water_safety,
                ))
            elif water_safety < prof.channel_watch:
                alerts.append(self._alert(
                    pid, "water_chemistry", "watch",
                    self._format(
                        "WATCH", obs.species, pid, loc,
                        "water chemistry trending outside range",
                    ),
                    loc, water_safety,
                ))

        # School cohesion + sea lice — independent channels.
        if school < prof.channel_urgent:
            alerts.append(self._alert(
                pid, "school_cohesion", "urgent",
                self._format(
                    "URGENT", obs.species, pid, loc,
                    "school cohesion lost — pen-stress signature",
                    extra="Vet review recommended.",
                ),
                loc, school,
            ))
        elif school < prof.channel_watch:
            alerts.append(self._alert(
                pid, "school_cohesion", "watch",
                self._format(
                    "WATCH", obs.species, pid, loc,
                    "school cohesion below baseline",
                ),
                loc, school,
            ))

        if lice < prof.channel_urgent:
            alerts.append(self._alert(
                pid, "sea_lice", "urgent",
                self._format(
                    "URGENT", obs.species, pid, loc,
                    "sea-lice burden indicator high",
                    extra="Vet review recommended.",
                ),
                loc, lice,
            ))
        elif lice < prof.channel_watch:
            alerts.append(self._alert(
                pid, "sea_lice", "watch",
                self._format(
                    "WATCH", obs.species, pid, loc,
                    "sea-lice burden indicator rising",
                ),
                loc, lice,
            ))

        # Calibration alert if vision confidence dropped
        # markedly — the engine wants the farm manager to
        # know the pen-pass was less reliable than usual.
        if vision_confidence < 0.6 and not alerts:
            alerts.append(self._alert(
                pid, "calibration", "watch",
                self._format(
                    "WATCH", obs.species, pid, loc,
                    "vision-channel confidence reduced "
                    "(turbidity); pen pass less informative than usual",
                ),
                loc, vision_confidence,
            ))

        return alerts

    @staticmethod
    def _format(
        tier: str,
        species: str,
        pen_id: str,
        location_handle: str,
        body: str,
        extra: str = "",
    ) -> str:
        msg = f"{tier} ({species}, {pen_id}, {location_handle}): {body}."
        if extra:
            msg = f"{msg} {extra}"
        return msg

    @staticmethod
    def _alert(
        pen_id: str,
        kind: AlertKind,
        level: WelfareLevel,
        text: str,
        location_handle: str,
        observed_value: float,
    ) -> FarmManagerAlert:
        return FarmManagerAlert(
            pen_id=pen_id,
            kind=kind,
            level=level,
            text=text,
            location_handle=location_handle,
            observed_value=observed_value,
        )
