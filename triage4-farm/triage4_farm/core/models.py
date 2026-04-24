"""Core dataclasses for triage4-farm.

Intentionally flat, frozen where sensible, no methods beyond
trivial validation + a short human-readable `as_text`. The
welfare engine reads these; the synthetic herd populates them;
tests compare them. No inheritance from triage4 or triage4-fit
types — copy-fork, not cross-import.

Regulatory posture lives in the claims guard on ``FarmerAlert``.
See docs/PHILOSOPHY.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import (
    AlertKind,
    Species,
    VALID_ALERT_KINDS,
    VALID_FLAGS,
    VALID_SPECIES,
    WelfareFlag,
)


# ---------------------------------------------------------------------------
# Raw observations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class JointPoseSample:
    """One joint position at one instant, in image-plane coordinates.

    Coordinates are normalised [0, 1] — matches triage4-fit's
    convention so the pose-estimator adapter can be swapped
    without rewriting the signatures.
    """

    joint: str
    x: float
    y: float
    confidence: float = 1.0

    def __post_init__(self) -> None:
        for name, val, lo, hi in (
            ("x", self.x, 0.0, 1.0),
            ("y", self.y, 0.0, 1.0),
            ("confidence", self.confidence, 0.0, 1.0),
        ):
            if not lo <= val <= hi:
                raise ValueError(
                    f"{name} must be in [{lo}, {hi}], got {val}"
                )


@dataclass
class AnimalObservation:
    """One animal's worth of stand-off observations for a pass.

    A "pass" is a single walk-by past the stall, alley, or pen
    camera. Not every signature is always available: pose frames
    come from the camera, respiratory + thermal come from
    optional sensors.
    """

    animal_id: str
    species: Species
    # Per-frame pose samples, chronologically ordered.
    pose_frames: list[list[JointPoseSample]] = field(default_factory=list)
    # Observation-window duration in seconds (used by gait cadence).
    duration_s: float = 0.0
    # Stand-off respiratory rate estimate, breaths per minute.
    respiratory_bpm: float | None = None
    # Surface-temperature hotspot signal from IR — unit-free
    # proxy in [0, 1], 1.0 = dramatic focal hotspot vs body
    # baseline. None = no IR sensor.
    thermal_hotspot: float | None = None
    # Self-reported stock-person note, free-form. Used by the
    # engine only to attach context to alerts, never parsed
    # as a signal.
    stockperson_note: str | None = None

    def __post_init__(self) -> None:
        if not self.animal_id:
            raise ValueError("animal_id must not be empty")
        if self.species not in VALID_SPECIES:
            raise ValueError(
                f"species must be one of {VALID_SPECIES}, got {self.species!r}"
            )
        if self.duration_s < 0:
            raise ValueError(
                f"duration_s must be ≥ 0, got {self.duration_s}"
            )
        if self.respiratory_bpm is not None and not 2 <= self.respiratory_bpm <= 120:
            raise ValueError(
                f"respiratory_bpm out of plausible range: {self.respiratory_bpm}"
            )
        if self.thermal_hotspot is not None and not 0.0 <= self.thermal_hotspot <= 1.0:
            raise ValueError(
                f"thermal_hotspot must be in [0, 1], got {self.thermal_hotspot}"
            )


# ---------------------------------------------------------------------------
# Engine output
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WelfareScore:
    """Per-animal score summary.

    Channels are unit-interval, 1.0 = textbook welfare for this
    channel. ``overall`` is a weighted combination the welfare
    engine produces. ``flag`` is a discrete bucket the engine
    assigns after thresholding the continuous score.
    """

    animal_id: str
    gait: float
    respiratory: float
    thermal: float
    overall: float
    flag: WelfareFlag

    def __post_init__(self) -> None:
        for name, v in (
            ("gait", self.gait),
            ("respiratory", self.respiratory),
            ("thermal", self.thermal),
            ("overall", self.overall),
        ):
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {v}")
        if self.flag not in VALID_FLAGS:
            raise ValueError(
                f"flag must be one of {VALID_FLAGS}, got {self.flag!r}"
            )


@dataclass(frozen=True)
class FarmerAlert:
    """A single farmer-facing alert surfaced by the welfare engine.

    Observation-only posture: the alert text MUST NOT contain
    veterinary-practice vocabulary. The dataclass-level claims
    guard in ``__post_init__`` enforces the forbidden list. See
    docs/PHILOSOPHY.md for the rationale.
    """

    animal_id: str
    kind: AlertKind
    flag: WelfareFlag
    text: str
    observed_value: float | None = None

    def __post_init__(self) -> None:
        if self.kind not in VALID_ALERT_KINDS:
            raise ValueError(
                f"kind must be one of {VALID_ALERT_KINDS}, got {self.kind!r}"
            )
        if self.flag not in VALID_FLAGS:
            raise ValueError(
                f"flag must be one of {VALID_FLAGS}, got {self.flag!r}"
            )
        if not self.text.strip():
            raise ValueError("alert text must not be empty")
        # Claims guard — never emit veterinary-practice words.
        # Trailing space on single-word tokens that appear inside
        # common safe phrases (e.g. "dose response" is fine, "dose "
        # as an instruction is not). Kept permissive on purpose:
        # the guard is a backstop, not the only layer.
        _FORBIDDEN = (
            "diagnose",
            "diagnosis",
            "prescribe",
            "administer",
            "medicate",
            "antibiotic",
            "withdrawal period",
            "treat ",
            "dose ",
            "therapy",
        )
        low = self.text.lower()
        for word in _FORBIDDEN:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden word {word!r} "
                    f"(observation-only posture; see docs/PHILOSOPHY.md)"
                )


@dataclass
class HerdReport:
    """Welfare engine output for a whole pass over a herd."""

    farm_id: str
    scores: list[WelfareScore] = field(default_factory=list)
    alerts: list[FarmerAlert] = field(default_factory=list)
    herd_overall: float = 0.0

    def __post_init__(self) -> None:
        if not self.farm_id:
            raise ValueError("farm_id must not be empty")
        if not 0.0 <= self.herd_overall <= 1.0:
            raise ValueError(
                f"herd_overall must be in [0, 1], got {self.herd_overall}"
            )

    def alerts_at_flag(self, flag: WelfareFlag) -> list[FarmerAlert]:
        return [a for a in self.alerts if a.flag == flag]

    @property
    def animal_count(self) -> int:
        return len(self.scores)

    def as_text(self) -> str:
        """Short human-readable summary. Used in the demo + tests."""
        lines: list[str] = []
        lines.append(
            f"Farm: {self.farm_id} · "
            f"{self.animal_count} animals observed"
        )
        lines.append(f"Herd welfare: {self.herd_overall:.2f} / 1.00")
        if not self.alerts:
            lines.append(
                "No alerts surfaced — herd looked consistent with routine welfare."
            )
            return "\n".join(lines)
        urgent = self.alerts_at_flag("urgent")
        concern = self.alerts_at_flag("concern")
        if urgent:
            lines.append("URGENT alerts (vet review recommended):")
            for a in urgent:
                lines.append(f"  - [{a.kind}] animal {a.animal_id}: {a.text}")
        if concern:
            lines.append("CONCERN alerts (monitor / vet review recommended):")
            for a in concern:
                lines.append(f"  - [{a.kind}] animal {a.animal_id}: {a.text}")
        return "\n".join(lines)


__all__ = [
    "AnimalObservation",
    "FarmerAlert",
    "HerdReport",
    "JointPoseSample",
    "WelfareScore",
]
