"""Core dataclasses for triage4-bird.

Architectural posture summary:

- ``CallSample`` carries already-classified call
  metadata only. The data model has NO field for raw
  audio / waveforms. Voice-content removal is therefore
  an upstream responsibility — by construction, the
  library cannot accidentally process or echo voice.
- ``OrnithologistAlert`` enforces three boundary lists
  novel to this sibling (or significantly tightened
  from prior siblings):
  * Surveillance-overreach (no avian-flu / HPAI /
    outbreak diagnosis).
  * Audio-privacy (no voice-quoting vocabulary in
    alert text).
  * Field-security (inherited from triage4-wild —
    no decimal-degree coordinate patterns or lat /
    lon vocabulary in alert text).

See docs/PHILOSOPHY.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .enums import (
    AlertKind,
    AlertLevel,
    CallKind,
    MAX_AVIAN_SMS_CHARS,
    Species,
    VALID_ALERT_KINDS,
    VALID_ALERT_LEVELS,
    VALID_CALL_KINDS,
    VALID_SPECIES,
)


# Decimal-coordinate-pair regex — same shape as triage4-wild.
_DECIMAL_PAIR_RE = re.compile(
    r"[-+]?\d+\.\d{2,}\s*[,\s]\s*[-+]?\d+\.\d{2,}"
)


# ---------------------------------------------------------------------------
# Already-classified samples — never raw audio
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CallSample:
    """One already-classified bird call.

    The data model carries no audio payload. Upstream
    BirdNET-class classifier produces ``species`` +
    ``confidence`` + ``kind``; the library consumes those
    outputs and never sees waveforms.
    """

    t_s: float
    species: Species
    kind: CallKind
    confidence: float

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if self.species not in VALID_SPECIES:
            raise ValueError(
                f"species must be one of {VALID_SPECIES}, "
                f"got {self.species!r}"
            )
        if self.kind not in VALID_CALL_KINDS:
            raise ValueError(
                f"kind must be one of {VALID_CALL_KINDS}, "
                f"got {self.kind!r}"
            )
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence must be in [0, 1], got {self.confidence}"
            )


@dataclass(frozen=True)
class WingbeatSample:
    """Visual wing-beat frequency snapshot for a perched /
    slow-flying bird. ``frequency_hz`` is the upstream
    estimate; ``reliable`` indicates the visual signal
    passed a quality threshold (the bird was still enough,
    light was good)."""

    t_s: float
    frequency_hz: float
    reliable: bool

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if not 0.0 <= self.frequency_hz <= 100.0:
            raise ValueError(
                f"frequency_hz out of plausible range: {self.frequency_hz}"
            )


@dataclass(frozen=True)
class BodyThermalSample:
    """Body-temp anomaly proxy in [0, 1]. 0.0 = normal,
    1.0 = strong elevated reading vs. species baseline.
    Avian-flu surveillance flag input — reported here as
    an OBSERVATION, never as a clinical conclusion.
    """

    t_s: float
    elevation: float

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if not 0.0 <= self.elevation <= 1.0:
            raise ValueError(
                f"elevation must be in [0, 1], got {self.elevation}"
            )


@dataclass(frozen=True)
class DeadBirdCandidate:
    """One visual ground-immobile bird flag from upstream."""

    t_s: float
    confidence: float

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence must be in [0, 1], got {self.confidence}"
            )


@dataclass
class BirdObservation:
    """One station-window observation pass.

    ``location_handle`` is opaque (grid cell or station
    label). The library never accepts plaintext decimal
    coordinates here — the constructor refuses obvious
    coordinate patterns.
    """

    obs_token: str
    station_id: str
    location_handle: str
    window_duration_s: float
    expected_species: tuple[Species, ...] = ()
    call_samples: list[CallSample] = field(default_factory=list)
    wingbeat_samples: list[WingbeatSample] = field(default_factory=list)
    thermal_samples: list[BodyThermalSample] = field(default_factory=list)
    dead_bird_candidates: list[DeadBirdCandidate] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.obs_token:
            raise ValueError("obs_token must not be empty")
        if not self.station_id:
            raise ValueError("station_id must not be empty")
        if not self.location_handle.strip():
            raise ValueError("location_handle must not be empty")
        if _DECIMAL_PAIR_RE.search(self.location_handle):
            raise ValueError(
                "location_handle appears to contain decimal-degree "
                "coordinates — the library accepts opaque grid / "
                "station tokens only. See field-security boundary "
                "in docs/PHILOSOPHY.md."
            )
        if self.window_duration_s <= 0 or self.window_duration_s > 7200:
            raise ValueError(
                f"window_duration_s must be in (0, 7200], "
                f"got {self.window_duration_s}"
            )
        for s in self.expected_species:
            if s not in VALID_SPECIES:
                raise ValueError(
                    f"expected_species entry must be one of "
                    f"{VALID_SPECIES}, got {s!r}"
                )


# ---------------------------------------------------------------------------
# Engine output
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AvianHealthScore:
    """Per-observation summary, unit-interval channels."""

    obs_token: str
    call_presence_safety: float
    distress_safety: float
    vitals_safety: float
    thermal_safety: float
    mortality_cluster_safety: float
    overall: float
    alert_level: AlertLevel

    def __post_init__(self) -> None:
        for name, v in (
            ("call_presence_safety", self.call_presence_safety),
            ("distress_safety", self.distress_safety),
            ("vitals_safety", self.vitals_safety),
            ("thermal_safety", self.thermal_safety),
            ("mortality_cluster_safety", self.mortality_cluster_safety),
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
class OrnithologistAlert:
    """Ornithologist / sampling-coordinator facing alert.

    Multi-list claims guard:

    - Surveillance-overreach (NEW): no avian-flu / HPAI /
      outbreak / pandemic vocabulary. Output is
      "candidate mortality cluster" framing only.
    - Audio-privacy (NEW): no voice-quoting vocabulary
      in alert text.
    - Field-security (from triage4-wild): no decimal-
      degree patterns + no lat / lon / coordinates
      vocabulary.
    - Clinical: no definitive-diagnosis language.
    - Operational: no sampling-team command vocabulary.
    - Reassurance / panic-prevention: light versions.
    - Hard SMS-length cap at MAX_AVIAN_SMS_CHARS.

    See docs/PHILOSOPHY.md.
    """

    obs_token: str
    kind: AlertKind
    level: AlertLevel
    text: str
    location_handle: str
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
        if len(self.text) > MAX_AVIAN_SMS_CHARS:
            raise ValueError(
                f"alert text exceeds SMS cap of "
                f"{MAX_AVIAN_SMS_CHARS} chars (got {len(self.text)})"
            )
        if not self.location_handle.strip():
            raise ValueError("location_handle must not be empty")
        if _DECIMAL_PAIR_RE.search(self.location_handle):
            raise ValueError(
                "location_handle contains decimal-degree "
                "coordinates — field-security boundary"
            )
        if _DECIMAL_PAIR_RE.search(self.text):
            raise ValueError(
                "alert text contains decimal-degree "
                "coordinates — field-security boundary"
            )

        low = self.text.lower()

        _SURVEILLANCE_OVERREACH = (
            "detects avian flu",
            "detects hpai",
            "diagnoses avian flu",
            "diagnoses hpai",
            "confirms outbreak",
            "predicts outbreak",
            "flu strain identified",
            "epidemic detected",
            "pandemic",
            "h5n1",
            "h7n9",
            "h5n8",
        )
        _AUDIO_PRIVACY_FORBIDDEN = (
            "person said",
            "someone said",
            "voice content",
            "conversation captured",
            "human speech",
            "audio of speaker",
            "quoted speech",
            "transcribed audio",
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
        _CLINICAL_FORBIDDEN = (
            "is sick",
            "has rabies",
            "has hpai",
            "is infected",
            "confirms",
            "diagnosis",
        )
        _OPERATIONAL_FORBIDDEN = (
            "cull birds",
            "destroy nest",
            "remove carcass",
            "dispatch sampler",
            "deploy sampling team",
        )
        _REASSURANCE_FORBIDDEN = (
            "no flu",
            "all clear",
            "no concerns",
        )
        _PANIC_FORBIDDEN = (
            "tragedy",
            "catastrophe",
            "disaster",
        )

        for word in _SURVEILLANCE_OVERREACH:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden surveillance-"
                    f"overreach phrase {word!r} — flu / HPAI / "
                    f"outbreak diagnosis is a public-health claim "
                    f"the library cannot make. See "
                    f"docs/PHILOSOPHY.md."
                )
        for word in _AUDIO_PRIVACY_FORBIDDEN:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden audio-privacy "
                    f"phrase {word!r} — the library never echoes "
                    f"recorded voice content. See "
                    f"docs/PHILOSOPHY.md."
                )
        for word in _FIELD_SECURITY_FORBIDDEN:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden field-security "
                    f"phrase {word!r}"
                )
        for word in _CLINICAL_FORBIDDEN:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden clinical "
                    f"phrase {word!r}"
                )
        for word in _OPERATIONAL_FORBIDDEN:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden operational "
                    f"phrase {word!r}"
                )
        for word in _REASSURANCE_FORBIDDEN:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden reassurance "
                    f"phrase {word!r}"
                )
        for word in _PANIC_FORBIDDEN:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden panic-inducing "
                    f"phrase {word!r}"
                )


@dataclass
class StationReport:
    """Per-station per-window report."""

    station_id: str
    scores: list[AvianHealthScore] = field(default_factory=list)
    alerts: list[OrnithologistAlert] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.station_id:
            raise ValueError("station_id must not be empty")

    @property
    def observation_count(self) -> int:
        return len(self.scores)

    def alerts_at_level(self, level: AlertLevel) -> list[OrnithologistAlert]:
        return [a for a in self.alerts if a.level == level]

    def alerts_of_kind(self, kind: AlertKind) -> list[OrnithologistAlert]:
        return [a for a in self.alerts if a.kind == kind]

    def as_text(self) -> str:
        lines = [
            f"Station: {self.station_id} · "
            f"{self.observation_count} observation"
            f"{'s' if self.observation_count != 1 else ''}",
        ]
        if self.alerts:
            kinds: tuple[AlertKind, ...] = (
                "call_presence", "distress", "vitals",
                "thermal", "mortality_cluster",
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
            # Deliberately observation-worded; never "all clear".
            lines.append(
                "No concerning signals on this pass. Routine "
                "review by the on-station ornithologist remains "
                "required."
            )
        return "\n".join(lines)


__all__ = [
    "AvianHealthScore",
    "BirdObservation",
    "BodyThermalSample",
    "CallSample",
    "DeadBirdCandidate",
    "OrnithologistAlert",
    "StationReport",
    "WingbeatSample",
]
