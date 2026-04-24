"""Core dataclasses for triage4-fit.

Design note — intentionally flat, frozen where sensible, no
methods beyond trivial validation. The form-check engine reads
these; the sim populates them; tests compare them. No inheritance
from triage4 types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from .enums import CueKind, CueSeverity, ExerciseKind, VALID_EXERCISES, VALID_SEVERITIES


# ---------------------------------------------------------------------------
# Raw observations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class JointPoseSample:
    """One joint position at one instant, in image-plane coordinates.

    Coordinates are normalised [0, 1] square — so the engine does
    not depend on what resolution the pose estimator returns.
    """

    joint: str
    x: float
    y: float
    confidence: float = 1.0

    def __post_init__(self) -> None:
        for name, val, lo, hi in (
            ("x", self.x, 0.0, 1.0),
            ("y", self.y, 0.0, 1.0),
            ("confidence", self.confidence, 0.0, 1.0),
        ):
            if not lo <= val <= hi:
                raise ValueError(
                    f"{name} must be in [{lo}, {hi}], got {val}"
                )


@dataclass
class RepObservation:
    """A single rep's worth of joint samples + timing.

    ``samples`` is a per-frame list, each frame a list of joint
    samples across whatever joints the pose estimator found.
    Frames are chronologically ordered. ``duration_s`` is top-of-
    rep to top-of-rep; tempo cues read it.
    """

    rep_index: int
    duration_s: float
    samples: list[list[JointPoseSample]] = field(default_factory=list)
    # Post-rep heart-rate snapshot, if available. None = no wearable.
    hr_bpm: float | None = None
    # Post-rep breathing rate, if available.
    breathing_bpm: float | None = None

    def __post_init__(self) -> None:
        if self.rep_index < 0:
            raise ValueError(f"rep_index must be ≥ 0, got {self.rep_index}")
        if self.duration_s <= 0:
            raise ValueError(f"duration_s must be positive, got {self.duration_s}")
        if self.hr_bpm is not None and not 20 <= self.hr_bpm <= 250:
            raise ValueError(f"hr_bpm out of plausible range: {self.hr_bpm}")
        if self.breathing_bpm is not None and not 4 <= self.breathing_bpm <= 60:
            raise ValueError(f"breathing_bpm out of plausible range: {self.breathing_bpm}")


@dataclass
class ExerciseSession:
    """A complete set — N reps of one exercise by one trainee."""

    trainee_id: str
    exercise: ExerciseKind
    reps: list[RepObservation] = field(default_factory=list)
    # Optional: trainee's self-reported RPE on a 1-10 scale.
    reported_rpe: float | None = None

    def __post_init__(self) -> None:
        if not self.trainee_id:
            raise ValueError("trainee_id must not be empty")
        if self.exercise not in VALID_EXERCISES:
            raise ValueError(
                f"exercise must be one of {VALID_EXERCISES}, got {self.exercise!r}"
            )
        if self.reported_rpe is not None and not 1.0 <= self.reported_rpe <= 10.0:
            raise ValueError(f"reported_rpe must be in [1, 10], got {self.reported_rpe}")

    @property
    def rep_count(self) -> int:
        return len(self.reps)


# ---------------------------------------------------------------------------
# Engine output
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FormScore:
    """Per-rep form summary.

    Score components are all normalised so that 1.0 = textbook.
    ``overall`` is a weighted combination the engine produces.
    """

    rep_index: int
    symmetry: float
    depth: float
    tempo: float
    overall: float

    def __post_init__(self) -> None:
        for name, v in (
            ("symmetry", self.symmetry),
            ("depth", self.depth),
            ("tempo", self.tempo),
            ("overall", self.overall),
        ):
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {v}")


@dataclass(frozen=True)
class CoachCue:
    """A single coaching cue surfaced to the trainer / trainee.

    Wellness posture: the cue text MUST NOT contain medical
    vocabulary ("injured", "diagnose", "treat", "dangerous").
    It describes WHAT was observed and SUGGESTS an adjustment.
    """

    rep_index: int | None
    kind: CueKind
    severity: CueSeverity
    text: str
    observed_value: float | None = None

    def __post_init__(self) -> None:
        if self.severity not in VALID_SEVERITIES:
            raise ValueError(
                f"severity must be one of {VALID_SEVERITIES}, got {self.severity!r}"
            )
        if not self.text.strip():
            raise ValueError("cue text must not be empty")
        # Light claims guard — never emit the forbidden words.
        _FORBIDDEN = ("injured", "diagnose", "treat ", "dangerous", "medical")
        low = self.text.lower()
        for word in _FORBIDDEN:
            if word in low:
                raise ValueError(
                    f"cue text contains forbidden word {word!r} "
                    f"(wellness posture; see docs/PHILOSOPHY.md)"
                )


@dataclass
class CoachBriefing:
    """The form engine's output for a whole session."""

    session: ExerciseSession
    form_scores: list[FormScore] = field(default_factory=list)
    cues: list[CoachCue] = field(default_factory=list)
    session_overall: float = 0.0
    recovery_quality: float | None = None

    def cues_at_severity(self, severity: CueSeverity) -> list[CoachCue]:
        return [c for c in self.cues if c.severity == severity]

    def as_text(self) -> str:
        """Short human-readable summary. For the demo + tests."""
        lines: list[str] = []
        lines.append(
            f"Session: {self.session.trainee_id} · "
            f"{self.session.exercise} · {self.session.rep_count} reps"
        )
        lines.append(f"Overall form: {self.session_overall:.2f} / 1.00")
        if self.recovery_quality is not None:
            lines.append(f"Recovery quality: {self.recovery_quality:.2f} / 1.00")
        if not self.cues:
            lines.append("No cues surfaced — form looked consistent.")
            return "\n".join(lines)
        by_sev: dict[CueSeverity, list[CoachCue]] = {"severe": [], "minor": [], "ok": []}
        for cue in self.cues:
            by_sev[cue.severity].append(cue)
        for sev in ("severe", "minor"):  # "ok" is implicit, skip in briefing
            typed_sev: CueSeverity = sev  # type: ignore[assignment]
            if by_sev[typed_sev]:
                lines.append(f"{sev.upper()} cues:")
                for cue in by_sev[typed_sev]:
                    rep = f" rep {cue.rep_index + 1}" if cue.rep_index is not None else ""
                    lines.append(f"  - [{cue.kind}]{rep}: {cue.text}")
        return "\n".join(lines)


__all__ = [
    "CoachBriefing",
    "CoachCue",
    "ExerciseSession",
    "FormScore",
    "JointPoseSample",
    "RepObservation",
]


# Silence unused-import warning — ``Sequence`` stays importable for
# downstream modules that want a common type alias.
_ = Sequence
