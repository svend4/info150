"""Core dataclasses for triage4-crowd.

Subject is **aggregate** — zones, not individuals. There is
no worker/resident/driver/casualty token in the data model;
the primary identifier is ``zone_id``. ``MedicalCandidate``
carries a short opaque ``candidate_id`` scoped to the single
observation window, which never leaves the library as an
identity record.

Claims guard on ``VenueOpsAlert`` enforces SIX boundaries at
construction time: clinical + operational + privacy +
dignity + labor-relations + **panic-prevention**. The last
list is new in this sibling. See docs/PHILOSOPHY.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import (
    AlertKind,
    AlertLevel,
    CrowdDirection,
    VALID_ALERT_KINDS,
    VALID_ALERT_LEVELS,
    VALID_CROWD_DIRECTIONS,
    VALID_ZONE_KINDS,
    ZoneKind,
)


# ---------------------------------------------------------------------------
# Raw aggregate observations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DensityReading:
    """Zone density estimate at one instant.

    ``persons_per_m2`` is the mean density estimated by the
    upstream crowd counter over the zone's accessible
    floor area at ``t_s``. Helbing / Fruin bands cap
    comfortable standing at ~2 p/m², dense at ~4, and
    identify critical conditions above ~5.
    """

    t_s: float
    persons_per_m2: float

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if not 0.0 <= self.persons_per_m2 <= 12.0:
            raise ValueError(
                f"persons_per_m2 out of plausible range: "
                f"{self.persons_per_m2}"
            )


@dataclass(frozen=True)
class FlowSample:
    """Zone-flow snapshot.

    ``net_direction`` summarises the flow field; ``magnitude``
    in [0, 1] expresses how pronounced the net direction is
    vs. an even distribution. ``compaction`` in [0, 1] is the
    concentration of net inflow into a choke point — the
    classic crush precursor when combined with high density.
    """

    t_s: float
    net_direction: CrowdDirection
    magnitude: float
    compaction: float

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if self.net_direction not in VALID_CROWD_DIRECTIONS:
            raise ValueError(
                f"net_direction must be one of "
                f"{VALID_CROWD_DIRECTIONS}, got {self.net_direction!r}"
            )
        for name, v in (
            ("magnitude", self.magnitude),
            ("compaction", self.compaction),
        ):
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {v}")


@dataclass(frozen=True)
class PressureReading:
    """Crowd-pressure RMS reading at one instant.

    ``pressure_rms`` is a dimensionless proxy in [0, 1]. The
    upstream signal is typically built from inter-person
    acceleration + jerk estimates integrated across the
    zone, matching Helbing's 2007 "crowd pressure" concept.
    Non-zero but low values are normal; sustained elevation
    is the strongest crush-precursor signal the library
    reads.
    """

    t_s: float
    pressure_rms: float

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if not 0.0 <= self.pressure_rms <= 1.0:
            raise ValueError(
                f"pressure_rms must be in [0, 1], got {self.pressure_rms}"
            )


@dataclass(frozen=True)
class MedicalCandidate:
    """Anonymous collapsed-person candidate in a zone.

    The ``candidate_id`` is an opaque token scoped to one
    observation window. It never leaves the library as an
    identity record — no face prints, no body attributes,
    no cross-window correlation. Consumer apps may attach
    dispatch tracking downstream with their own consent +
    retention policy.
    """

    candidate_id: str
    t_s: float
    confidence: float

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise ValueError("candidate_id must not be empty")
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence must be in [0, 1], got {self.confidence}"
            )


@dataclass
class ZoneObservation:
    """One zone's aggregate-state observation for a window.

    Aggregate by design — no individual tracking at this
    layer.
    """

    zone_id: str
    zone_kind: ZoneKind
    window_duration_s: float
    density_readings: list[DensityReading] = field(default_factory=list)
    flow_samples: list[FlowSample] = field(default_factory=list)
    pressure_readings: list[PressureReading] = field(default_factory=list)
    medical_candidates: list[MedicalCandidate] = field(default_factory=list)

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
                f"window_duration_s must be positive, "
                f"got {self.window_duration_s}"
            )


# ---------------------------------------------------------------------------
# Engine output
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CrowdScore:
    """Per-zone safety summary.

    Channels in [0, 1]: 1.0 = textbook-safe crowd state,
    0.0 = strong safety signal. ``overall`` is the fused
    weighted combination. Zone-level, never per-person.
    """

    zone_id: str
    density_safety: float
    flow_safety: float
    pressure_safety: float
    medical_safety: float
    overall: float
    alert_level: AlertLevel

    def __post_init__(self) -> None:
        for name, v in (
            ("density_safety", self.density_safety),
            ("flow_safety", self.flow_safety),
            ("pressure_safety", self.pressure_safety),
            ("medical_safety", self.medical_safety),
            ("overall", self.overall),
        ):
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {v}")
        if self.alert_level not in VALID_ALERT_LEVELS:
            raise ValueError(
                f"alert_level must be one of {VALID_ALERT_LEVELS}, "
                f"got {self.alert_level!r}"
            )


@dataclass(frozen=True)
class VenueOpsAlert:
    """Venue-ops facing alert.

    Six-boundary claims guard at construction. See
    docs/PHILOSOPHY.md — especially the panic-prevention
    list, which is new in this sibling and which rejects
    the dramatic vocabulary that amplifies incidents when
    relayed through venue radios / PA.
    """

    zone_id: str
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
            "seizure",
            "heart attack",
            "stroke",
            "overdose",
            "pronounced",
            "confirmed deceased",
        )
        _OPERATIONAL_FORBIDDEN = (
            "close gate",
            "close the gate",
            "stop entry",
            "evacuate",
            "evacuation",
            "activate the pa",
            "announce over pa",
            "disperse the crowd",
            "remove the attendee",
            "call 911",
            "dispatch ambulance",
        )
        _PRIVACY_FORBIDDEN = (
            "person in red",
            "person wearing",
            "same attendee as",
            "identify the attendee",
            "biometric match",
            "facial print",
            "face recognition",
        )
        _DIGNITY_FORBIDDEN = (
            "drunk attendee",
            "intoxicated attendee",
            "rowdy attendee",
            "belligerent attendee",
        )
        _LABOR_FORBIDDEN = (
            "security-guard performance",
            "guard performance metric",
            "discipline the guard",
            "guard write-up",
            "guard reprimand",
        )
        _PANIC_FORBIDDEN = (
            "stampede",
            "crush in progress",
            "crush forming",
            "disaster",
            "catastrophe",
            "catastrophic",
            "fatality",
            "fatalities",
            "panic",
            "mass casualty",
            "mass-casualty",
            "immediate danger",
            "imminent danger",
            "lethal",
            "deadly",
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


@dataclass
class VenueReport:
    """Aggregate across a set of zones for one observation pass."""

    venue_id: str
    scores: list[CrowdScore] = field(default_factory=list)
    alerts: list[VenueOpsAlert] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.venue_id:
            raise ValueError("venue_id must not be empty")

    @property
    def zone_count(self) -> int:
        return len(self.scores)

    def alerts_at_level(self, level: AlertLevel) -> list[VenueOpsAlert]:
        return [a for a in self.alerts if a.level == level]

    def alerts_of_kind(self, kind: AlertKind) -> list[VenueOpsAlert]:
        return [a for a in self.alerts if a.kind == kind]

    def as_text(self) -> str:
        """Short human-readable summary. Zone-level only."""
        lines = [
            f"Venue: {self.venue_id} · {self.zone_count} zone"
            f"{'s' if self.zone_count != 1 else ''} observed",
        ]
        if self.alerts:
            kinds: tuple[AlertKind, ...] = (
                "density", "flow", "pressure", "medical",
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
                lines.append(f"  - [{a.kind} / {a.zone_id}]: {a.text}")
        if watch:
            lines.append("WATCH alerts:")
            for a in watch:
                lines.append(f"  - [{a.kind} / {a.zone_id}]: {a.text}")
        if not urgent and not watch:
            lines.append("No watch / urgent alerts surfaced.")
        return "\n".join(lines)


__all__ = [
    "CrowdScore",
    "DensityReading",
    "FlowSample",
    "MedicalCandidate",
    "PressureReading",
    "VenueOpsAlert",
    "VenueReport",
    "ZoneObservation",
]
