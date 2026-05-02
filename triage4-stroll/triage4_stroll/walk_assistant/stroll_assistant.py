"""StrollAssistant — review() one ``StrollSegment`` at a time.

Channel rules (deliberately simple thresholds, not ML):

- **fatigue_index**: combination of pace-band excursion, duration,
  terrain multiplier, and HR (when available). 0.0 = fresh, 1.0 =
  exhausted.
- **hydration_due**: True when minutes_since_rest > 20 AND
  air_temp_c is None or > 22 °C.
- **shade_advisory**: True when sun_exposure_proxy > 0.6 AND
  duration_min > 15.
- **pace_advisory**: "slow_down" if pace > pace_high or HR > 165
  bpm; "speed_up" if pace < pace_low AND duration_min > 5;
  otherwise "continue".
- **rest_due**: True when minutes_since_rest > 30 OR
  fatigue_index > 0.75.
- **overall_safety**: 1 − fatigue_index, dampened by sun /
  hydration flags.

Wellness posture: cues never name a medical condition. They
report what was OBSERVED and SUGGEST an adjustment.
"""

from __future__ import annotations

from ..core.enums import PaceAdvisory
from ..core.models import CoachCue, StrollAdvisory, StrollSegment
from .walk_profiles import TerrainProfile, profile_for


_HR_HARD_BAND = 165.0  # bpm — generic "very high" reference, not age-tuned


class StrollAssistant:
    """Day-walk advisor — turns a segment into channel scores + cues."""

    def review(self, segment: StrollSegment) -> StrollAdvisory:
        prof = profile_for(segment.terrain)

        fatigue = self._fatigue(segment, prof.fatigue_multiplier)
        pace_adv = self._pace_advisory(segment, prof)
        hydration_due = (
            segment.minutes_since_rest > 20.0
            and (segment.air_temp_c is None or segment.air_temp_c > 22.0)
        )
        shade_advisory = (
            segment.sun_exposure_proxy > 0.6 and segment.duration_min > 15.0
        )
        rest_due = segment.minutes_since_rest > 30.0 or fatigue > 0.75

        overall = max(0.0, 1.0 - fatigue)
        if shade_advisory:
            overall *= 0.85
        if hydration_due:
            overall *= 0.85
        overall = max(0.0, min(1.0, overall))

        cues = self._cues(
            segment, fatigue, pace_adv, hydration_due, shade_advisory, rest_due,
        )

        return StrollAdvisory(
            segment=segment,
            fatigue_index=round(fatigue, 3),
            hydration_due=hydration_due,
            shade_advisory=shade_advisory,
            pace_advisory=pace_adv,
            rest_due=rest_due,
            overall_safety=round(overall, 3),
            cues=cues,
        )

    # -- channel rules -----------------------------------------------------

    @staticmethod
    def _fatigue(segment: StrollSegment, multiplier: float) -> float:
        """Combine duration, activity intensity, terrain, HR (if any)."""
        dur_part = min(1.0, segment.duration_min / 90.0)
        pace_part = segment.activity_intensity
        hr_part = 0.0
        if segment.hr_bpm is not None:
            hr_part = max(0.0, min(1.0, (segment.hr_bpm - 80.0) / 80.0))
        raw = 0.4 * dur_part + 0.4 * pace_part + 0.2 * hr_part
        return max(0.0, min(1.0, raw * multiplier))

    @staticmethod
    def _pace_advisory(
        segment: StrollSegment, prof: TerrainProfile,
    ) -> PaceAdvisory:
        if (
            segment.pace_kmh > prof.pace_high
            or (segment.hr_bpm is not None and segment.hr_bpm > _HR_HARD_BAND)
        ):
            return "slow_down"
        if segment.pace_kmh < prof.pace_low and segment.duration_min > 5.0:
            return "speed_up"
        return "continue"

    # -- cue generation ----------------------------------------------------

    @staticmethod
    def _cues(
        segment: StrollSegment,
        fatigue: float,
        pace_adv: PaceAdvisory,
        hydration_due: bool,
        shade_advisory: bool,
        rest_due: bool,
    ) -> list[CoachCue]:
        cues: list[CoachCue] = []

        if fatigue > 0.85:
            cues.append(CoachCue(
                kind="fatigue",
                severity="severe",
                text=f"Fatigue index {fatigue:.2f} — find a bench and rest.",
                observed_value=fatigue,
            ))
        elif fatigue > 0.6:
            cues.append(CoachCue(
                kind="fatigue",
                severity="minor",
                text=f"Fatigue index {fatigue:.2f} — slow down for a few minutes.",
                observed_value=fatigue,
            ))

        if pace_adv == "slow_down":
            cues.append(CoachCue(
                kind="pace",
                severity="minor",
                text=(
                    f"Pace {segment.pace_kmh:.1f} km/h is high for "
                    f"{segment.terrain} terrain — ease back."
                ),
                observed_value=segment.pace_kmh,
            ))
        elif pace_adv == "speed_up":
            cues.append(CoachCue(
                kind="pace",
                severity="minor",
                text=(
                    f"Pace {segment.pace_kmh:.1f} km/h is below the "
                    f"{segment.terrain} band — pick it up if you feel good."
                ),
                observed_value=segment.pace_kmh,
            ))

        if hydration_due:
            text = "Time for water — "
            if segment.air_temp_c is not None and segment.air_temp_c > 28:
                text += (
                    f"it is {segment.air_temp_c:.0f} C and you have been "
                    "walking a while."
                )
            else:
                text += f"{segment.minutes_since_rest:.0f} min since your last break."
            cues.append(CoachCue(
                kind="hydration",
                severity="minor",
                text=text,
                observed_value=segment.minutes_since_rest,
            ))

        if shade_advisory:
            cues.append(CoachCue(
                kind="shade",
                severity="minor",
                text=(
                    f"High sun exposure for {segment.duration_min:.0f} min — "
                    "consider walking on the shaded side."
                ),
                observed_value=segment.sun_exposure_proxy,
            ))

        if rest_due and not any(
            c.kind == "fatigue" and c.severity == "severe" for c in cues
        ):
            cues.append(CoachCue(
                kind="rest",
                severity="minor" if segment.minutes_since_rest < 45 else "severe",
                text=(
                    f"{segment.minutes_since_rest:.0f} min without a rest — "
                    "take five."
                ),
                observed_value=segment.minutes_since_rest,
            ))

        return cues


__all__ = ["StrollAssistant"]
