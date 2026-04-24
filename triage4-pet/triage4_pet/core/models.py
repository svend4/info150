"""Core dataclasses for triage4-pet.

Dual-audience architecture: ``OwnerMessage`` and
``VetSummary`` each have their own forbidden-vocabulary
list, and the library emits both from one observation.
See docs/PHILOSOPHY.md for rationale.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import (
    PainBehaviorKind,
    SpeciesKind,
    TriageRecommendation,
    VALID_PAIN_BEHAVIORS,
    VALID_RECOMMENDATIONS,
    VALID_SPECIES,
    VALID_VIDEO_QUALITIES,
    VideoQuality,
)


# ---------------------------------------------------------------------------
# Raw observations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PoseSample:
    """Pose-detector output for one frame.

    ``visible_keypoints`` is the count of anatomical
    keypoints the upstream detector could locate with
    acceptable confidence. The signature layer uses this to
    gate gait calculations (too few keypoints = skip).
    """

    t_s: float
    visible_keypoints: int
    detection_confidence: float

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if not 0 <= self.visible_keypoints <= 50:
            raise ValueError(
                f"visible_keypoints out of plausible range: "
                f"{self.visible_keypoints}"
            )
        if not 0.0 <= self.detection_confidence <= 1.0:
            raise ValueError(
                f"detection_confidence must be in [0, 1], "
                f"got {self.detection_confidence}"
            )


@dataclass(frozen=True)
class GaitSample:
    """Per-cycle gait estimate.

    ``limb_asymmetry`` in [0, 1], 0 = symmetric gait, 1 =
    one-sided lameness. ``pace_consistency`` in [0, 1], 1 =
    rhythmic gait. Derived from a pose-tracking model;
    consumed here as a scalar input.
    """

    t_s: float
    limb_asymmetry: float
    pace_consistency: float

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        for name, v in (
            ("limb_asymmetry", self.limb_asymmetry),
            ("pace_consistency", self.pace_consistency),
        ):
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {v}")


@dataclass(frozen=True)
class BreathingSample:
    """Respiratory-rate estimate over a short window.

    ``rate_bpm`` is breaths per minute. ``at_rest`` is True
    when the pet was still enough for the estimate to be
    reliable — panting-at-rest is a pain-behavior tell.
    """

    t_s: float
    rate_bpm: float
    at_rest: bool

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if not 2.0 <= self.rate_bpm <= 200.0:
            raise ValueError(
                f"rate_bpm out of plausible range: {self.rate_bpm}"
            )


@dataclass(frozen=True)
class VitalHRSample:
    """Heart-rate estimate via Eulerian magnification.

    ``hr_bpm`` is beats per minute. ``reliable`` is True
    when the pet was still enough, lighting was good, and
    the upstream signal crossed a quality threshold.
    """

    t_s: float
    hr_bpm: float
    reliable: bool

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if not 20.0 <= self.hr_bpm <= 400.0:
            raise ValueError(
                f"hr_bpm out of plausible range: {self.hr_bpm}"
            )


@dataclass(frozen=True)
class PainBehaviorSample:
    """Classifier output for one detected pain behavior."""

    t_s: float
    kind: PainBehaviorKind
    confidence: float

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if self.kind not in VALID_PAIN_BEHAVIORS:
            raise ValueError(
                f"kind must be one of {VALID_PAIN_BEHAVIORS}, "
                f"got {self.kind!r}"
            )
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence must be in [0, 1], got {self.confidence}"
            )


@dataclass
class PetObservation:
    """One submission — a single 30-60 s video upload.

    The species is supplied explicitly by the consumer app
    (either from the owner choosing it in the flow or from
    an upstream species classifier). The library does not
    re-detect it. ``pet_token`` is an opaque identifier
    from the consumer app; the library never correlates it
    to owner PII.
    """

    pet_token: str
    species: SpeciesKind
    window_duration_s: float
    age_years: float | None = None
    owner_note: str | None = None
    video_quality: VideoQuality = "good"
    pose_samples: list[PoseSample] = field(default_factory=list)
    gait_samples: list[GaitSample] = field(default_factory=list)
    breathing_samples: list[BreathingSample] = field(default_factory=list)
    hr_samples: list[VitalHRSample] = field(default_factory=list)
    pain_samples: list[PainBehaviorSample] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.pet_token:
            raise ValueError("pet_token must not be empty")
        if self.species not in VALID_SPECIES:
            raise ValueError(
                f"species must be one of {VALID_SPECIES}, "
                f"got {self.species!r}"
            )
        if self.window_duration_s <= 0 or self.window_duration_s > 600:
            raise ValueError(
                f"window_duration_s must be in (0, 600], "
                f"got {self.window_duration_s}"
            )
        if self.age_years is not None and not 0.0 <= self.age_years <= 50.0:
            raise ValueError(
                f"age_years out of plausible range: {self.age_years}"
            )
        if self.video_quality not in VALID_VIDEO_QUALITIES:
            raise ValueError(
                f"video_quality must be one of "
                f"{VALID_VIDEO_QUALITIES}, got {self.video_quality!r}"
            )


# ---------------------------------------------------------------------------
# Engine output
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PetAssessment:
    """Per-submission assessment summary (channel scores).

    All four channel scores in [0, 1], 1.0 = textbook-
    healthy observation, 0.0 = strong concern signal.
    """

    pet_token: str
    gait_safety: float
    respiratory_safety: float
    cardiac_safety: float
    pain_safety: float
    overall: float
    recommendation: TriageRecommendation

    def __post_init__(self) -> None:
        for name, v in (
            ("gait_safety", self.gait_safety),
            ("respiratory_safety", self.respiratory_safety),
            ("cardiac_safety", self.cardiac_safety),
            ("pain_safety", self.pain_safety),
            ("overall", self.overall),
        ):
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {v}")
        if self.recommendation not in VALID_RECOMMENDATIONS:
            raise ValueError(
                f"recommendation must be one of "
                f"{VALID_RECOMMENDATIONS}, got {self.recommendation!r}"
            )


# Identifier-prefix guard — common pet-name tokens blocked
# from either output dataclass. Small representative list
# covering US / UK popular pet names; real deployments
# would extend.
_PET_NAME_PREFIXES: tuple[str, ...] = (
    "max ",
    "bella ",
    "charlie ",
    "luna ",
    "cooper ",
    "lucy ",
    "buddy ",
    "daisy ",
    "bailey ",
    "rocky ",
    "milo ",
    "molly ",
)


def _identifier_hit(text: str, prefixes: tuple[str, ...]) -> str | None:
    """Return the matching prefix if the text identifies a
    specific pet by common name, else None."""
    for prefix in prefixes:
        if prefix in text:
            return prefix
    return None


@dataclass(frozen=True)
class OwnerMessage:
    """Owner-facing message.

    STRICT claims guard — owners are laypeople, cannot
    receive clinical jargon, cannot receive reassurance,
    cannot be told they can skip a vet visit. See
    docs/PHILOSOPHY.md.
    """

    pet_token: str
    text: str

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("owner message text must not be empty")

        low = self.text.lower()

        _CLINICAL_JARGON = (
            "arthritis",
            "fracture",
            "infection",
            "malignancy",
            "tumor",
            "neoplasia",
            "cardiomyopathy",
            "gastroenteritis",
            "pancreatitis",
            "nephropathy",
            "hepatopathy",
            "osteochondrosis",
            "hypothyroidism",
            "hyperthyroidism",
            "diabetes",
            "seizure",
            "stroke",
            "diagnosis:",
        )
        _DEFINITIVE_DIAGNOSIS = (
            "your pet has a",
            "your pet is suffering from",
            "this is a",
            "confirms a",
        )
        _REASSURANCE_DELAY = (
            "everything is fine",
            "your pet is fine",
            "no need to worry",
            "no concerns",
            "safe to skip",
            "no vet visit needed",
            "can wait without seeing",
            "nothing is wrong",
            "your pet is healthy",
            "no issues at all",
        )
        _OWNER_INSTRUCTION = (
            "give medication",
            "administer medication",
            "prescribe",
            "give a pill",
        )

        for word in _CLINICAL_JARGON:
            if word in low:
                raise ValueError(
                    f"owner message contains forbidden clinical "
                    f"word {word!r} (owner is a layperson; "
                    f"see docs/PHILOSOPHY.md)"
                )
        for word in _DEFINITIVE_DIAGNOSIS:
            if word in low:
                raise ValueError(
                    f"owner message contains forbidden definitive-"
                    f"diagnosis phrase {word!r} (see "
                    f"docs/PHILOSOPHY.md)"
                )
        for word in _REASSURANCE_DELAY:
            if word in low:
                raise ValueError(
                    f"owner message contains forbidden "
                    f"reassurance / delay-implication phrase "
                    f"{word!r} (see docs/PHILOSOPHY.md)"
                )
        for word in _OWNER_INSTRUCTION:
            if word in low:
                raise ValueError(
                    f"owner message contains forbidden owner-"
                    f"instruction phrase {word!r} (the vet "
                    f"prescribes; see docs/PHILOSOPHY.md)"
                )
        hit = _identifier_hit(low, _PET_NAME_PREFIXES)
        if hit is not None:
            raise ValueError(
                f"owner message appears to identify a specific "
                f"pet by common name ({hit!r}; see "
                f"docs/PHILOSOPHY.md)"
            )


@dataclass(frozen=True)
class VetSummary:
    """Vet-facing multi-paragraph summary.

    Permissive on clinical vocabulary (the vet IS clinical)
    but refuses definitive diagnosis + operational
    scheduling + owner-identifying content.
    """

    pet_token: str
    text: str

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("vet summary text must not be empty")

        low = self.text.lower()

        _DEFINITIVE_DIAGNOSIS = (
            "diagnosis:",
            "confirmed diagnosis",
            "the pet has a fracture",
            "the pet has arthritis",
            "the pet has cancer",
        )
        _OPERATIONAL_SCHEDULING = (
            "schedule surgery",
            "order this procedure",
            "prescribe this drug",
            "prescribe this medication",
            "administer this drug",
            "administer this medication",
        )
        _OWNER_PII = (
            "owner name:",
            "owner phone",
            "owner email",
            "owner address",
            "owner's phone",
            "owner's email",
            "owner's address",
        )

        for word in _DEFINITIVE_DIAGNOSIS:
            if word in low:
                raise ValueError(
                    f"vet summary contains forbidden definitive-"
                    f"diagnosis phrase {word!r} (the vet examines "
                    f"and decides; see docs/PHILOSOPHY.md)"
                )
        for word in _OPERATIONAL_SCHEDULING:
            if word in low:
                raise ValueError(
                    f"vet summary contains forbidden operational-"
                    f"scheduling phrase {word!r} (see "
                    f"docs/PHILOSOPHY.md)"
                )
        for word in _OWNER_PII:
            if word in low:
                raise ValueError(
                    f"vet summary contains forbidden owner-PII "
                    f"phrase {word!r} (owner data flows through a "
                    f"separate consent-gated layer; see "
                    f"docs/PHILOSOPHY.md)"
                )
        hit = _identifier_hit(low, _PET_NAME_PREFIXES)
        if hit is not None:
            raise ValueError(
                f"vet summary contains a pet-name identifier "
                f"({hit!r}; library operates on opaque tokens; "
                f"see docs/PHILOSOPHY.md)"
            )


@dataclass
class PetReport:
    """Per-submission output bundle.

    The engine produces ``PetReport`` — exactly one
    ``PetAssessment``, exactly one ``VetSummary``, and
    zero-or-more ``OwnerMessage`` entries (typically one
    headline message plus per-channel follow-ups when
    multiple channels fire).
    """

    pet_token: str
    assessment: PetAssessment
    vet_summary: VetSummary
    owner_messages: list[OwnerMessage] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.pet_token:
            raise ValueError("pet_token must not be empty")

    def as_text(self) -> str:
        """Short human-readable summary — for the demo."""
        lines = [
            f"Pet: {self.pet_token} · "
            f"{self.assessment.recommendation}",
            "",
            "VET SUMMARY:",
            self.vet_summary.text,
            "",
            "OWNER MESSAGES:",
        ]
        for m in self.owner_messages:
            lines.append(f"  - {m.text}")
        return "\n".join(lines)


__all__ = [
    "BreathingSample",
    "GaitSample",
    "OwnerMessage",
    "PainBehaviorSample",
    "PetAssessment",
    "PetObservation",
    "PetReport",
    "PoseSample",
    "VetSummary",
    "VitalHRSample",
]
