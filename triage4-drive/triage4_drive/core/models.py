"""Core dataclasses for triage4-drive.

Intentionally flat, frozen where sensible, no methods beyond
validation + a short `as_text` on the aggregate. Copy-fork of
the sibling pattern with a triple claims guard on
``DispatcherAlert`` — clinical + operational + privacy. See
docs/PHILOSOPHY.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import (
    AlertKind,
    AlertLevel,
    GazeRegion,
    VALID_ALERT_KINDS,
    VALID_ALERT_LEVELS,
    VALID_GAZE_REGIONS,
)


# ---------------------------------------------------------------------------
# Raw observations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EyeStateSample:
    """Eyelid-closure at one instant.

    ``closure`` in [0, 1] — 0 = fully open, 1 = fully closed.
    In production, this comes from the eye-aspect-ratio or a
    Face-Mesh-derived lid-distance ratio. At the MVP layer we
    consume whatever upstream reports, on the assumption it's
    already normalised per the calibration spec.
    """

    t_s: float
    closure: float

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if not 0.0 <= self.closure <= 1.0:
            raise ValueError(
                f"closure must be in [0, 1], got {self.closure}"
            )


@dataclass(frozen=True)
class GazeSample:
    """Gaze region at one instant."""

    t_s: float
    region: GazeRegion

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if self.region not in VALID_GAZE_REGIONS:
            raise ValueError(
                f"region must be one of {VALID_GAZE_REGIONS}, "
                f"got {self.region!r}"
            )


@dataclass(frozen=True)
class PostureSample:
    """Driver posture at one instant — normalised [0, 1] coords.

    Two minimal keypoints: ``nose_y`` (vertical position of
    the nose tip) and ``shoulder_midline_y`` (midpoint of the
    two shoulders). A growing delta between the two over a
    short window = slumping, the primary incapacitation
    signal this library reads.
    """

    t_s: float
    nose_y: float
    shoulder_midline_y: float

    def __post_init__(self) -> None:
        for name, v in (
            ("nose_y", self.nose_y),
            ("shoulder_midline_y", self.shoulder_midline_y),
        ):
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {v}")
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")


@dataclass(frozen=True)
class CanBusSample:
    """Optional CAN-bus snapshot.

    Reserved for a future engine pass that cross-correlates
    driver state with vehicle dynamics. The MVP engine does
    not yet use these fields — they're accepted on
    ``DriverObservation`` so consumer apps can pass them
    without rewriting the dataclass.
    """

    t_s: float
    speed_kmh: float | None = None
    steering_angle_deg: float | None = None
    lane_departure: bool | None = None

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if self.speed_kmh is not None and not 0 <= self.speed_kmh <= 300:
            raise ValueError(
                f"speed_kmh out of plausible range: {self.speed_kmh}"
            )
        if self.steering_angle_deg is not None and not -720 <= self.steering_angle_deg <= 720:
            raise ValueError(
                f"steering_angle_deg out of plausible range: "
                f"{self.steering_angle_deg}"
            )


@dataclass
class DriverObservation:
    """One observation window of a single driver in one cab.

    A "window" is a few seconds to a few minutes of samples,
    chronologically ordered. The engine consumes one
    observation at a time — no cross-session state persists
    at this layer (privacy boundary).
    """

    # Opaque session identifier. Not a driver identifier —
    # see docs/PHILOSOPHY.md. The library never correlates
    # session_id to a human.
    session_id: str
    window_duration_s: float
    eye_samples: list[EyeStateSample] = field(default_factory=list)
    gaze_samples: list[GazeSample] = field(default_factory=list)
    posture_samples: list[PostureSample] = field(default_factory=list)
    can_samples: list[CanBusSample] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("session_id must not be empty")
        if self.window_duration_s <= 0:
            raise ValueError(
                f"window_duration_s must be positive, "
                f"got {self.window_duration_s}"
            )


# ---------------------------------------------------------------------------
# Engine output
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FatigueScore:
    """Per-window driver-state summary.

    Channels are unit-interval risk scores — 0.0 = textbook
    alert driver, 1.0 = maximum fatigue / distraction /
    incapacitation signal. ``overall`` is a weighted
    combination the engine produces. Note the SIGN convention
    is flipped relative to fit / farm where higher = better —
    here higher = worse because "drowsiness" and "distraction"
    read more naturally as risk.
    """

    session_id: str
    perclos: float
    distraction: float
    incapacitation: float
    overall: float
    alert_level: AlertLevel

    def __post_init__(self) -> None:
        for name, v in (
            ("perclos", self.perclos),
            ("distraction", self.distraction),
            ("incapacitation", self.incapacitation),
            ("overall", self.overall),
        ):
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {v}")
        if self.alert_level not in VALID_ALERT_LEVELS:
            raise ValueError(
                f"alert_level must be one of {VALID_ALERT_LEVELS}, "
                f"got {self.alert_level!r}"
            )


# Pattern list for the privacy claims guard. Matches anything
# that looks like a first-name reference ("driver Maria",
# "driver J.", etc.) without storing the names themselves —
# the list is a small sample of the commonest tokens. Real
# deployments would extend with localisation-specific lists.
_IDENTIFIER_PREFIXES: tuple[str, ...] = (
    "driver john",
    "driver jane",
    "driver mike",
    "driver maria",
    "driver sam",
    "driver alex",
    "driver chris",
    "driver james",
    "driver mary",
    "driver robert",
)


@dataclass(frozen=True)
class DispatcherAlert:
    """A single dispatcher-facing alert.

    Triple claims guard enforced at construction time. See
    docs/PHILOSOPHY.md for rationale on each list.
    """

    session_id: str
    kind: AlertKind
    level: AlertLevel
    text: str
    observed_value: float | None = None

    def __post_init__(self) -> None:
        if self.kind not in VALID_ALERT_KINDS:
            raise ValueError(
                f"kind must be one of {VALID_ALERT_KINDS}, got {self.kind!r}"
            )
        if self.level not in VALID_ALERT_LEVELS:
            raise ValueError(
                f"level must be one of {VALID_ALERT_LEVELS}, got {self.level!r}"
            )
        if not self.text.strip():
            raise ValueError("alert text must not be empty")

        low = self.text.lower()

        _CLINICAL_FORBIDDEN = (
            "diagnose",
            "diagnosis",
            "prescribe",
            "medicate",
            "administer",
            "drunk",
            "intoxicated",
            "under the influence",
            "stroke",
            "arrhythmia",
            "seizure",
            "heart attack",
            "pronounced",
            "confirmed deceased",
        )
        _OPERATIONAL_FORBIDDEN = (
            "auto-brake",
            "stop the vehicle",
            "pull over now",
            "disengage autopilot",
            "take over",
            "apply brake",
            "brake now",
            "accelerate",
        )
        _PRIVACY_FORBIDDEN = (
            "same driver as",
            "matches previous driver",
            "driver identity",
            "biometric match",
            "facial print",
            "identify the driver",
            "driver's face print",
        )

        for word in _CLINICAL_FORBIDDEN:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden clinical word {word!r} "
                    f"(clinical boundary; see docs/PHILOSOPHY.md)"
                )
        for word in _OPERATIONAL_FORBIDDEN:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden operational-command "
                    f"word {word!r} (operational boundary; "
                    f"see docs/PHILOSOPHY.md)"
                )
        for word in _PRIVACY_FORBIDDEN:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden privacy / "
                    f"identification phrase {word!r} (privacy boundary; "
                    f"see docs/PHILOSOPHY.md)"
                )
        # Personal-identifier heuristic: any text starting with
        # "driver <firstname>" from a small common-name list.
        for prefix in _IDENTIFIER_PREFIXES:
            if prefix in low:
                raise ValueError(
                    f"alert text appears to identify the driver "
                    f"({prefix!r}; privacy boundary; "
                    f"see docs/PHILOSOPHY.md)"
                )


@dataclass
class DrivingSession:
    """Aggregate view across multiple windows of one session.

    Consumer apps typically hold one of these per cab session
    and append to it as new windows arrive. The library itself
    treats this as a data container — no cross-window logic
    lives here.
    """

    session_id: str
    scores: list[FatigueScore] = field(default_factory=list)
    alerts: list[DispatcherAlert] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("session_id must not be empty")

    @property
    def window_count(self) -> int:
        return len(self.scores)

    def alerts_at_level(self, level: AlertLevel) -> list[DispatcherAlert]:
        return [a for a in self.alerts if a.level == level]

    def latest_overall(self) -> float:
        return self.scores[-1].overall if self.scores else 0.0

    def as_text(self) -> str:
        """Short human-readable summary — for the demo + tests."""
        lines = [
            f"Session: {self.session_id} · "
            f"{self.window_count} observation window"
            f"{'s' if self.window_count != 1 else ''}",
        ]
        if self.scores:
            last = self.scores[-1]
            lines.append(
                f"Latest: overall risk {last.overall:.2f} · "
                f"PERCLOS {last.perclos:.2f} · "
                f"distraction {last.distraction:.2f} · "
                f"incapacitation {last.incapacitation:.2f} · "
                f"level={last.alert_level}"
            )
        critical = self.alerts_at_level("critical")
        caution = self.alerts_at_level("caution")
        if critical:
            lines.append("CRITICAL alerts:")
            for a in critical:
                lines.append(f"  - [{a.kind}]: {a.text}")
        if caution:
            lines.append("CAUTION alerts:")
            for a in caution:
                lines.append(f"  - [{a.kind}]: {a.text}")
        if not critical and not caution:
            lines.append("No caution / critical alerts surfaced.")
        return "\n".join(lines)


__all__ = [
    "CanBusSample",
    "DispatcherAlert",
    "DriverObservation",
    "DrivingSession",
    "EyeStateSample",
    "FatigueScore",
    "GazeSample",
    "PostureSample",
]
