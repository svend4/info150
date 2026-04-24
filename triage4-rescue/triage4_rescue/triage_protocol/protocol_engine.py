"""StartProtocolEngine — dispatch layer + incident aggregation.

Sibling of triage4's RapidTriageEngine, triage4-fit's
RapidFormEngine, and triage4-farm's WelfareCheckEngine. Takes a
list of CivilianCasualty and produces an IncidentReport with
one TriageAssessment + zero-or-more ResponderCue per casualty.

Dispatch rules:
- casualty.age_years is None → adult START with an advisory cue
  noting the assumption.
- casualty.age_years in [1, 8) → JumpSTART.
- casualty.age_years in [8, ...] → adult START.
- casualty.age_years < 1 → StartProtocolError. Infant triage is
  out of scope for this library.

Observation-only, advisory-only. No operational commands. No
clinical diagnoses. See docs/PHILOSOPHY.md.
"""

from __future__ import annotations

from ..core.models import (
    CivilianCasualty,
    IncidentReport,
    ResponderCue,
    TriageAssessment,
)
from .jumpstart_pediatric import tag_pediatric
from .start_protocol import StartProtocolError, tag_adult


class StartProtocolEngine:
    """Run START / JumpSTART across a list of casualties.

    Stateless — a new engine instance per incident is fine, and
    cheap.
    """

    def review(
        self,
        incident_id: str,
        casualties: list[CivilianCasualty],
    ) -> IncidentReport:
        if not casualties:
            return IncidentReport(
                incident_id=incident_id,
                assessments=[],
                cues=[
                    ResponderCue(
                        casualty_id="-",
                        kind="secondary_review",
                        severity="advisory",
                        text=(
                            "No casualties recorded on this sweep. "
                            "Responder: confirm scene coverage before "
                            "moving to the next sector."
                        ),
                    )
                ],
            )

        assessments: list[TriageAssessment] = []
        cues: list[ResponderCue] = []
        for casualty in casualties:
            a, cs = self._tag_one(casualty)
            assessments.append(a)
            cues.extend(cs)
        return IncidentReport(
            incident_id=incident_id,
            assessments=assessments,
            cues=cues,
        )

    # -- internals ------------------------------------------------------

    def _tag_one(
        self,
        casualty: CivilianCasualty,
    ) -> tuple[TriageAssessment, list[ResponderCue]]:
        if casualty.age_years is not None and casualty.age_years < 1:
            raise StartProtocolError(
                f"casualty {casualty.casualty_id!r} is an infant "
                f"({casualty.age_years} yr). Infant triage is outside "
                "START / JumpSTART scope — use PTT + paediatric first "
                "responder."
            )
        if casualty.age_group == "pediatric":
            return tag_pediatric(casualty)
        # Adult path.
        if casualty.age_years is None:
            assessment, cues = tag_adult(casualty)
            # Prepend an advisory cue noting the assumption.
            cues = [
                ResponderCue(
                    casualty_id=casualty.casualty_id,
                    kind="secondary_review",
                    severity="advisory",
                    text=(
                        f"Casualty {casualty.casualty_id} age unknown. "
                        "Defaulted to adult START. Responder: confirm "
                        "age during secondary review."
                    ),
                ),
                *cues,
            ]
            return assessment, cues
        return tag_adult(casualty)
