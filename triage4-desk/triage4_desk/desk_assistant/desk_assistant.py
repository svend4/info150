"""DeskAssistant — review() one ``DeskSession`` at a time.

Channel rules (deliberately simple thresholds, not ML):

- **fatigue_index**: combo of session_min, posture_quality,
  drowsiness, typing_intensity, and HR. Weighted by work_mode's
  fatigue_multiplier.
- **hydration_due**: True when minutes_since_break > 45 (or > 30 if
  air_temp_c > 24 °C). Drinking water is the typical microbreak
  trigger.
- **eye_break_due**: 20-20-20 rule — every N minutes of continuous
  screen time, look at something 20 ft away for 20 s. N from
  WorkProfile.eye_break_minutes.
- **microbreak_due**: True when minutes_since_break exceeds the
  Pomodoro-style threshold for the work_mode.
- **stretch_due**: True when minutes_since_stretch exceeds the
  long-block threshold.
- **posture_advisory**: from posture_quality:
    >= 0.8 → "ok"; >= 0.5 → "leaning"; else → "slumped"
- **drowsiness_alert**: True when drowsiness_signal >= 0.7 OR
  HR < 55 bpm during a long session.
- **distraction_alert**: True when distraction_signal >= 0.7 (eye
  gaze drifting away from screen for prolonged stretches).
- **overall_safety**: 1 − fatigue_index, dampened by every active
  flag (each multiplies by 0.9).

Wellness posture: cues never name a medical condition.
"""

from __future__ import annotations

from ..core.enums import PostureAdvisory
from ..core.models import CoachCue, DeskAdvisory, DeskSession
from .work_profiles import WorkProfile, profile_for


_HR_LOW_DROWSY = 55.0  # bpm — generic "very low" reference (long-session drowsiness)


