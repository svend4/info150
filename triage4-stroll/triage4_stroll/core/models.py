"""Core dataclasses for triage4-stroll.

Domain: a single-person day-walk advisor. The unit of input is a
``StrollSegment`` (one continuous walk window of N minutes); the
unit of output is a ``StrollAdvisory`` (channel scores + cues).

Design note — flat dataclasses, frozen where sensible, plain
strings (`Literal`) for enums. The engine reads these; the sim
populates them; tests compare them. No inheritance from triage4.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import (
    CueKind,
    CueSeverity,
    PaceAdvisory,
    Terrain,
    VALID_PACE_ADVISORIES,
    VALID_SEVERITIES,
    VALID_TERRAINS,
)


# ---------------------------------------------------------------------------
# Raw observation
# ---------------------------------------------------------------------------


@dataclass
class StrollSegment:
    """One walk window — typically 1-30 minutes.

    Channel inputs are normalised scalars from camera + manual UI
    sliders + optional wearable. The engine combines them into the
    advisory; it does not store raw frames.
    """

    walker_id: str
    terrain: Terrain
    pace_kmh: float
    duration_min: float
    activity_intensity: float    # camera-derived motion proxy in [0, 1]
    sun_exposure_proxy: float    # camera-derived luminance proxy in [0, 1]
    minutes_since_rest: float    # operator-tracked or auto
    air_temp_c: float | None = None  # ambient temperature, optional
    hr_bpm: float | None = None      # operator-supplied or wearable

    def __post_init__(self) -> None:
        if not self.walker_id:
            raise ValueError("walker_id must not be empty")
        if self.terrain not in VALID_TERRAINS:
            raise ValueError(
                f"terrain must be one of {VALID_TERRAINS}, got {self.terrain!r}"
            )
        if not 0.0 <= self.pace_kmh <= 20.0:
            raise ValueError(
                f"pace_kmh out of plausible range [0, 20], got {self.pace_kmh}"
            )
        if not 0.0 <= self.duration_min <= 24 * 60:
            raise ValueError(
                f"duration_min out of plausible range [0, 1440], got {self.duration_min}"
            )
        for name, val in (
            ("activity_intensity", self.activity_intensity),
            ("sun_exposure_proxy", self.sun_exposure_proxy),
        ):
            if not 0.0 <= val <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {val}")
        if not 0.0 <= self.minutes_since_rest <= 24 * 60:
            raise ValueError(
                f"minutes_since_rest must be in [0, 1440], got {self.minutes_since_rest}"
            )
        if self.air_temp_c is not None and not -40.0 <= self.air_temp_c <= 60.0:
            raise ValueError(
                f"air_temp_c out of plausible range [-40, 60], got {self.air_temp_c}"
            )
        if self.hr_bpm is not None and not 30.0 <= self.hr_bpm <= 220.0:
            raise ValueError(
                f"hr_bpm out of plausible range [30, 220], got {self.hr_bpm}"
            )


# ---------------------------------------------------------------------------
# Engine output
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CoachCue:
    """A single coaching cue surfaced to the walker.

    Wellness posture: the cue text MUST NOT contain medical
    vocabulary. It describes WHAT was observed and SUGGESTS an
    adjustment.
    """

    kind: CueKind
    severity: CueSeverity
    text: str
    observed_value: float | None = None

    def __post_init__(self) -> None:
        if self.severity not in VALID_SEVERITIES:
            raise ValueError(
                f"severity must be one of {VALID_SEVERITIES}, got {self.severity!r}"
            )
        if not self.text.strip():
            raise ValueError("cue text must not be empty")
        _FORBIDDEN = ("injured", "diagnose", "treat ", "dangerous", "medical")
        low = self.text.lower()
        for word in _FORBIDDEN:
            if word in low:
                raise ValueError(
                    f"cue text contains forbidden word {word!r} "
                    f"(wellness posture; see docs/PHILOSOPHY.md)"
                )


@dataclass
class StrollAdvisory:
    """Engine output for one segment.

    Channel scores are 1.0 = great, 0.0 = poor.
    """

    segment: StrollSegment
    fatigue_index: float
    hydration_due: bool
    shade_advisory: bool
    pace_advisory: PaceAdvisory
    rest_due: bool
    overall_safety: float
    cues: list[CoachCue] = field(default_factory=list)

    def __post_init__(self) -> None:
        for name, v in (
            ("fatigue_index", self.fatigue_index),
            ("overall_safety", self.overall_safety),
        ):
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {v}")
        if self.pace_advisory not in VALID_PACE_ADVISORIES:
            raise ValueError(
                f"pace_advisory must be one of {VALID_PACE_ADVISORIES}, "
                f"got {self.pace_advisory!r}"
            )

    def cues_at_severity(self, severity: CueSeverity) -> list[CoachCue]:
        return [c for c in self.cues if c.severity == severity]

    def as_text(self) -> str:
        lines: list[str] = []
        lines.append(
            f"Walker {self.segment.walker_id} · {self.segment.terrain} · "
            f"{self.segment.duration_min:.0f} min · pace {self.segment.pace_kmh:.1f} km/h"
        )
        lines.append(
            f"Fatigue: {self.fatigue_index:.2f}   Overall safety: {self.overall_safety:.2f}"
        )
        flags: list[str] = []
        if self.hydration_due:
            flags.append("hydration_due")
        if self.shade_advisory:
            flags.append("shade_advisory")
        if self.rest_due:
            flags.append("rest_due")
        flags.append(f"pace={self.pace_advisory}")
        lines.append("Flags: " + ", ".join(flags))
        if not self.cues:
            lines.append("No cues — keep walking comfortably.")
            return "\n".join(lines)
        for sev in ("severe", "minor"):
            typed_sev: CueSeverity = sev  # type: ignore[assignment]
            for c in self.cues_at_severity(typed_sev):
                lines.append(f"  [{sev}] [{c.kind}] {c.text}")
        return "\n".join(lines)


__all__ = [
    "CoachCue",
    "StrollAdvisory",
    "StrollSegment",
]
