"""Core dataclasses for triage4-home.

Intentionally flat, frozen where sensible, no methods beyond
validation + a short `as_text` on the aggregate. Copy-fork of
the sibling pattern, with a **quadruple** claims guard on
``CaregiverAlert`` — clinical + operational + privacy +
dignity. The dignity list is new in this sibling; see
docs/PHILOSOPHY.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import (
    ActivityIntensity,
    AlertKind,
    AlertLevel,
    RoomKind,
    VALID_ALERT_KINDS,
    VALID_ALERT_LEVELS,
    VALID_INTENSITIES,
    VALID_ROOM_KINDS,
)


# ---------------------------------------------------------------------------
# Raw observations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ImpactSample:
    """One impact candidate from the home sensor hub.

    ``magnitude_g`` is the peak acceleration in units of
    Earth gravity at the impact instant. 1.0 g = resting; a
    fall typically peaks 2-5 g depending on surface. The
    post-impact stillness window is reported separately, in
    seconds — a long stillness combined with a high
    magnitude is the two-factor fall signature.
    """

    t_s: float
    magnitude_g: float
    stillness_after_s: float

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if not 0.0 <= self.magnitude_g <= 30.0:
            raise ValueError(
                f"magnitude_g out of plausible range: {self.magnitude_g}"
            )
        if self.stillness_after_s < 0:
            raise ValueError(
                f"stillness_after_s must be ≥ 0, got "
                f"{self.stillness_after_s}"
            )


@dataclass(frozen=True)
class ActivitySample:
    """Coarse activity bucket at one observation instant.

    Produced by the sensor-hub layer from whatever primitive
    it has available (passive-infrared motion, depth-camera
    skeleton energy, wearable step count). This library
    consumes the bucketised result.
    """

    t_s: float
    intensity: ActivityIntensity

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if self.intensity not in VALID_INTENSITIES:
            raise ValueError(
                f"intensity must be one of {VALID_INTENSITIES}, "
                f"got {self.intensity!r}"
            )


@dataclass(frozen=True)
class RoomTransition:
    """One room-to-room transition event.

    ``distance_m`` is the approximate path length for the
    transit (set by the sensor-hub's home map).
    ``duration_s`` is the actual transit time — the elapsed
    wall time from leaving ``from_room`` to entering
    ``to_room``. The two fields together give the pace
    estimate (distance / duration). Time between
    transitions is NOT the same as transit time (the
    resident may have stopped in a room for an hour), so
    the signature requires an explicit duration.
    """

    t_s: float
    from_room: RoomKind
    to_room: RoomKind
    distance_m: float
    duration_s: float

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if self.from_room not in VALID_ROOM_KINDS:
            raise ValueError(
                f"from_room must be one of {VALID_ROOM_KINDS}, "
                f"got {self.from_room!r}"
            )
        if self.to_room not in VALID_ROOM_KINDS:
            raise ValueError(
                f"to_room must be one of {VALID_ROOM_KINDS}, "
                f"got {self.to_room!r}"
            )
        if self.from_room == self.to_room:
            raise ValueError(
                f"from_room and to_room must differ, both are "
                f"{self.from_room!r}"
            )
        if not 0.5 <= self.distance_m <= 50.0:
            raise ValueError(
                f"distance_m out of plausible range: {self.distance_m}"
            )
        if not 0.5 <= self.duration_s <= 300.0:
            raise ValueError(
                f"duration_s out of plausible range: {self.duration_s}"
            )


@dataclass
class ResidentObservation:
    """One observation window for a single resident.

    A "window" is typically one day. The engine consumes one
    observation at a time. Cross-day baselines are computed
    by the caller and passed into the engine separately — no
    state is persisted inside this layer.
    """

    # Opaque window identifier — NOT a resident identifier.
    # See docs/PHILOSOPHY.md. The library never correlates
    # the window_id to a person.
    window_id: str
    window_duration_s: float
    impacts: list[ImpactSample] = field(default_factory=list)
    activity_samples: list[ActivitySample] = field(default_factory=list)
    transitions: list[RoomTransition] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.window_id:
            raise ValueError("window_id must not be empty")
        if self.window_duration_s <= 0:
            raise ValueError(
                f"window_duration_s must be positive, "
                f"got {self.window_duration_s}"
            )


# ---------------------------------------------------------------------------
# Engine output
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WellnessScore:
    """Per-window wellness summary.

    Channels in [0, 1] — 1.0 = textbook for the resident's
    own baseline, 0.0 = strong deviation. ``overall`` is a
    weighted combination. NOT a clinical assessment — the
    library is observation-only.
    """

    window_id: str
    fall_risk: float            # 0 = no fall candidate, 1 = clear candidate
    activity_alignment: float   # 1 = matches baseline, 0 = far off
    mobility_trend: float       # 1 = stable / improving, 0 = marked decline
    overall: float
    alert_level: AlertLevel

    def __post_init__(self) -> None:
        for name, v in (
            ("fall_risk", self.fall_risk),
            ("activity_alignment", self.activity_alignment),
            ("mobility_trend", self.mobility_trend),
            ("overall", self.overall),
        ):
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {v}")
        if self.alert_level not in VALID_ALERT_LEVELS:
            raise ValueError(
                f"alert_level must be one of {VALID_ALERT_LEVELS}, "
                f"got {self.alert_level!r}"
            )


# Identifier-prefix guard — same small common-name list
# triage4-drive uses, adapted for resident context. Not an
# exhaustive list; the real deployment would layer a
# jurisdiction-specific list on top.
_IDENTIFIER_PREFIXES: tuple[str, ...] = (
    "resident john",
    "resident jane",
    "resident mike",
    "resident maria",
    "resident sam",
    "resident alex",
    "resident chris",
    "resident james",
    "resident mary",
    "resident robert",
)


@dataclass(frozen=True)
class CaregiverAlert:
    """A single caregiver-facing alert.

    Quadruple claims guard enforced at construction time.
    See docs/PHILOSOPHY.md for rationale on each list.
    """

    window_id: str
    kind: AlertKind
    level: AlertLevel
    text: str
    observed_value: float | None = None

    def __post_init__(self) -> None:
        if self.kind not in VALID_ALERT_KINDS:
            raise ValueError(
                f"kind must be one of {VALID_ALERT_KINDS}, "
                f"got {self.kind!r}"
            )
        if self.level not in VALID_ALERT_LEVELS:
            raise ValueError(
                f"level must be one of {VALID_ALERT_LEVELS}, "
                f"got {self.level!r}"
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
            "dementia",
            "alzheimer",
            "parkinson",
            "cognitive decline",
            "cognitive impairment",
            "dehydrated",
            "malnourished",
            "infection",
            "sepsis",
            "pronounced",
            "confirmed deceased",
        )
        _OPERATIONAL_FORBIDDEN = (
            "call 911",
            "call 112",
            "dispatch ambulance",
            "call emergency services",
            "activate medical alarm",
            "contact the paramedic",
        )
        _PRIVACY_FORBIDDEN = (
            "previous resident",
            "same resident as",
            "identify the resident",
            "biometric match",
            "facial print",
            "voice print",
        )
        _DIGNITY_FORBIDDEN = (
            "confused",
            "disoriented",
            "incompetent",
            "cannot care for themselves",
            "dementia patient",
            "demented",
            "wandering",
            "deteriorating",
            "senile",
            "feeble",
            "frail",
        )

        for word in _CLINICAL_FORBIDDEN:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden clinical word "
                    f"{word!r} (clinical boundary; "
                    f"see docs/PHILOSOPHY.md)"
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
        for word in _DIGNITY_FORBIDDEN:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden dignity-eroding "
                    f"word {word!r} (dignity boundary; "
                    f"see docs/PHILOSOPHY.md)"
                )
        for prefix in _IDENTIFIER_PREFIXES:
            if prefix in low:
                raise ValueError(
                    f"alert text appears to identify the resident "
                    f"({prefix!r}; privacy boundary; "
                    f"see docs/PHILOSOPHY.md)"
                )


@dataclass
class HomeReport:
    """Aggregate across one or more windows in a single residence.

    Consumer apps typically hold one of these per residence
    and append scores + alerts as new windows arrive. The
    library treats it as a data container; no cross-window
    inference lives here.
    """

    residence_id: str
    scores: list[WellnessScore] = field(default_factory=list)
    alerts: list[CaregiverAlert] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.residence_id:
            raise ValueError("residence_id must not be empty")

    @property
    def window_count(self) -> int:
        return len(self.scores)

    def alerts_at_level(self, level: AlertLevel) -> list[CaregiverAlert]:
        return [a for a in self.alerts if a.level == level]

    def latest_overall(self) -> float:
        return self.scores[-1].overall if self.scores else 1.0

    def as_text(self) -> str:
        """Short human-readable summary — for the demo + tests."""
        lines = [
            f"Residence: {self.residence_id} · "
            f"{self.window_count} observation window"
            f"{'s' if self.window_count != 1 else ''}",
        ]
        if self.scores:
            last = self.scores[-1]
            lines.append(
                f"Latest wellness: overall {last.overall:.2f} · "
                f"fall_risk {last.fall_risk:.2f} · "
                f"activity {last.activity_alignment:.2f} · "
                f"mobility {last.mobility_trend:.2f} · "
                f"level={last.alert_level}"
            )
        urgent = self.alerts_at_level("urgent")
        check = self.alerts_at_level("check_in")
        if urgent:
            lines.append("URGENT alerts:")
            for a in urgent:
                lines.append(f"  - [{a.kind}]: {a.text}")
        if check:
            lines.append("CHECK-IN alerts:")
            for a in check:
                lines.append(f"  - [{a.kind}]: {a.text}")
        if not urgent and not check:
            lines.append("No check-in / urgent alerts surfaced.")
        return "\n".join(lines)


__all__ = [
    "ActivitySample",
    "CaregiverAlert",
    "HomeReport",
    "ImpactSample",
    "ResidentObservation",
    "RoomTransition",
    "WellnessScore",
]