class DeskAssistant:
    """Desk-worker advisor — turns a session into channel scores + cues."""

    def review(self, session: DeskSession) -> DeskAdvisory:
        prof = profile_for(session.work_mode)

        fatigue = self._fatigue(session, prof.fatigue_multiplier)
        hydration_due = (
            session.minutes_since_break > 45.0
            or (
                session.air_temp_c is not None and session.air_temp_c > 24.0
                and session.minutes_since_break > 30.0
            )
        )
        eye_break_due = session.session_min > prof.eye_break_minutes
        microbreak_due = (
            session.minutes_since_break > prof.microbreak_minutes
            or fatigue > 0.75
        )
        stretch_due = session.minutes_since_stretch > prof.stretch_minutes
        posture_adv = self._posture_advisory(session)
        drowsiness_alert = (
            session.drowsiness_signal >= 0.7
            or (
                session.hr_bpm is not None
                and session.hr_bpm < _HR_LOW_DROWSY
                and session.session_min > 60.0
            )
        )
        distraction_alert = session.distraction_signal >= 0.7

        overall = max(0.0, 1.0 - fatigue)
        for flag in (
            hydration_due, eye_break_due, microbreak_due, stretch_due,
            drowsiness_alert, distraction_alert,
            posture_adv == "slumped",
        ):
            if flag:
                overall *= 0.90
        overall = max(0.0, min(1.0, overall))

        cues = self._cues(
            session, prof, fatigue, hydration_due, eye_break_due,
            microbreak_due, stretch_due, posture_adv,
            drowsiness_alert, distraction_alert,
        )

        return DeskAdvisory(
            session=session,
            fatigue_index=round(fatigue, 3),
            hydration_due=hydration_due,
            eye_break_due=eye_break_due,
            microbreak_due=microbreak_due,
            stretch_due=stretch_due,
            posture_advisory=posture_adv,
            drowsiness_alert=drowsiness_alert,
            distraction_alert=distraction_alert,
            overall_safety=round(overall, 3),
            cues=cues,
        )

    # -- channel rules -----------------------------------------------------

    @staticmethod
    def _fatigue(session: DeskSession, multiplier: float) -> float:
        # Session duration component, saturating around 4 h.
        dur_part = min(1.0, session.session_min / 240.0)
        # Posture cost — slumped raises fatigue.
        post_part = max(0.0, 1.0 - session.posture_quality)
        # Drowsiness directly contributes.
        drowsy_part = session.drowsiness_signal
        # Typing intensity adds slow accumulation (RSI proxy).
        typing_part = 0.5 * session.typing_intensity
        # HR component — high or very low both raise fatigue.
        hr_part = 0.0
        if session.hr_bpm is not None:
            if session.hr_bpm > 110:
                hr_part = min(1.0, (session.hr_bpm - 110.0) / 60.0)
            elif session.hr_bpm < 55:
                hr_part = min(1.0, (55.0 - session.hr_bpm) / 30.0)
        raw = (
            0.35 * dur_part
            + 0.25 * post_part
            + 0.15 * drowsy_part
            + 0.10 * typing_part
            + 0.15 * hr_part
        )
        return max(0.0, min(1.0, raw * multiplier))

    @staticmethod
    def _posture_advisory(session: DeskSession) -> PostureAdvisory:
        q = session.posture_quality
        if q >= 0.8:
            return "ok"
        if q >= 0.5:
            return "leaning"
        return "slumped"

    # -- cue generation ----------------------------------------------------

    @staticmethod
    def _cues(
        session: DeskSession,
        prof: WorkProfile,
        fatigue: float,
        hydration_due: bool,
        eye_break_due: bool,
        microbreak_due: bool,
        stretch_due: bool,
        posture_adv: PostureAdvisory,
        drowsiness_alert: bool,
        distraction_alert: bool,
    ) -> list[CoachCue]:
        cues: list[CoachCue] = []

        if fatigue > 0.85:
            cues.append(CoachCue(
                kind="fatigue", severity="severe",
                text=(
                    f"Fatigue index {fatigue:.2f} — stand up, walk for "
                    "five minutes, and consider ending this block."
                ),
                observed_value=fatigue,
            ))
        elif fatigue > 0.6:
            cues.append(CoachCue(
                kind="fatigue", severity="minor",
                text=f"Fatigue index {fatigue:.2f} — short break recommended.",
                observed_value=fatigue,
            ))

        if posture_adv == "slumped":
            cues.append(CoachCue(
                kind="posture", severity="minor",
                text=(
                    "Sitting slumped — straighten up, shoulders back, "
                    "screen at eye level."
                ),
                observed_value=session.posture_quality,
            ))
        elif posture_adv == "leaning" and session.session_min > 30.0:
            cues.append(CoachCue(
                kind="posture", severity="minor",
                text="Leaning to one side — recentre on the chair.",
                observed_value=session.posture_quality,
            ))

        if eye_break_due:
            cues.append(CoachCue(
                kind="eye_strain", severity="minor",
                text=(
                    f"20-20-20 rule: {session.session_min:.0f} min on screen "
                    "— look at something 20 ft away for 20 seconds."
                ),
                observed_value=session.session_min,
            ))

        if microbreak_due:
            cues.append(CoachCue(
                kind="microbreak", severity="minor",
                text=(
                    f"{session.minutes_since_break:.0f} min since your last "
                    f"break — Pomodoro suggests one every "
                    f"{prof.microbreak_minutes:.0f} min."
                ),
                observed_value=session.minutes_since_break,
            ))

        if stretch_due:
            cues.append(CoachCue(
                kind="stretch",
                severity="severe" if session.minutes_since_stretch > 180 else "minor",
                text=(
                    f"{session.minutes_since_stretch:.0f} min since you stretched "
                    "— stand, roll your shoulders, neck, wrists."
                ),
                observed_value=session.minutes_since_stretch,
            ))

        if hydration_due:
            text = "Time for water — "
            if session.air_temp_c is not None and session.air_temp_c > 26:
                text += f"workspace is at {session.air_temp_c:.0f} C, drink up."
            else:
                text += f"{session.minutes_since_break:.0f} min since you last broke."
            cues.append(CoachCue(
                kind="hydration", severity="minor",
                text=text,
                observed_value=session.minutes_since_break,
            ))

        if drowsiness_alert:
            cues.append(CoachCue(
                kind="drowsiness",
                severity="severe" if session.drowsiness_signal > 0.85 else "minor",
                text=(
                    "Drowsiness signal is high — consider a short walk, "
                    "fresh air, or wrapping up the session."
                ),
                observed_value=session.drowsiness_signal,
            ))

        if distraction_alert:
            cues.append(CoachCue(
                kind="distraction", severity="minor",
                text=(
                    "Looking away frequently — if you need a break, take "
                    "one; otherwise consider noise-cancelling or "
                    "do-not-disturb."
                ),
                observed_value=session.distraction_signal,
            ))

        return cues


__all__ = ["DeskAssistant"]
