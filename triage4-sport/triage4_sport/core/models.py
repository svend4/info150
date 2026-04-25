"""Core dataclasses for triage4-sport.

Three-audience output is the architectural contribution:
``CoachMessage`` (strict layperson — coach), ``TrainerNote``
(intermediate — athletic trainer), ``PhysicianAlert``
(permissive on clinical-observation vocabulary; positive
audit-trace requirement). Plus two universal forbidden
lists across all three (injury-prediction overreach +
athlete-data-sensitivity).

See docs/PHILOSOPHY.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import (
    ChannelKind,
    MovementKind,
    RiskBand,
    Sport,
    VALID_MOVEMENT_KINDS,
    VALID_RISK_BANDS,
    VALID_SPORTS,
)


# ---------------------------------------------------------------------------
# Raw observations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MovementSample:
    """One sport-specific movement event.

    ``form_asymmetry`` in [0, 1], 0 = symmetric form, 1 =
    one-sided. ``range_of_motion`` in [0, 1], 1 = full
    typical ROM, 0 = severely restricted.
    """

    t_s: float
    kind: MovementKind
    form_asymmetry: float
    range_of_motion: float

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if self.kind not in VALID_MOVEMENT_KINDS:
            raise ValueError(
                f"kind must be one of {VALID_MOVEMENT_KINDS}, "
                f"got {self.kind!r}"
            )
        for name, v in (
            ("form_asymmetry", self.form_asymmetry),
            ("range_of_motion", self.range_of_motion),
        ):
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {v}")


@dataclass(frozen=True)
class WorkloadSample:
    """GPS-vest aggregate for a session interval.

    Numbers are session-level totals, not instantaneous.
    Real GPS-vest products (Catapult / WIMU / StatSports)
    expose these as ``acwr`` / acute-chronic ratio inputs.
    """

    t_s: float
    distance_m: float
    high_speed_runs: int
    accelerations: int
    decelerations: int

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if self.distance_m < 0 or self.distance_m > 30000:
            raise ValueError(
                f"distance_m out of plausible range: {self.distance_m}"
            )
        for name, v in (
            ("high_speed_runs", self.high_speed_runs),
            ("accelerations", self.accelerations),
            ("decelerations", self.decelerations),
        ):
            if not 0 <= v <= 1000:
                raise ValueError(
                    f"{name} out of plausible range: {v}"
                )


@dataclass(frozen=True)
class RecoveryHRSample:
    """Post-effort HR-recovery snapshot.

    ``recovery_drop_bpm`` is the HR drop one minute after
    interval cessation. >= 30 is good recovery; < 12 is
    poor recovery.
    """

    t_s: float
    peak_hr_bpm: float
    recovery_drop_bpm: float

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if not 60.0 <= self.peak_hr_bpm <= 250.0:
            raise ValueError(
                f"peak_hr_bpm out of plausible range: {self.peak_hr_bpm}"
            )
        if not 0.0 <= self.recovery_drop_bpm <= 100.0:
            raise ValueError(
                f"recovery_drop_bpm out of plausible range: "
                f"{self.recovery_drop_bpm}"
            )


@dataclass(frozen=True)
class AthleteBaseline:
    """Per-athlete baseline from prior sessions.

    Computed by a consumer-app baseline-learner across weeks.
    The library accepts a baseline as engine input; it does
    not learn baselines itself (that work crosses the
    cross-session athlete-identity-persistence boundary the
    library deliberately avoids).
    """

    typical_form_asymmetry: float
    typical_workload_index: float
    typical_recovery_drop_bpm: float

    def __post_init__(self) -> None:
        for name, v in (
            ("typical_form_asymmetry", self.typical_form_asymmetry),
            ("typical_workload_index", self.typical_workload_index),
        ):
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {v}")
        if not 0.0 <= self.typical_recovery_drop_bpm <= 100.0:
            raise ValueError(
                f"typical_recovery_drop_bpm out of plausible range: "
                f"{self.typical_recovery_drop_bpm}"
            )


@dataclass
class AthleteObservation:
    """One training session for one athlete.

    ``athlete_token`` is opaque per-session — the library
    never persists cross-session athlete identity. See the
    athlete-data-sensitivity boundary in docs/PHILOSOPHY.md.
    """

    athlete_token: str
    sport: Sport
    session_duration_s: float
    movement_samples: list[MovementSample] = field(default_factory=list)
    workload_samples: list[WorkloadSample] = field(default_factory=list)
    recovery_samples: list[RecoveryHRSample] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.athlete_token:
            raise ValueError("athlete_token must not be empty")
        if self.sport not in VALID_SPORTS:
            raise ValueError(
                f"sport must be one of {VALID_SPORTS}, "
                f"got {self.sport!r}"
            )
        if self.session_duration_s <= 0 or self.session_duration_s > 21600:
            raise ValueError(
                f"session_duration_s must be in (0, 21600], "
                f"got {self.session_duration_s}"
            )


# ---------------------------------------------------------------------------
# Engine output
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PerformanceAssessment:
    """Per-session per-channel score + risk-band."""

    athlete_token: str
    form_asymmetry_safety: float
    workload_load_safety: float
    recovery_hr_safety: float
    baseline_deviation_safety: float
    overall: float
    risk_band: RiskBand

    def __post_init__(self) -> None:
        for name, v in (
            ("form_asymmetry_safety", self.form_asymmetry_safety),
            ("workload_load_safety", self.workload_load_safety),
            ("recovery_hr_safety", self.recovery_hr_safety),
            ("baseline_deviation_safety", self.baseline_deviation_safety),
            ("overall", self.overall),
        ):
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {v}")
        if self.risk_band not in VALID_RISK_BANDS:
            raise ValueError(
                f"risk_band must be one of {VALID_RISK_BANDS}, "
                f"got {self.risk_band!r}"
            )


# ---------------------------------------------------------------------------
# Universal forbidden lists — applied to every audience
# ---------------------------------------------------------------------------


_INJURY_PREDICTION_OVERREACH = (
    "predicts injury",
    "predict injury",
    "prevents injury",
    "prevent injury",
    "will get injured",
    "injury imminent",
    "guaranteed safe to return",
    "ready to play",
    "cleared to play",
    "no injury risk",
)

_TEAM_LEAGUE_TOKENS = (
    "nfl",
    "nba",
    "nhl",
    "mlb",
    "mls",
    "epl",
    "premier league",
    "la liga",
    "bundesliga",
    "serie a",
    "champions league",
)

_CAREER_JEOPARDY = (
    "will be cut",
    "roster decision",
    "will lose contract",
    "contract decision",
    "marketability impact",
    "marketability concern",
    "media attention warranted",
    "trade rumour",
    "trade rumor",
)

# Athlete-name identifier prefixes — shared across the three
# audience dataclasses.
_IDENTIFIER_PREFIXES: tuple[str, ...] = (
    "athlete john ",
    "athlete jane ",
    "athlete mike ",
    "athlete maria ",
    "athlete sam ",
    "athlete chris ",
    "player john ",
    "player jane ",
    "player mike ",
    "player maria ",
    "player sam ",
    "player chris ",
)


def _check_universal(text: str) -> None:
    """Raise if any universal-forbidden phrase appears."""
    low = text.lower()
    for word in _INJURY_PREDICTION_OVERREACH:
        if word in low:
            raise ValueError(
                f"alert text contains forbidden injury-prediction-"
                f"overreach phrase {word!r} (universal across all "
                f"audiences; see docs/PHILOSOPHY.md)"
            )
    for word in _TEAM_LEAGUE_TOKENS:
        if word in low:
            raise ValueError(
                f"alert text contains forbidden team / league name "
                f"{word!r} (athlete-data-sensitivity; see "
                f"docs/PHILOSOPHY.md)"
            )
    for word in _CAREER_JEOPARDY:
        if word in low:
            raise ValueError(
                f"alert text contains forbidden career-jeopardy "
                f"phrase {word!r} (athlete-data-sensitivity; see "
                f"docs/PHILOSOPHY.md)"
            )
    for prefix in _IDENTIFIER_PREFIXES:
        if prefix in low:
            raise ValueError(
                f"alert text appears to identify the athlete "
                f"({prefix!r}; athlete-data-sensitivity boundary; "
                f"see docs/PHILOSOPHY.md)"
            )


# ---------------------------------------------------------------------------
# CoachMessage — STRICT (no clinical jargon, no injury claims)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CoachMessage:
    """Coach-facing message — strict layperson guard."""

    athlete_token: str
    text: str

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("coach message text must not be empty")

        _check_universal(self.text)
        low = self.text.lower()

        _CLINICAL_JARGON = (
            "fracture",
            "tear",
            "sprain",
            "strain injury",
            "acl",
            "mcl",
            "pcl",
            "lcl",
            "rotator cuff",
            "meniscus",
            "labrum",
            "tendinitis",
            "tendonitis",
            "concussion",
            "medical clearance",
        )
        _DEFINITIVE_INJURY = (
            "is injured",
            "has an injury",
            "confirmed injury",
            "injury confirmed",
            "out for the season",
        )

        for word in _CLINICAL_JARGON:
            if word in low:
                raise ValueError(
                    f"coach message contains forbidden clinical "
                    f"jargon {word!r} (coach is non-clinical; see "
                    f"docs/PHILOSOPHY.md)"
                )
        for word in _DEFINITIVE_INJURY:
            if word in low:
                raise ValueError(
                    f"coach message contains forbidden definitive-"
                    f"injury phrase {word!r}"
                )


# ---------------------------------------------------------------------------
# TrainerNote — INTERMEDIATE (allows ROM / fatigue, no diagnosis)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TrainerNote:
    """Athletic-trainer-facing note — intermediate guard.

    Allows mild rehab vocabulary that the coach guard
    rejects (ROM, fatigue level, RPE, acute load) but
    blocks definitive diagnosis.
    """

    athlete_token: str
    text: str

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("trainer note text must not be empty")

        _check_universal(self.text)
        low = self.text.lower()

        _DEFINITIVE_DIAGNOSIS = (
            "tear visible",
            "fracture confirmed",
            "confirmed diagnosis",
            "diagnosis:",
            "diagnosis is",
        )
        for word in _DEFINITIVE_DIAGNOSIS:
            if word in low:
                raise ValueError(
                    f"trainer note contains forbidden definitive-"
                    f"diagnosis phrase {word!r} (the team physician "
                    f"diagnoses; see docs/PHILOSOPHY.md)"
                )


# ---------------------------------------------------------------------------
# PhysicianAlert — PERMISSIVE clinical + POSITIVE audit-trace requirement
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PhysicianAlert:
    """Team-physician facing alert.

    Permits clinical-observation vocabulary the coach +
    trainer guards reject (`flexion deficit`, `gait
    asymmetry`, etc.). Still rejects definitive diagnosis.
    REQUIRES non-empty ``reasoning_trace`` — audit-readiness
    pattern from triage4-clinic.
    """

    athlete_token: str
    text: str
    reasoning_trace: str

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("physician alert text must not be empty")
        if not self.reasoning_trace.strip():
            raise ValueError(
                "physician alert must carry a non-empty "
                "reasoning_trace (audit-readiness; see "
                "docs/PHILOSOPHY.md)"
            )

        _check_universal(self.text)
        low = self.text.lower()

        _DEFINITIVE_DIAGNOSIS = (
            "diagnosis:",
            "diagnosis is",
            "confirmed diagnosis",
            "the athlete has a fracture",
            "the athlete has an acl tear",
            "the athlete has a meniscus tear",
        )
        for word in _DEFINITIVE_DIAGNOSIS:
            if word in low:
                raise ValueError(
                    f"physician alert contains forbidden definitive-"
                    f"diagnosis phrase {word!r} (the physician "
                    f"examines and decides; see docs/PHILOSOPHY.md)"
                )


@dataclass
class SessionReport:
    """Per-session output bundle — three streams + assessment."""

    athlete_token: str
    assessment: PerformanceAssessment
    coach_messages: list[CoachMessage] = field(default_factory=list)
    trainer_notes: list[TrainerNote] = field(default_factory=list)
    physician_alert: PhysicianAlert | None = None

    def __post_init__(self) -> None:
        if not self.athlete_token:
            raise ValueError("athlete_token must not be empty")

    def alerts_count(self) -> int:
        return (
            len(self.coach_messages)
            + len(self.trainer_notes)
            + (1 if self.physician_alert is not None else 0)
        )

    def as_text(self) -> str:
        a = self.assessment
        lines = [
            f"Athlete: {self.athlete_token} · risk={a.risk_band}",
            f"  channels — form={a.form_asymmetry_safety:.2f}  "
            f"workload={a.workload_load_safety:.2f}  "
            f"recovery={a.recovery_hr_safety:.2f}  "
            f"baseline={a.baseline_deviation_safety:.2f}  "
            f"overall={a.overall:.2f}",
        ]
        if self.coach_messages:
            lines.append("  COACH:")
            for m in self.coach_messages:
                lines.append(f"    - {m.text}")
        if self.trainer_notes:
            lines.append("  TRAINER:")
            for n in self.trainer_notes:
                lines.append(f"    - {n.text}")
        if self.physician_alert is not None:
            lines.append("  PHYSICIAN:")
            lines.append(f"    - {self.physician_alert.text}")
            lines.append(
                f"      reasoning: {self.physician_alert.reasoning_trace}"
            )
        if self.alerts_count() == 0:
            lines.append(
                "  No alerts surfaced. Routine review by the "
                "athletic trainer remains required."
            )
        return "\n".join(lines)


__all__ = [
    "AthleteBaseline",
    "AthleteObservation",
    "CoachMessage",
    "MovementSample",
    "PerformanceAssessment",
    "PhysicianAlert",
    "RecoveryHRSample",
    "SessionReport",
    "TrainerNote",
    "WorkloadSample",
    "ChannelKind",
]
