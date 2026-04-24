"""Core dataclasses for triage4-rescue.

Intentionally flat, frozen where sensible, no methods beyond
validation + a short human-readable `as_text` on the aggregate
types. Copy-fork of triage4-fit / triage4-farm patterns, with
disaster-response vocabulary and an expanded claims guard that
protects two boundaries — clinical AND operational-command.
See docs/PHILOSOPHY.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import (
    AgeGroup,
    CueKind,
    CueSeverity,
    StartTag,
    VALID_AGE_GROUPS,
    VALID_CUE_KINDS,
    VALID_SEVERITIES,
    VALID_TAGS,
)


# ---------------------------------------------------------------------------
# Raw observations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VitalSignsObservation:
    """A single stand-off vitals snapshot for one casualty.

    Captures the inputs START / JumpSTART evaluate. Any channel
    can be ``None`` if the sensor or check wasn't available —
    the protocol layer handles missing inputs explicitly
    (e.g. JumpSTART uses perfusion only when respiratory rate
    is equivocal).
    """

    # Can the casualty walk on command? START's first branch.
    # None = not yet assessed (e.g. casualty found trapped).
    can_walk: bool | None = None
    # Spontaneous respiratory rate in breaths/min. None = absent
    # (apneic). The protocol layer retries once after airway
    # repositioning before tagging deceased.
    respiratory_bpm: float | None = None
    # Did the responder reposition the airway and re-check
    # breathing? Required before tagging deceased under START.
    airway_repositioned: bool = False
    # Capillary refill time in seconds. > 2 s is abnormal in
    # adults (START perfusion check).
    capillary_refill_s: float | None = None
    # Radial pulse present? START uses it as an alternative to
    # cap-refill in poor lighting / cold conditions.
    radial_pulse: bool | None = None
    # Can the casualty follow simple commands? START's mental-
    # status branch. True / False / None (unresponsive =
    # False; unknown = None).
    follows_commands: bool | None = None

    def __post_init__(self) -> None:
        if self.respiratory_bpm is not None and not 0 <= self.respiratory_bpm <= 120:
            raise ValueError(
                f"respiratory_bpm out of plausible range: "
                f"{self.respiratory_bpm}"
            )
        if self.capillary_refill_s is not None and not 0 <= self.capillary_refill_s <= 20:
            raise ValueError(
                f"capillary_refill_s out of plausible range: "
                f"{self.capillary_refill_s}"
            )


@dataclass
class CivilianCasualty:
    """One person found in the disaster zone.

    Fields are the minimum the protocol layer needs. Anything
    downstream (family-reunification identifiers, hospital
    transfer records) belongs in a consumer application's data
    model, not here — keeping this layer small is what lets the
    claims guard on ``ResponderCue`` stay meaningful.
    """

    casualty_id: str
    # Approximate age in years. Needed for JumpSTART routing
    # (pediatric is < 8 yr). ``None`` means the algorithm
    # falls back to adult START with an advisory cue noting
    # the assumption.
    age_years: float | None = None
    # Observational sex is NOT recorded — the protocol doesn't
    # use it, and the less identifying data this layer holds
    # the lower the data-protection burden on the incident.
    vitals: VitalSignsObservation = field(default_factory=VitalSignsObservation)
    # Stand-off notes from the responder — never parsed as a
    # signal, only surfaced alongside the tag for context.
    responder_note: str | None = None

    def __post_init__(self) -> None:
        if not self.casualty_id:
            raise ValueError("casualty_id must not be empty")
        if self.age_years is not None and not 0 <= self.age_years <= 130:
            raise ValueError(
                f"age_years out of plausible range: {self.age_years}"
            )

    @property
    def age_group(self) -> AgeGroup:
        """JumpSTART applies to 1-7 yr. Adult START from 8 yr up.

        Infants (< 1 yr) are out of scope; the protocol layer
        refuses to tag them. Unknown age defaults to adult with
        a caution cue (see `start_protocol`).
        """
        if self.age_years is None:
            return "adult"
        if self.age_years < 8:
            return "pediatric"
        return "adult"


# ---------------------------------------------------------------------------
# Engine output
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TriageAssessment:
    """Outcome of one casualty's pass through START / JumpSTART.

    The ``tag`` is the authoritative output. ``reasoning`` is a
    short human-readable trace of which branches of the
    protocol fired, so a human reviewer can audit why a
    casualty landed in a given bucket. Audits are required in
    every civilian mass-casualty framework.
    """

    casualty_id: str
    tag: StartTag
    age_group: AgeGroup
    reasoning: str
    # Free-form flag for the secondary-review process: set to
    # True when the protocol hit an equivocal case and the
    # responder should return for a closer look after the
    # primary sweep completes.
    flag_for_secondary_review: bool = False

    def __post_init__(self) -> None:
        if self.tag not in VALID_TAGS:
            raise ValueError(
                f"tag must be one of {VALID_TAGS}, got {self.tag!r}"
            )
        if self.age_group not in VALID_AGE_GROUPS:
            raise ValueError(
                f"age_group must be one of {VALID_AGE_GROUPS}, "
                f"got {self.age_group!r}"
            )
        if not self.reasoning.strip():
            raise ValueError("reasoning must not be empty")


@dataclass(frozen=True)
class ResponderCue:
    """A single hint surfaced to the responder on their tablet.

    Support, not command. Clinical-adjacent, not clinical.

    Two forbidden-vocabulary lists enforced at construction
    time (see docs/PHILOSOPHY.md for rationale):

    - Clinical-practice words: ``diagnose``, ``prescribe``,
      ``administer``, ``dose``, ``confirmed deceased``,
      ``pronounced``.
    - Operational-command words: ``deploy``, ``dispatch``,
      ``assign team``, ``evacuate``, ``transport to``.

    A cue containing any of these raises ``ValueError`` before
    the object exists.
    """

    casualty_id: str
    kind: CueKind
    severity: CueSeverity
    text: str
    observed_value: float | None = None

    def __post_init__(self) -> None:
        if self.kind not in VALID_CUE_KINDS:
            raise ValueError(
                f"kind must be one of {VALID_CUE_KINDS}, got {self.kind!r}"
            )
        if self.severity not in VALID_SEVERITIES:
            raise ValueError(
                f"severity must be one of {VALID_SEVERITIES}, "
                f"got {self.severity!r}"
            )
        if not self.text.strip():
            raise ValueError("cue text must not be empty")
        _CLINICAL_FORBIDDEN = (
            "diagnose",
            "diagnosis",
            "prescribe",
            "administer",
            "dose ",
            "confirmed deceased",
            "confirmed dead",
            "pronounced",
            "cause of death",
        )
        _OPERATIONAL_FORBIDDEN = (
            "deploy",
            "dispatch",
            "assign team",
            "evacuate",
            "transport to",
            "establish perimeter",
            "clear the scene",
        )
        low = self.text.lower()
        for word in _CLINICAL_FORBIDDEN:
            if word in low:
                raise ValueError(
                    f"cue text contains forbidden clinical word {word!r} "
                    f"(clinical-adjacent posture; see docs/PHILOSOPHY.md)"
                )
        for word in _OPERATIONAL_FORBIDDEN:
            if word in low:
                raise ValueError(
                    f"cue text contains forbidden operational-command word "
                    f"{word!r} (advisory-only posture; "
                    f"see docs/PHILOSOPHY.md)"
                )


@dataclass
class IncidentReport:
    """START-tagged view of a single incident's first sweep.

    One per sweep, not one per incident — a large disaster runs
    multiple sweeps and the aggregator compares their outputs.
    This layer only knows about one sweep.
    """

    incident_id: str
    assessments: list[TriageAssessment] = field(default_factory=list)
    cues: list[ResponderCue] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.incident_id:
            raise ValueError("incident_id must not be empty")

    @property
    def casualty_count(self) -> int:
        return len(self.assessments)

    def assessments_with_tag(self, tag: StartTag) -> list[TriageAssessment]:
        return [a for a in self.assessments if a.tag == tag]

    def cues_at_severity(self, severity: CueSeverity) -> list[ResponderCue]:
        return [c for c in self.cues if c.severity == severity]

    def as_text(self) -> str:
        """Short human-readable summary — for the demo + tests."""
        counts = {
            tag: len(self.assessments_with_tag(tag))
            for tag in VALID_TAGS
        }
        lines = [
            f"Incident: {self.incident_id} · "
            f"{self.casualty_count} casualties tagged",
            f"  immediate: {counts['immediate']}   "
            f"delayed: {counts['delayed']}   "
            f"minor: {counts['minor']}   "
            f"deceased: {counts['deceased']}",
        ]
        flagged = [a for a in self.assessments if a.flag_for_secondary_review]
        if flagged:
            lines.append(
                f"  {len(flagged)} casualt"
                f"{'y' if len(flagged) == 1 else 'ies'} "
                "flagged for secondary review"
            )
        return "\n".join(lines)


__all__ = [
    "CivilianCasualty",
    "IncidentReport",
    "ResponderCue",
    "TriageAssessment",
    "VitalSignsObservation",
]
