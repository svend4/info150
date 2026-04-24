"""JumpSTART pediatric algorithm (Romig 1995).

Used for casualties 1-7 years old. Differs from adult START on
three points relevant to this library:

1. Respiratory-rate thresholds: 15-45 /min is the normal band
   (vs. <30 for adults).
2. Apneic child with a palpable pulse gets five rescue breaths
   before being tagged — a clinical act the library does not
   perform but MUST flag to the responder. If the child has no
   pulse, they are tagged deceased immediately (skipping the
   rescue-breath step).
3. Perfusion is not the second branch — JumpSTART goes straight
   to an "AVPU" mental-status check after a normal respiratory
   read. AVPU stands for Alert / Verbal / Painful / Unresponsive.
   The library approximates this with ``follows_commands``: True
   → Alert (delayed); False → Painful-or-Unresponsive (immediate).

Infants (< 1 yr) are explicitly out of scope — ``StartProtocolError``
is raised from the dispatch layer rather than return a misleading tag.
"""

from __future__ import annotations

from ..core.models import (
    CivilianCasualty,
    ResponderCue,
    TriageAssessment,
    VitalSignsObservation,
)
from ..signatures.ambulation_check import can_ambulate
from ..signatures.breathing_check import classify_breathing
from .start_protocol import _finalise, _rr_text


def tag_pediatric(
    casualty: CivilianCasualty,
) -> tuple[TriageAssessment, list[ResponderCue]]:
    """Run the JumpSTART algorithm on one pediatric casualty."""
    cid = casualty.casualty_id
    vitals = casualty.vitals
    cues: list[ResponderCue] = []

    # Step 1: ambulation. JumpSTART additionally tags non-
    # ambulatory children who are otherwise well-appearing as
    # "minor" after a responder eyeballs them — that sub-check
    # relies on clinical judgment the library doesn't have, so
    # we stop short at the ambulation question.
    amb = can_ambulate(vitals)
    if amb is True:
        cues.append(ResponderCue(
            casualty_id=cid,
            kind="ambulation",
            severity="info",
            text=(
                f"Pediatric casualty {cid} is walking. "
                "JumpSTART minor. Direct to walking-wounded "
                "collection point."
            ),
        ))
        return _finalise(cid, "minor", "pediatric",
                         "ambulatory → JumpSTART minor", cues,
                         flag=False)

    # Step 2: respiratory. JumpSTART bands differ from adult.
    resp = classify_breathing(vitals, "pediatric")
    if resp == "apneic":
        # JumpSTART: responder checks pulse FIRST. Pulse present
        # → 5 rescue breaths (clinical, responder acts), then re-
        # check. Pulse absent → deceased. The library can't give
        # rescue breaths so it surfaces a flag cue and returns a
        # delayed-flagged assessment — the engine should be re-
        # called after the responder's physical intervention.
        if vitals.radial_pulse is False:
            cues.append(ResponderCue(
                casualty_id=cid,
                kind="breathing",
                severity="flag",
                text=(
                    f"Pediatric casualty {cid} apneic with no "
                    "palpable pulse. JumpSTART deceased (tag). "
                    "Mark for secondary review."
                ),
            ))
            return _finalise(
                cid, "deceased", "pediatric",
                "pediatric apneic, pulse absent → JumpSTART deceased",
                cues, flag=True,
            )
        cues.append(ResponderCue(
            casualty_id=cid,
            kind="breathing",
            severity="flag",
            text=(
                f"Pediatric casualty {cid} apneic with palpable "
                "pulse. Responder: give 5 rescue breaths per "
                "JumpSTART and re-observe before tagging."
            ),
        ))
        return _finalise(
            cid, "delayed", "pediatric",
            "pediatric apneic, pulse present → JumpSTART rescue-"
            "breath step required before final tag",
            cues, flag=True,
        )
    if resp == "apneic_post_reposition":
        # After responder's rescue-breath attempt, still apneic →
        # deceased under JumpSTART.
        cues.append(ResponderCue(
            casualty_id=cid,
            kind="breathing",
            severity="flag",
            text=(
                f"Pediatric casualty {cid} remains apneic after "
                "rescue breaths. JumpSTART deceased (tag). Mark "
                "for secondary review."
            ),
        ))
        return _finalise(
            cid, "deceased", "pediatric",
            "pediatric apneic after rescue breaths → JumpSTART deceased",
            cues, flag=True,
        )
    if resp == "abnormal":
        cues.append(ResponderCue(
            casualty_id=cid,
            kind="breathing",
            severity="flag",
            text=(
                f"Pediatric casualty {cid} respiratory rate "
                f"abnormal ({_rr_text(vitals)}). JumpSTART immediate."
            ),
            observed_value=vitals.respiratory_bpm,
        ))
        return _finalise(
            cid, "immediate", "pediatric",
            f"respiratory rate abnormal ({_rr_text(vitals)}) → "
            "JumpSTART immediate",
            cues, flag=False,
        )

    # Step 3: AVPU — approximated by follows_commands.
    if vitals.follows_commands is False:
        cues.append(ResponderCue(
            casualty_id=cid,
            kind="mental_status",
            severity="flag",
            text=(
                f"Pediatric casualty {cid} unresponsive to command "
                "(AVPU: Painful or Unresponsive). JumpSTART immediate."
            ),
        ))
        return _finalise(
            cid, "immediate", "pediatric",
            "AVPU P/U → JumpSTART immediate",
            cues, flag=False,
        )

    # Cleared every branch — delayed.
    flagged = vitals.follows_commands is None
    reasoning = "respiratory normal, AVPU alert → JumpSTART delayed"
    if flagged:
        reasoning = (
            "respiratory normal, AVPU not confirmed → JumpSTART "
            "delayed (flagged)"
        )
    cues.append(ResponderCue(
        casualty_id=cid,
        kind="secondary_review" if flagged else "mental_status",
        severity="advisory" if flagged else "info",
        text=(
            f"Pediatric casualty {cid} clears acute branches. "
            "JumpSTART delayed."
            + ("  Flag for secondary review — AVPU not confirmed."
               if flagged else "")
        ),
    ))
    return _finalise(cid, "delayed", "pediatric", reasoning, cues,
                     flag=flagged)


# Silence unused-import if mypy trims.
_ = VitalSignsObservation
