"""Core dataclasses for triage4-wild.

Flat + frozen + validation-only. Three new architectural
features in this sibling:

- ``LocationHandle`` — opaque token only; plaintext
  decimal-degree coordinates are never accepted into the
  data model.
- ``RangerAlert`` — enforces three new boundaries
  (field-security, poaching-prediction overreach,
  ecosystem-prediction overreach) + an SMS-length
  structural cap.
- Species-specific upstream ``ThreatKind`` confidences
  flow in on ``WildlifeObservation`` and drive the
  engine's escalation logic without ever becoming
  "this animal has a wire-snare injury" — observations
  only.

See docs/PHILOSOPHY.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .enums import (
    AlertKind,
    AlertLevel,
    CaptureQuality,
    MAX_RANGER_SMS_CHARS,
    Species,
    ThreatKind,
    VALID_ALERT_KINDS,
    VALID_ALERT_LEVELS,
    VALID_CAPTURE_QUALITIES,
    VALID_SPECIES,
    VALID_THREAT_KINDS,
)


# ---------------------------------------------------------------------------
# LocationHandle — opaque; NEVER plaintext coordinates
# ---------------------------------------------------------------------------


# Heuristic for obvious decimal-degree content that a
# caller might accidentally put into a location handle.
# Matches two float numbers with 2+ decimal digits
# separated by a comma or whitespace, which covers both
# "1.234, 5.678" and "1.234 5.678" coordinate formats.
_DECIMAL_PAIR_RE = re.compile(
    r"[-+]?\d+\.\d{2,}\s*[,\s]\s*[-+]?\d+\.\d{2,}"
)


@dataclass(frozen=True)
class LocationHandle:
    """Opaque location token — grid cell or reserve zone.

    The library REFUSES to accept plaintext decimal-degree
    coordinates in the ``handle`` string. Upstream consumers
    obfuscate GPS telemetry (grid-cell binning, zone
    labels) before passing an observation in. See the
    field-security boundary in docs/PHILOSOPHY.md.
    """

    handle: str

    def __post_init__(self) -> None:
        if not self.handle.strip():
            raise ValueError("LocationHandle.handle must not be empty")
        if _DECIMAL_PAIR_RE.search(self.handle):
            raise ValueError(
                "LocationHandle.handle appears to contain decimal-"
                "degree coordinates — the library only accepts "
                "opaque grid-cell or zone tokens upstream. See "
                "field-security boundary in docs/PHILOSOPHY.md."
            )


# ---------------------------------------------------------------------------
# Raw samples
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QuadrupedPoseSample:
    """Per-frame limb pose for a quadruped.

    ``limb_asymmetry`` in [0, 1] is the maximum asymmetry
    across the four paired limb joints for this frame.
    ``body_upright`` in [0, 1] is a proxy for whether the
    animal is in a non-collapsed posture.
    """

    t_s: float
    limb_asymmetry: float
    body_upright: float

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        for name, v in (
            ("limb_asymmetry", self.limb_asymmetry),
            ("body_upright", self.body_upright),
        ):
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {v}")


@dataclass(frozen=True)
class ThermalSample:
    """Thermal-camera hotspot reading — in [0, 1] proxy.

    1.0 = clear focal hotspot relative to body baseline.
    0.0 = no hotspot above ambient. Upstream normalises.
    """

    t_s: float
    hotspot: float

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if not 0.0 <= self.hotspot <= 1.0:
            raise ValueError(
                f"hotspot must be in [0, 1], got {self.hotspot}"
            )


@dataclass(frozen=True)
class GaitSample:
    """Pace + cadence snapshot for a quadruped."""

    t_s: float
    pace_mps: float
    cadence_steadiness: float   # [0, 1], 1 = steady rhythm

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if not 0.0 <= self.pace_mps <= 20.0:
            raise ValueError(
                f"pace_mps out of plausible range: {self.pace_mps}"
            )
        if not 0.0 <= self.cadence_steadiness <= 1.0:
            raise ValueError(
                f"cadence_steadiness must be in [0, 1], "
                f"got {self.cadence_steadiness}"
            )


@dataclass(frozen=True)
class BodyConditionSample:
    """Body-condition estimate — emaciation indicator.

    ``condition_score`` in [0, 1], 1.0 = healthy body
    condition, 0.0 = clearly emaciated. Derived upstream
    from frame-geometry proxies (rib prominence, flank
    hollow, spine visibility).
    """

    t_s: float
    condition_score: float

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if not 0.0 <= self.condition_score <= 1.0:
            raise ValueError(
                f"condition_score must be in [0, 1], "
                f"got {self.condition_score}"
            )


@dataclass(frozen=True)
class ThreatConfidence:
    """One upstream red-flag classifier output.

    An upstream vision model may detect specific threat
    patterns (wire-snare on a limb; tusk / horn
    asymmetry). The library consumes the confidence value
    here; it never performs its own threat classification.
    """

    kind: ThreatKind
    confidence: float

    def __post_init__(self) -> None:
        if self.kind not in VALID_THREAT_KINDS:
            raise ValueError(
                f"kind must be one of {VALID_THREAT_KINDS}, "
                f"got {self.kind!r}"
            )
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence must be in [0, 1], got {self.confidence}"
            )


@dataclass
class WildlifeObservation:
    """One camera-trap / drone pass observation.

    ``obs_token`` is an opaque identifier from the
    sensor-hub layer — NOT a collar ID, NOT identity
    across passes. Cross-pass identity tracking would
    create the anti-poaching leakage risk the field-
    security boundary prevents.
    """

    obs_token: str
    species: Species
    species_confidence: float
    window_duration_s: float
    location: LocationHandle
    capture_quality: CaptureQuality = "good"
    pose_samples: list[QuadrupedPoseSample] = field(default_factory=list)
    thermal_samples: list[ThermalSample] = field(default_factory=list)
    gait_samples: list[GaitSample] = field(default_factory=list)
    body_condition_samples: list[BodyConditionSample] = \
        field(default_factory=list)
    threat_signals: list[ThreatConfidence] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.obs_token:
            raise ValueError("obs_token must not be empty")
        if self.species not in VALID_SPECIES:
            raise ValueError(
                f"species must be one of {VALID_SPECIES}, "
                f"got {self.species!r}"
            )
        if not 0.0 <= self.species_confidence <= 1.0:
            raise ValueError(
                f"species_confidence must be in [0, 1], "
                f"got {self.species_confidence}"
            )
        if self.window_duration_s <= 0 or self.window_duration_s > 3600:
            raise ValueError(
                f"window_duration_s must be in (0, 3600], "
                f"got {self.window_duration_s}"
            )
        if self.capture_quality not in VALID_CAPTURE_QUALITIES:
            raise ValueError(
                f"capture_quality must be one of "
                f"{VALID_CAPTURE_QUALITIES}, got {self.capture_quality!r}"
            )


# ---------------------------------------------------------------------------
# Engine output
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WildlifeHealthScore:
    """Per-observation wildlife-health summary.

    All four channels in [0, 1], 1.0 = healthy-looking
    observation, 0.0 = strong concern. ``overall`` is the
    fused weighted combination. ``threat_signal`` is a
    separate channel — it captures upstream visual-red-flag
    classifier outputs (snare, tusk, horn).
    """

    obs_token: str
    gait_safety: float
    thermal_safety: float
    postural_safety: float
    body_condition_safety: float
    threat_signal: float  # 1.0 = no threat flags, 0.0 = strong threat
    overall: float
    alert_level: AlertLevel

    def __post_init__(self) -> None:
        for name, v in (
            ("gait_safety", self.gait_safety),
            ("thermal_safety", self.thermal_safety),
            ("postural_safety", self.postural_safety),
            ("body_condition_safety", self.body_condition_safety),
            ("threat_signal", self.threat_signal),
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
class RangerAlert:
    """Ranger-facing alert — SMS-length + multi-boundary guarded.

    Three new boundaries enforced at construction:

    - **Field-security**: no lat/lon vocabulary, no
      decimal-degree patterns, no "gps coordinates" /
      "located at" phrases.
    - **Poaching-prediction overreach**: no "predict
      poacher", "optimise patrol", "anti-poaching
      operation" vocabulary.
    - **Ecosystem-prediction overreach**: no "population
      trajectory", "predict extinction", "conservation
      outcome" vocabulary.

    Plus standard clinical / operational / reassurance /
    panic-prevention guards, and a **hard length cap** at
    ``MAX_RANGER_SMS_CHARS`` — the library refuses to emit
    text that won't fit an SMS frame.

    See docs/PHILOSOPHY.md.
    """

    obs_token: str
    kind: AlertKind
    level: AlertLevel
    text: str
    location_handle: str   # opaque token, not plaintext coords
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
        if len(self.text) > MAX_RANGER_SMS_CHARS:
            raise ValueError(
                f"alert text exceeds SMS cap of "
                f"{MAX_RANGER_SMS_CHARS} chars "
                f"(got {len(self.text)}); see "
                f"docs/PHILOSOPHY.md on the SMS-length "
                f"structural constraint"
            )
        if not self.location_handle.strip():
            raise ValueError("location_handle must not be empty")
        if _DECIMAL_PAIR_RE.search(self.location_handle):
            raise ValueError(
                "location_handle contains decimal-degree "
                "coordinates — field-security boundary; see "
                "docs/PHILOSOPHY.md"
            )

        low = self.text.lower()

        # Also reject coordinate-decimal patterns in the
        # body text itself. An alert text that embeds
        # "1.234, 5.678" leaks coordinates even if the
        # location_handle is obfuscated.
        if _DECIMAL_PAIR_RE.search(self.text):
            raise ValueError(
                "alert text appears to contain decimal-"
                "degree coordinates — field-security "
                "boundary; see docs/PHILOSOPHY.md"
            )

        _FIELD_SECURITY_FORBIDDEN = (
            "latitude",
            "longitude",
            "lat:",
            "lng:",
            "lon:",
            "gps coordinates",
            "coordinates:",
            "located at",
        )
        _POACHING_OVERREACH = (
            "predict poacher",
            "predict poaching",
            "likely poacher",
            "suspect poacher",
            "identify poacher",
            "optimise patrol",
            "optimize patrol",
            "schedule patrol route",
            "patrol route recommendation",
            "anti-poaching operation",
        )
        _ECOSYSTEM_OVERREACH = (
            "population trajectory",
            "predict extinction",
            "extinction risk",
            "species will",
            "conservation outcome",
            "conservation outcome prediction",
        )
        _CLINICAL_FORBIDDEN = (
            "is injured",
            "has a wound",
            "confirms",
            "diagnosis",
            "is in shock",
            "is suffering",
        )
        _OPERATIONAL_FORBIDDEN = (
            "intercept",
            "deploy patrol",
            "dispatch rangers",
            "apprehend",
            "detain",
        )
        _REASSURANCE_FORBIDDEN = (
            "herd is safe",
            "no threats detected",
            "all clear",
        )
        _PANIC_FORBIDDEN = (
            "tragedy",
            "catastrophe",
            "fatalities",
        )

        for word in _FIELD_SECURITY_FORBIDDEN:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden field-"
                    f"security vocabulary {word!r} — the library "
                    f"never leaks location. See "
                    f"docs/PHILOSOPHY.md."
                )
        for word in _POACHING_OVERREACH:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden poaching-"
                    f"prediction-overreach phrase {word!r}; see "
                    f"docs/PHILOSOPHY.md"
                )
        for word in _ECOSYSTEM_OVERREACH:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden ecosystem-"
                    f"prediction-overreach phrase {word!r}; see "
                    f"docs/PHILOSOPHY.md"
                )
        for word in _CLINICAL_FORBIDDEN:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden clinical "
                    f"phrase {word!r}; see docs/PHILOSOPHY.md"
                )
        for word in _OPERATIONAL_FORBIDDEN:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden operational-"
                    f"command phrase {word!r}; see "
                    f"docs/PHILOSOPHY.md"
                )
        for word in _REASSURANCE_FORBIDDEN:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden reassurance "
                    f"phrase {word!r}; see docs/PHILOSOPHY.md"
                )
        for word in _PANIC_FORBIDDEN:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden panic-"
                    f"inducing phrase {word!r}; see "
                    f"docs/PHILOSOPHY.md"
                )


@dataclass
class ReserveReport:
    """Aggregate across a pass of observations.

    Reserve-level aggregates are deliberately zone-level,
    never individual-animal-level across passes — same
    field-security rationale: cross-pass identity tracking
    enables the poaching-leakage risk the library is
    designed to prevent.
    """

    reserve_id: str
    scores: list[WildlifeHealthScore] = field(default_factory=list)
    alerts: list[RangerAlert] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.reserve_id:
            raise ValueError("reserve_id must not be empty")

    @property
    def observation_count(self) -> int:
        return len(self.scores)

    def alerts_at_level(self, level: AlertLevel) -> list[RangerAlert]:
        return [a for a in self.alerts if a.level == level]

    def alerts_of_kind(self, kind: AlertKind) -> list[RangerAlert]:
        return [a for a in self.alerts if a.kind == kind]

    def as_text(self) -> str:
        """Short human-readable summary — for the demo."""
        lines = [
            f"Reserve: {self.reserve_id} · {self.observation_count} "
            f"observation"
            f"{'s' if self.observation_count != 1 else ''}",
        ]
        if self.alerts:
            kinds: tuple[AlertKind, ...] = (
                "gait", "thermal", "collapse", "body_condition",
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
                lines.append(
                    f"  - [{a.kind} / handle={a.location_handle}] {a.text}"
                )
        if watch:
            lines.append("WATCH alerts:")
            for a in watch:
                lines.append(
                    f"  - [{a.kind} / handle={a.location_handle}] {a.text}"
                )
        if not urgent and not watch:
            # Deliberately observation-worded, NEVER "all
            # clear" — ranger attention remains required.
            lines.append(
                "No concerning signals on this pass. Ranger "
                "attention remains required across the reserve."
            )
        return "\n".join(lines)


__all__ = [
    "BodyConditionSample",
    "GaitSample",
    "LocationHandle",
    "QuadrupedPoseSample",
    "RangerAlert",
    "ReserveReport",
    "ThermalSample",
    "ThreatConfidence",
    "WildlifeHealthScore",
    "WildlifeObservation",
]
