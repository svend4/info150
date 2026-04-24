"""Core dataclasses for triage4-aqua.

Flat + frozen + validation-only. Copy-fork of the sibling
shape. Seven forbidden-vocabulary lists on
``LifeguardAlert`` — same six the prior siblings cumulative
and one new (no-false-reassurance). See docs/PHILOSOPHY.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import (
    AlertKind,
    AlertLevel,
    PoolCondition,
    VALID_ALERT_KINDS,
    VALID_ALERT_LEVELS,
    VALID_POOL_CONDITIONS,
    VALID_WATER_ZONES,
    WaterZone,
)


# ---------------------------------------------------------------------------
# Raw observation samples
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SurfacePoseSample:
    """Above-water pose sample for one swimmer at one instant.

    ``head_height_rel`` in [0, 1]: 0 = at / below the water
    line, 1 = clearly above. ``body_vertical`` in [0, 1]: 0
    = horizontal (swimming), 1 = vertical (IDR-like upright).
    ``motion_rhythm`` in [0, 1]: 0 = non-rhythmic / flailing,
    1 = rhythmic swim stroke.
    """

    t_s: float
    head_height_rel: float
    body_vertical: float
    motion_rhythm: float

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        for name, v in (
            ("head_height_rel", self.head_height_rel),
            ("body_vertical", self.body_vertical),
            ("motion_rhythm", self.motion_rhythm),
        ):
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {v}")


@dataclass(frozen=True)
class SubmersionSample:
    """Per-frame below-surface boolean for one swimmer.

    ``submerged`` is True when the upstream detector reads the
    swimmer as below the water line at ``t_s``. The signature
    layer reduces these samples to the longest consecutive
    run, which is the submersion-duration primary signal.
    """

    t_s: float
    submerged: bool

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")


@dataclass(frozen=True)
class SwimmerPresenceSample:
    """Presence / activity heartbeat for one swimmer.

    ``active`` is True when the swimmer was observed
    (surface, submersion, or motion) in the last tracker
    cycle. Used by the absent-swimmer signature — a swimmer
    with no recent activity hasn't visibly surfaced and
    hasn't exited the zone.
    """

    t_s: float
    active: bool

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")


@dataclass
class SwimmerObservation:
    """One swimmer's observation window.

    ``swimmer_token`` is an opaque identifier from the pool's
    tracker layer — NOT a face print, NOT a name. The
    library never correlates the token to a person.
    """

    swimmer_token: str
    zone: WaterZone
    window_duration_s: float
    surface_samples: list[SurfacePoseSample] = field(default_factory=list)
    submersion_samples: list[SubmersionSample] = field(default_factory=list)
    presence_samples: list[SwimmerPresenceSample] = field(default_factory=list)
    pool_condition: PoolCondition = "clear"

    def __post_init__(self) -> None:
        if not self.swimmer_token:
            raise ValueError("swimmer_token must not be empty")
        if self.zone not in VALID_WATER_ZONES:
            raise ValueError(
                f"zone must be one of {VALID_WATER_ZONES}, "
                f"got {self.zone!r}"
            )
        if self.window_duration_s <= 0:
            raise ValueError(
                f"window_duration_s must be positive, "
                f"got {self.window_duration_s}"
            )
        if self.pool_condition not in VALID_POOL_CONDITIONS:
            raise ValueError(
                f"pool_condition must be one of "
                f"{VALID_POOL_CONDITIONS}, got {self.pool_condition!r}"
            )


# ---------------------------------------------------------------------------
# Engine output
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AquaticScore:
    """Per-swimmer aquatic-safety summary.

    All channels in [0, 1], 1.0 = textbook-safe swimmer,
    0.0 = strong drowning signal. ``overall`` is the fused
    weighted combination. Per-swimmer, but per-swimmer in
    the anonymous-token sense — never tied to identity.
    """

    swimmer_token: str
    submersion_safety: float
    idr_safety: float
    absent_safety: float
    distress_safety: float
    overall: float
    alert_level: AlertLevel

    def __post_init__(self) -> None:
        for name, v in (
            ("submersion_safety", self.submersion_safety),
            ("idr_safety", self.idr_safety),
            ("absent_safety", self.absent_safety),
            ("distress_safety", self.distress_safety),
            ("overall", self.overall),
        ):
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {v}")
        if self.alert_level not in VALID_ALERT_LEVELS:
            raise ValueError(
                f"alert_level must be one of {VALID_ALERT_LEVELS}, "
                f"got {self.alert_level!r}"
            )


_IDENTIFIER_PREFIXES: tuple[str, ...] = (
    "swimmer john",
    "swimmer jane",
    "swimmer mike",
    "swimmer maria",
    "swimmer sam",
    "swimmer alex",
    "swimmer chris",
    "swimmer james",
    "swimmer mary",
    "swimmer robert",
)


@dataclass(frozen=True)
class LifeguardAlert:
    """Lifeguard-pendant facing alert.

    Seven-boundary claims guard at construction. See
    docs/PHILOSOPHY.md — especially the no-false-reassurance
    list, which is new in this sibling.
    """

    swimmer_token: str
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
            "cardiac arrest",
            "heart attack",
            "stroke",
            "secondary drowning",
            "dry drowning",
            "hypoxia",
            "hypoxic",
            "pronounced",
            "confirmed deceased",
        )
        _OPERATIONAL_FORBIDDEN = (
            "call 911",
            "call 112",
            "dispatch ambulance",
            "call emergency services",
            "perform cpr",
            "begin chest compressions",
            "defibrillate",
        )
        _PRIVACY_FORBIDDEN = (
            "child in red",
            "child wearing",
            "boy in swimsuit",
            "girl in swimsuit",
            "female swimmer",
            "male swimmer",
            "approximate age",
            "looks about",
            "biometric match",
            "facial print",
        )
        _DIGNITY_FORBIDDEN = (
            "drowning victim",
            "the swimmer who drowned",
            "overweight swimmer",
            "unfit swimmer",
        )
        _LABOR_FORBIDDEN = (
            "lifeguard performance",
            "lifeguard performance metric",
            "lifeguard missed",
            "lifeguard discipline",
            "lifeguard reprimand",
            "lifeguard write-up",
        )
        _PANIC_FORBIDDEN = (
            "tragedy",
            "tragic",
            "disaster",
            "catastrophe",
            "catastrophic",
            "fatality",
            "fatalities",
            "mass casualty",
            "lethal",
            "deadly",
            "victim count",
        )
        _FALSE_REASSURANCE_FORBIDDEN = (
            "all clear",
            "pool is safe",
            "beach is safe",
            "no drowning",
            "no incidents",
            "all swimmers safe",
            "no risk",
            "confirmed safe",
            "system confirms safety",
            "nothing to worry about",
            "rest assured",
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
                    f"alert text contains forbidden privacy phrase "
                    f"{word!r} (privacy boundary; "
                    f"see docs/PHILOSOPHY.md)"
                )
        for word in _DIGNITY_FORBIDDEN:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden dignity-eroding "
                    f"word {word!r} (dignity boundary; "
                    f"see docs/PHILOSOPHY.md)"
                )
        for word in _LABOR_FORBIDDEN:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden labor-relations "
                    f"phrase {word!r} (labor-relations boundary; "
                    f"see docs/PHILOSOPHY.md)"
                )
        for word in _PANIC_FORBIDDEN:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden panic-inducing "
                    f"word {word!r} (panic-prevention boundary; "
                    f"see docs/PHILOSOPHY.md)"
                )
        for word in _FALSE_REASSURANCE_FORBIDDEN:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden false-reassurance "
                    f"phrase {word!r} (no-false-reassurance boundary; "
                    f"see docs/PHILOSOPHY.md)"
                )
        for prefix in _IDENTIFIER_PREFIXES:
            if prefix in low:
                raise ValueError(
                    f"alert text appears to identify the swimmer "
                    f"({prefix!r}; privacy boundary; "
                    f"see docs/PHILOSOPHY.md)"
                )


@dataclass
class PoolReport:
    """Aggregate across a set of swimmer observations."""

    pool_id: str
    scores: list[AquaticScore] = field(default_factory=list)
    alerts: list[LifeguardAlert] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.pool_id:
            raise ValueError("pool_id must not be empty")

    @property
    def observation_count(self) -> int:
        return len(self.scores)

    def alerts_at_level(self, level: AlertLevel) -> list[LifeguardAlert]:
        return [a for a in self.alerts if a.level == level]

    def alerts_of_kind(self, kind: AlertKind) -> list[LifeguardAlert]:
        return [a for a in self.alerts if a.kind == kind]

    def as_text(self) -> str:
        """Short human-readable summary.

        NB: the no-false-reassurance boundary means this
        function deliberately avoids "all clear" framing.
        A window with no alerts is described as "no
        drowning signature observed in this cycle", not
        "pool is safe".
        """
        lines = [
            f"Pool: {self.pool_id} · {self.observation_count} "
            f"swimmer observation"
            f"{'s' if self.observation_count != 1 else ''}",
        ]
        if self.alerts:
            kinds: tuple[AlertKind, ...] = (
                "submersion", "idr", "absent", "distress",
            )
            counts = {k: len(self.alerts_of_kind(k)) for k in kinds}
            lines.append(
                "  alerts by channel — "
                + "  ".join(f"{k}: {counts[k]}" for k in kinds)
            )
        urgent = self.alerts_at_level("urgent")
        watch = self.alerts_at_level("watch")
        if urgent:
            lines.append("URGENT alerts:")
            for a in urgent:
                lines.append(f"  - [{a.kind} / {a.swimmer_token}]: {a.text}")
        if watch:
            lines.append("WATCH alerts:")
            for a in watch:
                lines.append(f"  - [{a.kind} / {a.swimmer_token}]: {a.text}")
        if not urgent and not watch:
            # Intentionally observation-worded — never "all
            # safe" or "all clear".
            lines.append(
                "No drowning signatures observed in this cycle. "
                "Lifeguard attention remains required."
            )
        return "\n".join(lines)


__all__ = [
    "AquaticScore",
    "LifeguardAlert",
    "PoolReport",
    "SubmersionSample",
    "SurfacePoseSample",
    "SwimmerObservation",
    "SwimmerPresenceSample",
]
