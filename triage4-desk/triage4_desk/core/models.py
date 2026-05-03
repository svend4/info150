"""Core dataclasses for triage4-desk.

Domain: a single-person desk-worker advisor. The unit of input is a
``DeskSession`` (one continuous work window of N minutes); the unit
of output is a ``DeskAdvisory`` (channel scores + cues).

Wellness posture, not clinical. The engine never names a medical
condition — it describes what was observed and suggests adjustments
(stretch, drink water, look away from the screen, walk).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import (
    CueKind,
    CueSeverity,
    PostureAdvisory,
    VALID_POSTURE_ADVISORIES,
    VALID_SEVERITIES,
    VALID_WORK_MODES,
    WorkMode,
)


# ---------------------------------------------------------------------------
# Raw observation
# ---------------------------------------------------------------------------


@dataclass
class DeskSession:
    """One work window — typically 5-180 minutes.

    Channel inputs are normalised scalars from camera + manual UI
    sliders + optional wearable. The engine combines them into the
    advisory; it does not store raw frames.
    """

    worker_id: str
    work_mode: WorkMode
    session_min: float           # continuous minutes at desk
    minutes_since_break: float   # since last microbreak (water / eyes / posture)
    minutes_since_stretch: float # since last stretch / standing break
    typing_intensity: float      # camera or keylog proxy in [0, 1]
    screen_motion_proxy: float   # camera-derived motion in [0, 1]
    ambient_light_proxy: float   # camera-derived luminance in [0, 1]
    posture_quality: float       # 1.0 = upright, 0.0 = slumped
    drowsiness_signal: float = 0.0    # adapted from triage4-drive
    distraction_signal: float = 0.0   # adapted from triage4-drive
    air_temp_c: float | None = None
    hr_bpm: float | None = None

    def __post_init__(self) -> None:
        if not self.worker_id:
            raise ValueError("worker_id must not be empty")
        if self.work_mode not in VALID_WORK_MODES:
            raise ValueError(
                f"work_mode must be one of {VALID_WORK_MODES}, "
                f"got {self.work_mode!r}"
            )
        for name, val, lo, hi in (
            ("session_min",           self.session_min,           0.0, 24 * 60),
            ("minutes_since_break",   self.minutes_since_break,   0.0, 24 * 60),
            ("minutes_since_stretch", self.minutes_since_stretch, 0.0, 24 * 60),
        ):
            if not lo <= val <= hi:
                raise ValueError(f"{name} must be in [{lo}, {hi}], got {val}")
        for name, val in (
            ("typing_intensity",     self.typing_intensity),
            ("screen_motion_proxy",  self.screen_motion_proxy),
            ("ambient_light_proxy",  self.ambient_light_proxy),
            ("posture_quality",      self.posture_quality),
            ("drowsiness_signal",    self.drowsiness_signal),
            ("distraction_signal",   self.distraction_signal),
        ):
            if not 0.0 <= val <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {val}")
        if self.air_temp_c is not None and not -10.0 <= self.air_temp_c <= 50.0:
            raise ValueError(
                f"air_temp_c out of plausible office range, got {self.air_temp_c}"
            )
        if self.hr_bpm is not None and not 30.0 <= self.hr_bpm <= 220.0:
            raise ValueError(
                f"hr_bpm out of plausible range [30, 220], got {self.hr_bpm}"
            )


# ---------------------------------------------------------------------------
# Engine output
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CoachCue:
    """A single coaching cue surfaced to the worker.

    Wellness posture: the cue text MUST NOT contain medical
    vocabulary. It describes WHAT was observed and SUGGESTS an
    adjustment.
    """

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
        _FORBIDDEN = ("injured", "diagnose", "treat ", "dangerous", "medical")
        low = self.text.lower()
        for word in _FORBIDDEN:
            if word in low:
                raise ValueError(
                    f"cue text contains forbidden word {word!r} "
                    f"(wellness posture; see docs/PHILOSOPHY.md)"
                )


@dataclass
class DeskAdvisory:
    """Engine output for one session.

    Channel scores are 1.0 = great, 0.0 = poor.
    """

    session: DeskSession
    fatigue_index: float
    hydration_due: bool
    eye_break_due: bool
    microbreak_due: bool
    stretch_due: bool
    posture_advisory: PostureAdvisory
    drowsiness_alert: bool
    distraction_alert: bool
    overall_safety: float
    cues: list[CoachCue] = field(default_factory=list)

    def __post_init__(self) -> None:
        for name, v in (
            ("fatigue_index", self.fatigue_index),
            ("overall_safety", self.overall_safety),
        ):
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {v}")
        if self.posture_advisory not in VALID_POSTURE_ADVISORIES:
            raise ValueError(
                f"posture_advisory must be one of {VALID_POSTURE_ADVISORIES}, "
                f"got {self.posture_advisory!r}"
            )

    def cues_at_severity(self, severity: CueSeverity) -> list[CoachCue]:
        return [c for c in self.cues if c.severity == severity]

    def as_text(self) -> str:
        lines: list[str] = []
        s = self.session
        lines.append(
            f"Worker {s.worker_id} · {s.work_mode} · session {s.session_min:.0f} min · "
            f"break {s.minutes_since_break:.0f} min ago"
        )
        lines.append(
            f"Fatigue: {self.fatigue_index:.2f}   Overall: {self.overall_safety:.2f}   "
            f"Posture: {self.posture_advisory}"
        )
        flags: list[str] = []
        if self.hydration_due:
            flags.append("hydration_due")
        if self.eye_break_due:
            flags.append("eye_break_due")
        if self.microbreak_due:
            flags.append("microbreak_due")
        if self.stretch_due:
            flags.append("stretch_due")
        if self.drowsiness_alert:
            flags.append("drowsiness_alert")
        if self.distraction_alert:
            flags.append("distraction_alert")
        if flags:
            lines.append("Flags: " + ", ".join(flags))
        if not self.cues:
            lines.append("No cues — keep working comfortably.")
            return "\n".join(lines)
        for sev in ("severe", "minor"):
            typed_sev: CueSeverity = sev  # type: ignore[assignment]
            for c in self.cues_at_severity(typed_sev):
                lines.append(f"  [{sev}] [{c.kind}] {c.text}")
        return "\n".join(lines)


__all__ = [
    "CoachCue",
    "DeskAdvisory",
    "DeskSession",
]
