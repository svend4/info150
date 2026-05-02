"""Core dataclasses for triage4-coast.

A coast deployment is a strip of camera-monitored zones (beach,
promenade, water swim-zone, pier). The engine consumes one
``CoastZoneObservation`` per zone and produces a ``CoastScore``
plus zero or more ``CoastOpsAlert`` records, then aggregates into
a ``CoastReport``.

Operational posture: alerts are decision-support for lifeguards
and city operations. They never name a medical condition. They
DESCRIBE what was observed and SUGGEST a check.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import (
    AlertKind,
    AlertLevel,
    VALID_ALERT_KINDS,
    VALID_ALERT_LEVELS,
    VALID_ZONE_KINDS,
    ZoneKind,
)


# ---------------------------------------------------------------------------
# Raw observation (per zone)
# ---------------------------------------------------------------------------


@dataclass
class CoastZoneObservation:
    """One sensor window for one coastal zone.

    Channel inputs are normalised scalars from camera + manual
    operator slider. The engine combines them into a CoastScore.
    """

    zone_id: str
    zone_kind: ZoneKind
    window_duration_s: float
    # Camera-motion / variance proxy → crowd density on the strip.
    density_pressure: float
    # Camera-motion limited to the water region OR operator slider.
    in_water_motion: float
    # Camera-luminance proxy → sun intensity.
    sun_intensity: float
    # Operator-set or future detector — child without companion.
    lost_child_flag: bool = False

    def __post_init__(self) -> None:
        if not self.zone_id:
            raise ValueError("zone_id must not be empty")
        if self.zone_kind not in VALID_ZONE_KINDS:
            raise ValueError(
                f"zone_kind must be one of {VALID_ZONE_KINDS}, "
                f"got {self.zone_kind!r}"
            )
        if self.window_duration_s <= 0:
            raise ValueError(
                f"window_duration_s must be positive, got {self.window_duration_s}"
            )
        for name, val in (
            ("density_pressure", self.density_pressure),
            ("in_water_motion", self.in_water_motion),
            ("sun_intensity", self.sun_intensity),
        ):
            if not 0.0 <= val <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {val}")


# ---------------------------------------------------------------------------
# Engine output
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CoastScore:
    """Per-zone score the engine produces.

    Channel safety scores are 1.0 = safe, 0.0 = unsafe.
    """

    zone_id: str
    zone_kind: ZoneKind
    alert_level: AlertLevel
    density_safety: float
    drowning_safety: float
    sun_safety: float
    lost_child_safety: float
    overall: float

    def __post_init__(self) -> None:
        if self.alert_level not in VALID_ALERT_LEVELS:
            raise ValueError(
                f"alert_level must be one of {VALID_ALERT_LEVELS}, "
                f"got {self.alert_level!r}"
            )
        for name, v in (
            ("density_safety", self.density_safety),
            ("drowning_safety", self.drowning_safety),
            ("sun_safety", self.sun_safety),
            ("lost_child_safety", self.lost_child_safety),
            ("overall", self.overall),
        ):
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {v}")


_FORBIDDEN_TEXT = (
    "injured", "diagnose", "treat ", "dangerous", "medical",
)


@dataclass(frozen=True)
class CoastOpsAlert:
    """One alert surfaced to the lifeguard / operator."""

    zone_id: str
    kind: AlertKind
    level: AlertLevel
    text: str

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
        for word in _FORBIDDEN_TEXT:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden word {word!r} "
                    "(operational posture)"
                )


@dataclass
class CoastReport:
    """Aggregate report — one per coast deployment."""

    coast_id: str
    scores: list[CoastScore] = field(default_factory=list)
    alerts: list[CoastOpsAlert] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.coast_id:
            raise ValueError("coast_id must not be empty")

    def alerts_at_level(self, level: AlertLevel) -> list[CoastOpsAlert]:
        return [a for a in self.alerts if a.level == level]

    def as_text(self) -> str:
        lines: list[str] = []
        lines.append(
            f"Coast {self.coast_id} · {len(self.scores)} zones · "
            f"{len(self.alerts)} alerts"
        )
        for s in self.scores:
            lines.append(
                f"  {s.zone_id:<20s} "
                f"level={s.alert_level:7s} overall={s.overall:.2f}"
            )
        for a in self.alerts:
            lines.append(f"    [{a.level}] [{a.kind}] {a.zone_id}: {a.text}")
        return "\n".join(lines)


__all__ = [
    "CoastOpsAlert",
    "CoastReport",
    "CoastScore",
    "CoastZoneObservation",
]
