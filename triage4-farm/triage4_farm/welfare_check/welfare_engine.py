"""WelfareCheckEngine — the main observation engine.

Sibling of triage4's ``RapidTriageEngine`` and triage4-fit's
``RapidFormEngine``. Takes a list of ``AnimalObservation``
records and a farm id, scores every animal across three welfare
channels (gait / respiratory / thermal), aggregates into an
overall score with a discrete flag, and emits ``FarmerAlert``
records the stockperson surfaces at morning check.

Observation-only. Never diagnoses. Never recommends a
treatment, dose, antibiotic, or withdrawal period. The alert
text only describes what was seen and — when a concern is
surfaced — appends ``vet review recommended``.
"""

from __future__ import annotations

from ..core.enums import AlertKind, WelfareFlag
from ..core.models import (
    AnimalObservation,
    FarmerAlert,
    HerdReport,
    WelfareScore,
)
from ..signatures.lameness_gait import compute_lameness_score
from ..signatures.respiratory_rate import compute_respiratory_score
from ..signatures.thermal_inflammation import compute_thermal_score
from .species_profiles import SpeciesProfile, profile_for


# Channel weights for the overall welfare score. Gait weighted
# highest because lameness is the single biggest welfare cost in
# dairy and grower-pig systems. Respiratory and thermal carry
# real signal but more intermittently.
_CHANNEL_WEIGHTS: dict[str, float] = {
    "gait": 0.5,
    "respiratory": 0.3,
    "thermal": 0.2,
}


class WelfareCheckEngine:
    """Score a herd-pass's observations + emit farmer-facing alerts."""

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        w = dict(weights or _CHANNEL_WEIGHTS)
        total = sum(w.values())
        if total <= 0:
            raise ValueError("weight total must be positive")
        self._weights = {k: v / total for k, v in w.items()}

    # -- public API -----------------------------------------------------

    def review(
        self,
        farm_id: str,
        observations: list[AnimalObservation],
    ) -> HerdReport:
        if not observations:
            return HerdReport(
                farm_id=farm_id,
                scores=[],
                alerts=[
                    FarmerAlert(
                        animal_id="-",
                        kind="behaviour",
                        flag="concern",
                        text=(
                            "No animals observed on this pass. "
                            "Check the camera placement before the next round."
                        ),
                    )
                ],
                herd_overall=0.0,
            )

        scores: list[WelfareScore] = []
        alerts: list[FarmerAlert] = []
        for obs in observations:
            profile = profile_for(obs.species)
            score = self._score_animal(obs, profile)
            scores.append(score)
            alerts.extend(self._alerts_for_animal(obs, score, profile))

        herd_overall = sum(s.overall for s in scores) / len(scores)

        return HerdReport(
            farm_id=farm_id,
            scores=scores,
            alerts=alerts,
            herd_overall=round(herd_overall, 3),
        )

    # -- internals ------------------------------------------------------

    def _score_animal(
        self,
        obs: AnimalObservation,
        profile: SpeciesProfile,
    ) -> WelfareScore:
        # Gait: if the species has no bilateral pairs (chicken),
        # we can't compute a meaningful L/R lameness number —
        # neutral 1.0, and the channel effectively carries no
        # information for that species.
        if profile.lameness_pairs:
            gait = compute_lameness_score(obs, pairs=profile.lameness_pairs)
        else:
            gait = 1.0

        resp = compute_respiratory_score(obs.respiratory_bpm, obs.species)
        therm = compute_thermal_score(obs.thermal_hotspot)

        # Missing channels drop out of the weighted average
        # entirely — never impute wellness.
        weighted: list[tuple[float, float]] = [(self._weights["gait"], gait)]
        if resp is not None:
            weighted.append((self._weights["respiratory"], resp))
        if therm is not None:
            weighted.append((self._weights["thermal"], therm))
        total_w = sum(w for w, _ in weighted)
        overall = sum(w * v for w, v in weighted) / total_w if total_w else gait

        flag = self._flag_for(overall, profile)

        return WelfareScore(
            animal_id=obs.animal_id,
            gait=round(gait, 3),
            respiratory=round(resp, 3) if resp is not None else 1.0,
            thermal=round(therm, 3) if therm is not None else 1.0,
            overall=round(overall, 3),
            flag=flag,
        )

    @staticmethod
    def _flag_for(overall: float, profile: SpeciesProfile) -> WelfareFlag:
        if overall < profile.urgent_threshold:
            return "urgent"
        if overall < profile.concern_threshold:
            return "concern"
        return "well"

    def _alerts_for_animal(
        self,
        obs: AnimalObservation,
        score: WelfareScore,
        profile: SpeciesProfile,
    ) -> list[FarmerAlert]:
        alerts: list[FarmerAlert] = []

        # Gait channel.
        if profile.lameness_pairs:
            if score.gait < profile.lameness_urgent:
                alerts.append(self._alert(
                    obs.animal_id, "lameness", "urgent",
                    f"Animal {obs.animal_id} shows pronounced gait "
                    f"asymmetry (score {score.gait:.2f}). "
                    "Vet review recommended.",
                    observed_value=score.gait,
                ))
            elif score.gait < profile.lameness_concern:
                alerts.append(self._alert(
                    obs.animal_id, "lameness", "concern",
                    f"Animal {obs.animal_id} shows mild gait "
                    f"asymmetry (score {score.gait:.2f}). "
                    "Monitor; vet review recommended if persistent.",
                    observed_value=score.gait,
                ))

        # Respiratory channel (only if we actually measured it).
        if obs.respiratory_bpm is not None:
            if score.respiratory < profile.respiratory_urgent:
                alerts.append(self._alert(
                    obs.animal_id, "respiratory", "urgent",
                    f"Animal {obs.animal_id} respiratory rate "
                    f"{obs.respiratory_bpm:.0f} bpm — well outside "
                    "routine range. Vet review recommended.",
                    observed_value=obs.respiratory_bpm,
                ))
            elif score.respiratory < profile.respiratory_concern:
                alerts.append(self._alert(
                    obs.animal_id, "respiratory", "concern",
                    f"Animal {obs.animal_id} respiratory rate "
                    f"{obs.respiratory_bpm:.0f} bpm — above routine "
                    "range. Monitor; vet review recommended if persistent.",
                    observed_value=obs.respiratory_bpm,
                ))

        # Thermal channel (only if we actually measured it).
        if obs.thermal_hotspot is not None:
            if score.thermal < profile.thermal_urgent:
                alerts.append(self._alert(
                    obs.animal_id, "thermal", "urgent",
                    f"Animal {obs.animal_id} shows a pronounced "
                    "focal warm patch on IR. Vet review recommended.",
                    observed_value=obs.thermal_hotspot,
                ))
            elif score.thermal < profile.thermal_concern:
                alerts.append(self._alert(
                    obs.animal_id, "thermal", "concern",
                    f"Animal {obs.animal_id} shows a mildly elevated "
                    "focal warm patch on IR. Monitor; vet review "
                    "recommended if persistent.",
                    observed_value=obs.thermal_hotspot,
                ))

        return alerts

    @staticmethod
    def _alert(
        animal_id: str,
        kind: AlertKind,
        flag: WelfareFlag,
        text: str,
        observed_value: float | None = None,
    ) -> FarmerAlert:
        return FarmerAlert(
            animal_id=animal_id,
            kind=kind,
            flag=flag,
            text=text,
            observed_value=observed_value,
        )
