"""RapidFormEngine — the main wellness engine.

Sibling of triage4's ``RapidTriageEngine``. Takes an
``ExerciseSession``, scores every rep (symmetry + depth + tempo),
aggregates into an overall session form score, and emits
``CoachCue`` records the trainer can surface to the trainee.

Never diagnoses. Never recommends medical action. Emits
coaching language only.
"""

from __future__ import annotations

from typing import Iterable

from ..core.enums import CueKind, CueSeverity
from ..core.models import (
    CoachBriefing,
    CoachCue,
    ExerciseSession,
    FormScore,
    JointPoseSample,
    RepObservation,
)
from ..signatures.breathing_recovery import estimate_recovery_quality
from ..signatures.pose_symmetry import compute_rep_symmetry
from .exercise_profiles import ExerciseProfile, profile_for


# Overall-form weighting — symmetry weighted highest because it's
# the most reliable signal; tempo gets less because trainees
# naturally slow down as they fatigue.
_OVERALL_WEIGHTS: dict[str, float] = {
    "symmetry": 0.5,
    "depth": 0.3,
    "tempo": 0.2,
}


class RapidFormEngine:
    """Score a session's form + produce coaching cues."""

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        w = dict(weights or _OVERALL_WEIGHTS)
        total = sum(w.values())
        if total <= 0:
            raise ValueError("weight total must be positive")
        self._weights = {k: v / total for k, v in w.items()}

    # -- public API -----------------------------------------------------

    def review(self, session: ExerciseSession) -> CoachBriefing:
        if session.rep_count == 0:
            return CoachBriefing(
                session=session,
                form_scores=[],
                cues=[
                    CoachCue(
                        rep_index=None,
                        kind="tempo",
                        severity="minor",
                        text="No reps observed. Check the camera angle.",
                    )
                ],
                session_overall=0.0,
                recovery_quality=None,
            )

        profile = profile_for(session.exercise)
        scores: list[FormScore] = []
        cues: list[CoachCue] = []

        for rep in session.reps:
            score = self._score_rep(rep, profile)
            scores.append(score)
            cues.extend(self._cues_for_rep(rep, score, profile))

        session_overall = (
            sum(s.overall for s in scores) / len(scores)
            if scores else 0.0
        )

        # Recovery cue based on the LAST rep's post-rep vitals.
        last_rep = session.reps[-1]
        recovery = estimate_recovery_quality(last_rep.hr_bpm, last_rep.breathing_bpm)
        if recovery is not None and recovery < 0.5:
            cues.append(
                CoachCue(
                    rep_index=None,
                    kind="breathing",
                    severity="minor",
                    text=(
                        f"Post-set recovery quality {recovery:.2f} — "
                        "consider resting longer before the next set."
                    ),
                    observed_value=recovery,
                )
            )

        return CoachBriefing(
            session=session,
            form_scores=scores,
            cues=cues,
            session_overall=round(session_overall, 3),
            recovery_quality=None if recovery is None else round(recovery, 3),
        )

    # -- internals ------------------------------------------------------

    def _score_rep(self, rep: RepObservation, profile: ExerciseProfile) -> FormScore:
        symmetry = compute_rep_symmetry(rep)
        depth = self._score_depth(rep, profile)
        tempo = self._score_tempo(rep, profile)
        overall = (
            self._weights["symmetry"] * symmetry
            + self._weights["depth"] * depth
            + self._weights["tempo"] * tempo
        )
        return FormScore(
            rep_index=rep.rep_index,
            symmetry=round(symmetry, 3),
            depth=round(depth, 3),
            tempo=round(tempo, 3),
            overall=round(overall, 3),
        )

    def _score_depth(self, rep: RepObservation, profile: ExerciseProfile) -> float:
        if not profile.depth_joints or not rep.samples:
            return 1.0
        # y-travel of each depth joint across the rep.
        travels: list[float] = []
        body_scale = self._body_scale(rep.samples) or 1.0
        for joint in profile.depth_joints:
            ys = [s.y for frame in rep.samples for s in frame if s.joint == joint]
            if not ys:
                continue
            travels.append((max(ys) - min(ys)) / body_scale)
        if not travels:
            return 1.0
        travel = max(travels)   # best of both sides
        if travel >= profile.full_depth_travel:
            return 1.0
        if travel <= profile.min_depth_travel:
            return 0.0
        # Linear ramp between the two thresholds.
        span = profile.full_depth_travel - profile.min_depth_travel
        return max(0.0, min(1.0, (travel - profile.min_depth_travel) / span))

    def _score_tempo(self, rep: RepObservation, profile: ExerciseProfile) -> float:
        if rep.duration_s < profile.tempo_low:
            # too fast — dangerous-adjacent but framed neutrally
            ratio = rep.duration_s / profile.tempo_low
            return max(0.0, min(1.0, ratio))
        if rep.duration_s > profile.tempo_high:
            # too slow / struggled rep
            over = rep.duration_s - profile.tempo_high
            # Decay over another factor-of-2 beyond high.
            return max(0.0, 1.0 - over / profile.tempo_high)
        return 1.0

    @staticmethod
    def _body_scale(frames: Iterable[list[JointPoseSample]]) -> float:
        best = 0.0
        for frame in frames:
            idx = {s.joint: s for s in frame}
            ys: list[float] = []
            for side in ("shoulder_l", "shoulder_r", "hip_l", "hip_r"):
                if side in idx:
                    ys.append(idx[side].y)
            if len(ys) >= 2:
                best = max(best, max(ys) - min(ys))
        return best

    def _cues_for_rep(
        self,
        rep: RepObservation,
        score: FormScore,
        profile: ExerciseProfile,
    ) -> list[CoachCue]:
        cues: list[CoachCue] = []

        # Symmetry cues.
        if score.symmetry < profile.severe_symmetry:
            cues.append(self._cue(
                rep.rep_index, "asymmetry", "severe",
                f"Strong left-right asymmetry on rep {rep.rep_index + 1} "
                f"(symmetry score {score.symmetry:.2f}). Consider a reset "
                "set at lighter load to groove the movement.",
                observed_value=score.symmetry,
            ))
        elif score.symmetry < profile.minor_symmetry:
            cues.append(self._cue(
                rep.rep_index, "asymmetry", "minor",
                f"Slight asymmetry on rep {rep.rep_index + 1} "
                f"(symmetry {score.symmetry:.2f}) — focus on even effort.",
                observed_value=score.symmetry,
            ))

        # Depth cues (only if the profile scores depth).
        if profile.depth_joints:
            if score.depth < 0.5:
                cues.append(self._cue(
                    rep.rep_index, "depth", "minor",
                    f"Rep {rep.rep_index + 1} looks shallow — aim for fuller "
                    "range of motion on the next rep.",
                    observed_value=score.depth,
                ))

        # Tempo cues.
        if score.tempo < 0.5:
            if rep.duration_s < profile.tempo_low:
                cues.append(self._cue(
                    rep.rep_index, "tempo", "minor",
                    f"Rep {rep.rep_index + 1} was fast "
                    f"({rep.duration_s:.1f} s). Slow down to keep the "
                    "movement controlled.",
                    observed_value=rep.duration_s,
                ))
            else:
                cues.append(self._cue(
                    rep.rep_index, "tempo", "severe",
                    f"Rep {rep.rep_index + 1} stalled "
                    f"({rep.duration_s:.1f} s). End the set here and rest.",
                    observed_value=rep.duration_s,
                ))

        return cues

    @staticmethod
    def _cue(
        rep_index: int,
        kind: CueKind,
        severity: CueSeverity,
        text: str,
        observed_value: float | None = None,
    ) -> CoachCue:
        return CoachCue(
            rep_index=rep_index,
            kind=kind,
            severity=severity,
            text=text,
            observed_value=observed_value,
        )
