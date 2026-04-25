"""Core dataclasses for triage4-fish.

Three architectural features unique to this sibling:

- Multi-modal observation: ``PenObservation`` carries
  five sample types — four vision-derived
  (gill_rate / school_cohesion / sea_lice /
  mortality_floor) and one chemistry-derived
  (water_chemistry).
- ``FarmManagerAlert`` enforces the new antibiotic-dosing-
  overreach boundary as the dataclass-level claims guard.
- ``PenReport.as_text`` for an empty alert list produces
  the strongest no-false-reassurance text in the catalog.

See docs/PHILOSOPHY.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .enums import (
    AlertKind,
    Species,
    VALID_ALERT_KINDS,
    VALID_SPECIES,
    VALID_WATER_CONDITIONS,
    VALID_WELFARE_LEVELS,
    WaterCondition,
    WelfareLevel,
)


# Same field-security regex as triage4-wild / triage4-bird —
# offshore tuna / bluefin pens are theft targets.
_DECIMAL_PAIR_RE = re.compile(
    r"[-+]?\d+\.\d{2,}\s*[,\s]\s*[-+]?\d+\.\d{2,}"
)


# ---------------------------------------------------------------------------
# Vision-derived samples
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GillRateSample:
    """Pen-aggregate gill rate (Eulerian-derived) per
    snapshot. Rate in breaths/min — species reference bands
    in ``species_aquatic_bands``.
    """

    t_s: float
    rate_bpm: float

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if not 5.0 <= self.rate_bpm <= 200.0:
            raise ValueError(
                f"rate_bpm out of plausible range: {self.rate_bpm}"
            )


@dataclass(frozen=True)
class SchoolCohesionSample:
    """Schooling-behaviour aggregate.

    ``cohesion`` in [0, 1], 1.0 = tight school with low
    inter-fish-distance variance, 0.0 = scattered / chaotic.
    """

    t_s: float
    cohesion: float

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if not 0.0 <= self.cohesion <= 1.0:
            raise ValueError(
                f"cohesion must be in [0, 1], got {self.cohesion}"
            )


@dataclass(frozen=True)
class SeaLiceSample:
    """Sea-lice burden indicator from upstream visual
    classifier.

    ``count_proxy`` is a unit-interval indicator (NOT a
    raw count) — upstream classifier rolls per-fish counts
    into a per-pen burden indicator.
    """

    t_s: float
    count_proxy: float
    classifier_confidence: float

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if not 0.0 <= self.count_proxy <= 1.0:
            raise ValueError(
                f"count_proxy must be in [0, 1], got {self.count_proxy}"
            )
        if not 0.0 <= self.classifier_confidence <= 1.0:
            raise ValueError(
                f"classifier_confidence must be in [0, 1], "
                f"got {self.classifier_confidence}"
            )


@dataclass(frozen=True)
class MortalityFloorSample:
    """Dead-fish-on-bottom count from upstream classifier."""

    t_s: float
    count: int
    confidence: float

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if not 0 <= self.count <= 10000:
            raise ValueError(
                f"count out of plausible range: {self.count}"
            )
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence must be in [0, 1], got {self.confidence}"
            )


# ---------------------------------------------------------------------------
# Chemistry-derived sample
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WaterChemistrySample:
    """Bundled pen-sensor reading.

    DO in mg/L, temperature in °C, salinity in ppt,
    turbidity in NTU. Reference bands per species in
    ``species_aquatic_bands``.
    """

    t_s: float
    dissolved_oxygen_mg_l: float
    temperature_c: float
    salinity_ppt: float
    turbidity_ntu: float

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if not 0.0 <= self.dissolved_oxygen_mg_l <= 25.0:
            raise ValueError(
                f"dissolved_oxygen_mg_l out of plausible range: "
                f"{self.dissolved_oxygen_mg_l}"
            )
        if not -2.0 <= self.temperature_c <= 40.0:
            raise ValueError(
                f"temperature_c out of plausible range: "
                f"{self.temperature_c}"
            )
        if not 0.0 <= self.salinity_ppt <= 50.0:
            raise ValueError(
                f"salinity_ppt out of plausible range: "
                f"{self.salinity_ppt}"
            )
        if not 0.0 <= self.turbidity_ntu <= 200.0:
            raise ValueError(
                f"turbidity_ntu out of plausible range: "
                f"{self.turbidity_ntu}"
            )


@dataclass
class PenObservation:
    """One pen-pass observation — multi-modal samples.

    ``pen_id`` is opaque. ``location_handle`` is opaque
    (offshore-pen GPS coordinates are theft targets;
    field-security boundary inherited from triage4-wild).
    """

    pen_id: str
    species: Species
    location_handle: str
    window_duration_s: float
    water_condition: WaterCondition = "clear"
    gill_rate_samples: list[GillRateSample] = field(default_factory=list)
    school_samples: list[SchoolCohesionSample] = field(default_factory=list)
    sea_lice_samples: list[SeaLiceSample] = field(default_factory=list)
    mortality_samples: list[MortalityFloorSample] = field(default_factory=list)
    water_chemistry_samples: list[WaterChemistrySample] = \
        field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.pen_id:
            raise ValueError("pen_id must not be empty")
        if self.species not in VALID_SPECIES:
            raise ValueError(
                f"species must be one of {VALID_SPECIES}, "
                f"got {self.species!r}"
            )
        if not self.location_handle.strip():
            raise ValueError("location_handle must not be empty")
        if _DECIMAL_PAIR_RE.search(self.location_handle):
            raise ValueError(
                "location_handle appears to contain decimal-degree "
                "coordinates — opaque pen-handle tokens only "
                "(field-security boundary; see docs/PHILOSOPHY.md)."
            )
        if self.window_duration_s <= 0 or self.window_duration_s > 86400:
            raise ValueError(
                f"window_duration_s must be in (0, 86400], "
                f"got {self.window_duration_s}"
            )
        if self.water_condition not in VALID_WATER_CONDITIONS:
            raise ValueError(
                f"water_condition must be one of "
                f"{VALID_WATER_CONDITIONS}, got "
                f"{self.water_condition!r}"
            )


# ---------------------------------------------------------------------------
# Engine output
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PenWelfareScore:
    """Per-pen multi-modal welfare summary."""

    pen_id: str
    gill_rate_safety: float
    school_cohesion_safety: float
    sea_lice_safety: float
    mortality_safety: float
    water_chemistry_safety: float
    overall: float
    welfare_level: WelfareLevel

    def __post_init__(self) -> None:
        for name, v in (
            ("gill_rate_safety", self.gill_rate_safety),
            ("school_cohesion_safety", self.school_cohesion_safety),
            ("sea_lice_safety", self.sea_lice_safety),
            ("mortality_safety", self.mortality_safety),
            ("water_chemistry_safety", self.water_chemistry_safety),
            ("overall", self.overall),
        ):
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {v}")
        if self.welfare_level not in VALID_WELFARE_LEVELS:
            raise ValueError(
                f"welfare_level must be one of {VALID_WELFARE_LEVELS}, "
                f"got {self.welfare_level!r}"
            )


@dataclass(frozen=True)
class FarmManagerAlert:
    """Farm-manager facing alert.

    Six-list claims guard:
    - Antibiotic-dosing-overreach (NEW in this sibling).
    - Veterinary-practice (inherited from triage4-farm).
    - Outbreak-diagnosis-overreach (from triage4-bird,
      specialised for fish-disease nomenclature).
    - Field-security (from triage4-wild).
    - No-false-reassurance (strongest in the catalog).
    - Operational + panic-prevention.

    See docs/PHILOSOPHY.md for the per-list rationale.
    """

    pen_id: str
    kind: AlertKind
    level: WelfareLevel
    text: str
    location_handle: str
    observed_value: float | None = None

    def __post_init__(self) -> None:
        if self.kind not in VALID_ALERT_KINDS:
            raise ValueError(
                f"kind must be one of {VALID_ALERT_KINDS}, "
                f"got {self.kind!r}"
            )
        if self.level not in VALID_WELFARE_LEVELS:
            raise ValueError(
                f"level must be one of {VALID_WELFARE_LEVELS}, "
                f"got {self.level!r}"
            )
        if not self.text.strip():
            raise ValueError("alert text must not be empty")
        if not self.location_handle.strip():
            raise ValueError("location_handle must not be empty")
        if _DECIMAL_PAIR_RE.search(self.location_handle):
            raise ValueError(
                "location_handle contains decimal-degree coords — "
                "field-security boundary"
            )
        if _DECIMAL_PAIR_RE.search(self.text):
            raise ValueError(
                "alert text contains decimal-degree coords — "
                "field-security boundary"
            )

        low = self.text.lower()

        _ANTIBIOTIC_DOSING_OVERREACH = (
            "administer antibiotic",
            "administer antimicrobial",
            "dose with",
            "dosing recommendation",
            "prescribe antimicrobial",
            "prescribe antibiotic",
            "treatment regimen",
            "course of treatment",
            "withdrawal period",
            "oxytetracycline",
            "florfenicol",
            "emamectin",
            "azamethiphos",
            "medicated feed",
        )
        _VETERINARY_PRACTICE = (
            "diagnose",
            "diagnosis",
            "prescribe",
            "medicate",
            "medication regimen",
            "therapy",
            "dose ",
            "administer",
        )
        _OUTBREAK_OVERREACH = (
            "outbreak detected",
            "outbreak confirmed",
            "epidemic",
            "pandemic",
            "disease confirmed",
            "isa confirmed",
            "isav confirmed",
            "pd confirmed",
            "ipn confirmed",
            "sav confirmed",
        )
        _FIELD_SECURITY = (
            "latitude",
            "longitude",
            "lat:",
            "lng:",
            "lon:",
            "gps coordinates",
            "coordinates:",
            "located at",
        )
        _NO_FALSE_REASSURANCE = (
            "pen is healthy",
            "no outbreak",
            "stock is safe",
            "stocks are safe",
            "clean bill of health",
            "no concerns",
            "no welfare concerns",
            "all pens safe",
            "no disease",
            "disease-free",
        )
        _OPERATIONAL = (
            "cull the pen",
            "harvest now",
            "move stock",
            "dump the pen",
        )
        _PANIC = (
            "disaster",
            "catastrophe",
            "mass mortality",
        )

        for word in _ANTIBIOTIC_DOSING_OVERREACH:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden antibiotic-"
                    f"dosing-overreach phrase {word!r} — dosing "
                    f"is veterinary practice. See "
                    f"docs/PHILOSOPHY.md."
                )
        for word in _VETERINARY_PRACTICE:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden veterinary-"
                    f"practice phrase {word!r}"
                )
        for word in _OUTBREAK_OVERREACH:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden outbreak-"
                    f"diagnosis-overreach phrase {word!r}"
                )
        for word in _FIELD_SECURITY:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden field-security "
                    f"phrase {word!r}"
                )
        for word in _NO_FALSE_REASSURANCE:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden no-false-"
                    f"reassurance phrase {word!r} — failure-cost "
                    f"asymmetry; see docs/PHILOSOPHY.md."
                )
        for word in _OPERATIONAL:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden operational "
                    f"phrase {word!r}"
                )
        for word in _PANIC:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden panic-inducing "
                    f"phrase {word!r}"
                )


@dataclass
class PenReport:
    """Per-pen aggregate report."""

    farm_id: str
    scores: list[PenWelfareScore] = field(default_factory=list)
    alerts: list[FarmManagerAlert] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.farm_id:
            raise ValueError("farm_id must not be empty")

    @property
    def pen_count(self) -> int:
        return len(self.scores)

    def alerts_at_level(self, level: WelfareLevel) -> list[FarmManagerAlert]:
        return [a for a in self.alerts if a.level == level]

    def alerts_of_kind(self, kind: AlertKind) -> list[FarmManagerAlert]:
        return [a for a in self.alerts if a.kind == kind]

    def as_text(self) -> str:
        lines = [
            f"Farm: {self.farm_id} · "
            f"{self.pen_count} pen-observation"
            f"{'s' if self.pen_count != 1 else ''}",
        ]
        if self.alerts:
            kinds: tuple[AlertKind, ...] = (
                "gill_rate", "school_cohesion", "sea_lice",
                "mortality_floor", "water_chemistry",
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
                    f"  - [{a.kind} / pen={a.pen_id}] {a.text}"
                )
        if watch:
            lines.append("WATCH alerts:")
            for a in watch:
                lines.append(
                    f"  - [{a.kind} / pen={a.pen_id}] {a.text}"
                )
        if not urgent and not watch:
            # Strongest no-false-reassurance text in the
            # catalog. Failure-cost asymmetry: missed
            # outbreak = $1M loss.
            lines.append(
                "Absence of alerts is not a clearance of pen "
                "welfare — vet + farm-manager review remains "
                "required. The library observed one pass; the "
                "next pass may surface what this one missed."
            )
        return "\n".join(lines)


__all__ = [
    "FarmManagerAlert",
    "GillRateSample",
    "MortalityFloorSample",
    "PenObservation",
    "PenReport",
    "PenWelfareScore",
    "SchoolCohesionSample",
    "SeaLiceSample",
    "WaterChemistrySample",
]
