"""Core dataclasses for triage4-clinic.

Flat + frozen + validation-only. Copy-fork of the sibling
shape with two architectural additions unique to this
sibling:

- ``ChannelReading`` carries a ``signature_version`` tag so
  historical outputs can be tied to the exact signature
  code that produced them (audit readiness).
- ``ClinicianAlert`` enforces a POSITIVE requirement on
  top of the usual negative forbidden-list: every alert
  MUST carry a non-empty tuple of
  ``AlternativeExplanation`` entries and a non-empty
  ``reasoning_trace``. See docs/PHILOSOPHY.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import (
    CaptureQuality,
    ChannelKind,
    EscalationRecommendation,
    ExplanationLikelihood,
    VALID_CAPTURE_QUALITIES,
    VALID_CHANNEL_KINDS,
    VALID_ESCALATIONS,
    VALID_LIKELIHOODS,
)


# ---------------------------------------------------------------------------
# Raw samples
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VitalsSample:
    """Stand-off vitals snapshot.

    HR via Eulerian magnification on face video; RR via
    chest-motion FFT. ``reliable`` indicates the upstream
    signal passed a quality threshold — unreliable samples
    are kept for audit but excluded from signature
    calculation.
    """

    t_s: float
    hr_bpm: float
    rr_bpm: float
    reliable: bool

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if not 20.0 <= self.hr_bpm <= 300.0:
            raise ValueError(
                f"hr_bpm out of plausible range: {self.hr_bpm}"
            )
        if not 2.0 <= self.rr_bpm <= 80.0:
            raise ValueError(
                f"rr_bpm out of plausible range: {self.rr_bpm}"
            )


@dataclass(frozen=True)
class AcousticSample:
    """Vocal-strain snapshot from the 'aah' portion of the flow."""

    t_s: float
    strain_score: float   # [0, 1], 0 = effortless voice
    clarity: float        # [0, 1], 1 = clean audio

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        for name, v in (
            ("strain_score", self.strain_score),
            ("clarity", self.clarity),
        ):
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {v}")


@dataclass(frozen=True)
class CoughSample:
    """One detected cough event with classifier confidence."""

    t_s: float
    confidence: float    # classifier confidence [0, 1]

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence must be in [0, 1], got {self.confidence}"
            )


@dataclass(frozen=True)
class PostureSample:
    """Postural stability sample — sway + balance estimate."""

    t_s: float
    sway_magnitude: float   # [0, 1], higher = more sway
    balance_steadiness: float  # [0, 1], higher = steadier

    def __post_init__(self) -> None:
        if self.t_s < 0:
            raise ValueError(f"t_s must be ≥ 0, got {self.t_s}")
        for name, v in (
            ("sway_magnitude", self.sway_magnitude),
            ("balance_steadiness", self.balance_steadiness),
        ):
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {v}")


@dataclass(frozen=True)
class PatientSelfReport:
    """Structured symptom checkboxes the patient reports.

    Each flag is True / False / None; the library surfaces
    the reported flags verbatim for the clinician to review
    but does not attempt clinical inference from them.
    """

    reports_chest_pain: bool = False
    reports_shortness_of_breath: bool = False
    reports_dizziness: bool = False
    reports_fever: bool = False
    reports_persistent_cough: bool = False

    def as_list(self) -> list[str]:
        """Return the True-flagged items as human-readable tokens."""
        mapping = {
            "reports_chest_pain": "chest discomfort",
            "reports_shortness_of_breath": "shortness of breath",
            "reports_dizziness": "dizziness",
            "reports_fever": "fever",
            "reports_persistent_cough": "persistent cough",
        }
        return [
            human for field_name, human in mapping.items()
            if getattr(self, field_name)
        ]


@dataclass
class PatientObservation:
    """One pre-screening submission.

    ``patient_token`` is an opaque identifier from the
    consumer app — NOT name, NOT MRN, NOT phone number.
    The library never correlates the token to PHI.
    """

    patient_token: str
    window_duration_s: float
    age_years: float | None = None
    capture_quality: CaptureQuality = "good"
    vitals_samples: list[VitalsSample] = field(default_factory=list)
    acoustic_samples: list[AcousticSample] = field(default_factory=list)
    cough_samples: list[CoughSample] = field(default_factory=list)
    posture_samples: list[PostureSample] = field(default_factory=list)
    self_report: PatientSelfReport = field(default_factory=PatientSelfReport)

    def __post_init__(self) -> None:
        if not self.patient_token:
            raise ValueError("patient_token must not be empty")
        if self.window_duration_s <= 0 or self.window_duration_s > 600:
            raise ValueError(
                f"window_duration_s must be in (0, 600], "
                f"got {self.window_duration_s}"
            )
        if self.age_years is not None and not 0.0 <= self.age_years <= 130.0:
            raise ValueError(
                f"age_years out of plausible range: {self.age_years}"
            )
        if self.capture_quality not in VALID_CAPTURE_QUALITIES:
            raise ValueError(
                f"capture_quality must be one of "
                f"{VALID_CAPTURE_QUALITIES}, got "
                f"{self.capture_quality!r}"
            )


# ---------------------------------------------------------------------------
# Engine output
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChannelReading:
    """One channel's fused reading with audit-ready metadata.

    ``signature_version`` names the code that produced this
    reading — designed so a retrospective review can tie
    the reading back to the exact signature implementation.
    """

    channel: ChannelKind
    value: float
    signature_version: str

    def __post_init__(self) -> None:
        if self.channel not in VALID_CHANNEL_KINDS:
            raise ValueError(
                f"channel must be one of {VALID_CHANNEL_KINDS}, "
                f"got {self.channel!r}"
            )
        if not 0.0 <= self.value <= 1.0:
            raise ValueError(f"value must be in [0, 1], got {self.value}")
        if not self.signature_version.strip():
            raise ValueError(
                "signature_version must be non-empty (audit "
                "requirement; see docs/PHILOSOPHY.md)"
            )


# Tokens a grounded alternative must NOT contain even when
# framed as "could be X". "Could be tachycardia" still
# sneaks a diagnostic label past the clinician; the
# library sticks to mechanism-level descriptions ("could
# reflect recent exertion", "could reflect anxiety state",
# "could reflect cardiac strain").
_ALT_DIAGNOSTIC_TOKENS = (
    "diagnosis",
    "is a case of",
    "the patient has",
    "confirms",
)


@dataclass(frozen=True)
class AlternativeExplanation:
    """One grounded alternative explanation for a signal.

    ``text`` is a short ≈ 40-120 char description of a
    plausible non-diagnostic framing ("could reflect
    recent exertion"). ``likelihood`` is the qualitative
    strength the library estimates.
    """

    text: str
    likelihood: ExplanationLikelihood

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("alternative explanation text must not be empty")
        if self.likelihood not in VALID_LIKELIHOODS:
            raise ValueError(
                f"likelihood must be one of {VALID_LIKELIHOODS}, "
                f"got {self.likelihood!r}"
            )
        low = self.text.lower()
        for tok in _ALT_DIAGNOSTIC_TOKENS:
            if tok in low:
                raise ValueError(
                    f"alternative explanation contains forbidden "
                    f"diagnostic token {tok!r} — alternatives are "
                    f"mechanism-level, not diagnosis-level "
                    f"(see docs/PHILOSOPHY.md)"
                )


@dataclass(frozen=True)
class PreTriageAssessment:
    """Aggregate per-channel summary + escalation recommendation."""

    patient_token: str
    cardiac_safety: float
    respiratory_safety: float
    acoustic_safety: float
    postural_safety: float
    overall: float
    recommendation: EscalationRecommendation

    def __post_init__(self) -> None:
        for name, v in (
            ("cardiac_safety", self.cardiac_safety),
            ("respiratory_safety", self.respiratory_safety),
            ("acoustic_safety", self.acoustic_safety),
            ("postural_safety", self.postural_safety),
            ("overall", self.overall),
        ):
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {v}")
        if self.recommendation not in VALID_ESCALATIONS:
            raise ValueError(
                f"recommendation must be one of {VALID_ESCALATIONS}, "
                f"got {self.recommendation!r}"
            )


# Patient-identifier heuristic — common first names. Same
# idea as the drive / home / site / aqua / pet prior
# siblings.
_IDENTIFIER_PREFIXES: tuple[str, ...] = (
    "patient john ",
    "patient jane ",
    "patient mike ",
    "patient maria ",
    "patient sam ",
    "patient alex ",
    "patient chris ",
    "patient james ",
    "patient mary ",
    "patient robert ",
)


@dataclass(frozen=True)
class ClinicianAlert:
    """Clinician-facing alert with grounded alternatives.

    POSITIVE requirements enforced at construction time:
    - ``alternative_explanations`` tuple non-empty.
    - ``reasoning_trace`` string non-empty.

    NEGATIVE forbidden-lists also enforced:
    - Definitive diagnosis.
    - Treatment.
    - Regulatory over-claim.
    - Reassurance.
    - Patient-identity patterns.

    See docs/PHILOSOPHY.md for the per-list rationale.
    """

    patient_token: str
    channel: ChannelKind
    recommendation: EscalationRecommendation
    text: str
    alternative_explanations: tuple[AlternativeExplanation, ...]
    reasoning_trace: str
    observed_value: float | None = None

    def __post_init__(self) -> None:
        if self.channel not in VALID_CHANNEL_KINDS:
            raise ValueError(
                f"channel must be one of {VALID_CHANNEL_KINDS}, "
                f"got {self.channel!r}"
            )
        if self.recommendation not in VALID_ESCALATIONS:
            raise ValueError(
                f"recommendation must be one of {VALID_ESCALATIONS}, "
                f"got {self.recommendation!r}"
            )
        if not self.text.strip():
            raise ValueError("alert text must not be empty")

        # Positive requirements.
        if not self.alternative_explanations:
            raise ValueError(
                "ClinicianAlert must carry at least one "
                "AlternativeExplanation (grounded-alternatives "
                "positive requirement; see docs/PHILOSOPHY.md)"
            )
        if not self.reasoning_trace.strip():
            raise ValueError(
                "ClinicianAlert must carry a non-empty "
                "reasoning_trace (audit requirement; see "
                "docs/PHILOSOPHY.md)"
            )

        # Negative requirements (forbidden lists).
        low = self.text.lower()

        _DEFINITIVE_DIAGNOSIS = (
            "diagnosis of",
            "diagnosis:",
            "confirmed diagnosis",
            "the patient has",
            "is a case of",
            "confirms a",
            "diagnosis is",
        )
        _TREATMENT = (
            "prescribe",
            "prescribed",
            "administer",
            "start medication",
            "take this drug",
            "treatment:",
        )
        _REGULATORY_OVERCLAIM = (
            "fda-cleared",
            "fda cleared",
            "medical device",
            "samd",
            "clinically validated",
            "diagnoses",
            "replaces clinician",
            "replaces the clinician",
        )
        _REASSURANCE = (
            "you are fine",
            "no need for review",
            "can skip the visit",
            "no clinical concerns",
            "all vital signs normal",
            "nothing unusual",
        )

        for word in _DEFINITIVE_DIAGNOSIS:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden definitive-"
                    f"diagnosis phrase {word!r} (see "
                    f"docs/PHILOSOPHY.md)"
                )
        for word in _TREATMENT:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden treatment "
                    f"phrase {word!r} (see docs/PHILOSOPHY.md)"
                )
        for word in _REGULATORY_OVERCLAIM:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden regulatory-"
                    f"overclaim phrase {word!r} (see "
                    f"docs/PHILOSOPHY.md)"
                )
        for word in _REASSURANCE:
            if word in low:
                raise ValueError(
                    f"alert text contains forbidden reassurance "
                    f"phrase {word!r} (see docs/PHILOSOPHY.md)"
                )
        for prefix in _IDENTIFIER_PREFIXES:
            if prefix in low:
                raise ValueError(
                    f"alert text appears to identify the patient "
                    f"({prefix!r}; see docs/PHILOSOPHY.md)"
                )


@dataclass
class PreTriageReport:
    """Per-submission output bundle."""

    patient_token: str
    assessment: PreTriageAssessment
    alerts: list[ClinicianAlert] = field(default_factory=list)
    readings: list[ChannelReading] = field(default_factory=list)
    reported_symptoms: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.patient_token:
            raise ValueError("patient_token must not be empty")

    def alerts_for_recommendation(
        self,
        recommendation: EscalationRecommendation,
    ) -> list[ClinicianAlert]:
        return [a for a in self.alerts if a.recommendation == recommendation]

    def as_text(self) -> str:
        """Short human-readable summary — for the demo."""
        lines = [
            f"Patient: {self.patient_token} · "
            f"{self.assessment.recommendation}",
        ]
        if self.reported_symptoms:
            lines.append(
                "  Reported symptoms: " + ", ".join(self.reported_symptoms)
            )
        if self.alerts:
            lines.append("  Alerts:")
            for a in self.alerts:
                lines.append(f"    [{a.channel} · {a.recommendation}] {a.text}")
                lines.append(f"      reasoning: {a.reasoning_trace}")
                lines.append("      alternatives:")
                for alt in a.alternative_explanations:
                    lines.append(f"        - ({alt.likelihood}) {alt.text}")
        else:
            lines.append(
                "  No urgent-review channels surfaced. "
                "Defaulting to schedule recommendation — the "
                "library observed a 1-2 minute window and "
                "flags nothing it considered urgent. The "
                "clinician reviews before deciding next steps."
            )
        return "\n".join(lines)


__all__ = [
    "AcousticSample",
    "AlternativeExplanation",
    "ChannelReading",
    "ClinicianAlert",
    "CoughSample",
    "PatientObservation",
    "PatientSelfReport",
    "PostureSample",
    "PreTriageAssessment",
    "PreTriageReport",
    "VitalsSample",
]
