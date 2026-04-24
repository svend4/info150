"""Core dataclasses for triage4-site.

Flat, frozen where sensible, no methods beyond validation +
``as_text`` on the aggregate. Copy-fork of the sibling shape.

Claims guard on ``SafetyOfficerAlert`` enforces FIVE
boundaries at construction time: clinical + operational +
privacy + dignity + **labor relations**. The labor-relations
list is the new boundary introduced by this sibling; see
docs/PHILOSOPHY.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import (
    AlertKind,
    AlertLevel,
    PPEItem,
    SiteCondition,
    VALID_ALERT_KINDS,
    VALID_ALERT_LEVELS,
    VALID_PPE_ITEMS,
    VALID_SITE_CONDITIONS,
)


# ---------------------------------------------------------------------------
# Raw observations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PPESample:
    """PPE-item classification for one worker at one instant.

    ``items_detected`` is the tuple of PPE items the upstream
    detector identified (e.g. ("hard_hat", "vest")). A required
    item missing from this set counts as non-compliance at
    this instant.
    """

    t_s: float
    items_detected: tuple[PPEItem, ...]

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        for item in self.items_detected:
            if item not in VALID_PPE_ITEMS:
                raise ValueError(
                    f"PPE item must be one of {VALID_PPE_ITEMS}, "
                    f"got {item!r}"
                )
        # No duplicate items in a single sample.
        if len(set(self.items_detected)) != len(self.items_detected):
            raise ValueError(
                f"duplicate PPE items in sample: {self.items_detected!r}"
            )


@dataclass(frozen=True)
class LiftingSample:
    """One lifting-motion snapshot.

    ``back_angle_deg`` is the back-hip flexion angle at the
    moment sampled (0 = upright, 90 = horizontal). Safe-lift
    literature caps acceptable flexion at ~30-45° at peak
    load; higher values are the unsafe-lift signal.
    ``load_kg`` is the estimated load weight (0 if empty-hand
    motion).
    """

    t_s: float
    back_angle_deg: float
    load_kg: float

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if not 0.0 <= self.back_angle_deg <= 180.0:
            raise ValueError(
                f"back_angle_deg must be in [0, 180], "
                f"got {self.back_angle_deg}"
            )
        if not 0.0 <= self.load_kg <= 500.0:
            raise ValueError(
                f"load_kg out of plausible range: {self.load_kg}"
            )


@dataclass(frozen=True)
class ThermalSample:
    """Skin-temperature + ambient-temperature snapshot.

    Both values in °C. The heat-stress signature reads the
    skin-ambient differential and absolute skin temperature
    combined with the recent-movement slowdown signal.
    """

    t_s: float
    skin_temp_c: float
    ambient_temp_c: float

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if not 20.0 <= self.skin_temp_c <= 45.0:
            raise ValueError(
                f"skin_temp_c out of plausible range: {self.skin_temp_c}"
            )
        if not -30.0 <= self.ambient_temp_c <= 55.0:
            raise ValueError(
                f"ambient_temp_c out of plausible range: "
                f"{self.ambient_temp_c}"
            )


@dataclass(frozen=True)
class FatigueGaitSample:
    """Walking-pace + limb-asymmetry snapshot.

    ``pace_mps`` is the estimated walking speed over a
    short window ending at ``t_s``; ``asymmetry`` is the
    left-right step-length mismatch in [0, 1] where 0 =
    symmetric.
    """

    t_s: float
    pace_mps: float
    asymmetry: float

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if not 0.0 <= self.pace_mps <= 5.0:
            raise ValueError(
                f"pace_mps out of plausible range: {self.pace_mps}"
            )
        if not 0.0 <= self.asymmetry <= 1.0:
            raise ValueError(
                f"asymmetry must be in [0, 1], got {self.asymmetry}"
            )


@dataclass
class WorkerObservation:
    """One shift-window observation of a single worker-token.

    ``worker_token`` is an opaque identifier from the site's
    RFID-badge layer. The library never correlates the token
    to a human identity — no cross-shift state persists at
    this layer. See docs/PHILOSOPHY.md on the labor-relations
    boundary.

    ``required_ppe`` is the set of PPE items required in the
    zone this worker is operating in. The sensor hub
    supplies the zone-to-PPE mapping upstream.
    """

    worker_token: str
    window_duration_s: float
    required_ppe: tuple[PPEItem, ...] = ()
    ppe_samples: list[PPESample] = field(default_factory=list)
    lifting_samples: list[LiftingSample] = field(default_factory=list)
    thermal_samples: list[ThermalSample] = field(default_factory=list)
    gait_samples: list[FatigueGaitSample] = field(default_factory=list)
    site_condition: SiteCondition = "clear"

    def __post_init__(self) -> None:
        if not self.worker_token:
            raise ValueError("worker_token must not be empty")
        if self.window_duration_s <= 0:
            raise ValueError(
                f"window_duration_s must be positive, "
                f"got {self.window_duration_s}"
            )
        for item in self.required_ppe:
            if item not in VALID_PPE_ITEMS:
                raise ValueError(
                    f"required_ppe item must be one of "
                    f"{VALID_PPE_ITEMS}, got {item!r}"
                )
        if self.site_condition not in VALID_SITE_CONDITIONS:
            raise ValueError(
                f"site_condition must be one of "
                f"{VALID_SITE_CONDITIONS}, got {self.site_condition!r}"
            )


# ---------------------------------------------------------------------------
# Engine output
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SafetyScore:
    """Per-observation safety summary.

    Channels in [0, 1], 1.0 = textbook-safe observation,
    0.0 = strong non-compliance / risk signal. ``overall``
    is a weighted combination. Zone-level (not
    worker-performance-level) metric by construction.
    """

    worker_token: str
    ppe_compliance: float
    lifting_safety: float
    heat_safety: float
    fatigue_safety: float
    overall: float
    alert_level: AlertLevel

    def __post_init__(self) -> None:
        for name, v in (
            ("ppe_compliance", self.ppe_compliance),
            ("lifting_safety", self.lifting_safety),
            ("heat_safety", self.heat_safety),
            ("fatigue_safety", self.fatigue_safety),
            ("overall", self.overall),
        ):
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {v}")
        if self.alert_level not in VALID_ALERT_LEVELS:
            raise ValueError(
                f"alert_level must be one of {VALID_ALERT_LEVELS}, "
                f"got {self.alert_level!r}"
            )


# Identifier-prefix guard — same common-name heuristic the
# prior siblings use, adapted for worker context.
_IDENTIFIER_PREFIXES: tuple[str, ...] = (
    "worker john",
    "worker jane",
    "worker mike",
    "worker maria",
    "worker sam",
    "worker alex",
    "worker chris",
    "worker james",
    "worker mary",
    "worker robert",
)


@dataclass(frozen=True)
class SafetyOfficerAlert:
    """A single alert surfaced to the site safety officer.

    Five-boundary claims guard enforced at construction time.
    See docs/PHILOSOPHY.md on each list.
    """

    worker_token: str
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
            "dehydrated",
            "heat stroke",
            "musculoskeletal injury",
            "back injury",
            "exhausted",
            "pronounced",
            "confirmed deceased",
        )
        _OPERATIONAL_FORBIDDEN = (
            "stop work",
            "shut down the site",
            "halt operations",
            "evacuate",
            "send worker home",
            "call 911",
            "dispatch ambulance",
            "call emergency services",
        )
        _PRIVACY_FORBIDDEN = (
            "same worker as",
            "previous worker",
            "identify the worker",
            "biometric match",
            "facial print",
        )
        _DIGNITY_FORBIDDEN = (
            "careless",
            "negligent",
            "lazy",
            "reckless",
            "incompetent",
            "unfit",
            "unprofessional",
        )
        _LABOR_FORBIDDEN = (
            "productivity",
            "efficiency metric",
            "performance metric",
            "performance review",
            "discipline",
            "reprimand",
            "write-up",
            "write up",
            "hr action",
            "hr notification",
            "termination",
            "fire the worker",
            "dismiss the worker",
            "performance improvement plan",
            " pip ",
            "withholding bonus",
            "incentive penalty",
            "schedule penalty",
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
        for prefix in _IDENTIFIER_PREFIXES:
            if prefix in low:
                raise ValueError(
                    f"alert text appears to identify the worker "
                    f"({prefix!r}; privacy boundary; "
                    f"see docs/PHILOSOPHY.md)"
                )


@dataclass
class SiteReport:
    """Aggregate across multiple worker-observation windows."""

    site_id: str
    scores: list[SafetyScore] = field(default_factory=list)
    alerts: list[SafetyOfficerAlert] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.site_id:
            raise ValueError("site_id must not be empty")

    @property
    def observation_count(self) -> int:
        return len(self.scores)

    def alerts_at_level(self, level: AlertLevel) -> list[SafetyOfficerAlert]:
        return [a for a in self.alerts if a.level == level]

    def alerts_of_kind(self, kind: AlertKind) -> list[SafetyOfficerAlert]:
        return [a for a in self.alerts if a.kind == kind]

    def as_text(self) -> str:
        """Short human-readable summary — for the demo + tests.

        Aggregates at the channel level, NOT per-worker —
        labor-relations boundary.
        """
        lines = [
            f"Site: {self.site_id} · {self.observation_count} "
            f"worker observation"
            f"{'s' if self.observation_count != 1 else ''}",
        ]
        urgent = self.alerts_at_level("urgent")
        watch = self.alerts_at_level("watch")
        # Channel counts summary.
        if self.alerts:
            kinds = ("ppe", "lifting", "heat", "fatigue")
            counts = {k: len(self.alerts_of_kind(k)) for k in kinds}
            lines.append(
                "  alerts by channel — "
                + "  ".join(f"{k}: {counts[k]}" for k in kinds)
            )
        if urgent:
            lines.append("URGENT alerts:")
            for a in urgent:
                lines.append(f"  - [{a.kind}]: {a.text}")
        if watch:
            lines.append("WATCH alerts:")
            for a in watch:
                lines.append(f"  - [{a.kind}]: {a.text}")
        if not urgent and not watch:
            lines.append("No watch / urgent alerts surfaced.")
        return "\n".join(lines)


__all__ = [
    "FatigueGaitSample",
    "LiftingSample",
    "PPESample",
    "SafetyOfficerAlert",
    "SafetyScore",
    "SiteReport",
    "ThermalSample",
    "WorkerObservation",
]
