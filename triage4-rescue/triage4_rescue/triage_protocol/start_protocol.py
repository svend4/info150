"""Canonical 1983 START algorithm for adult casualties.

Flow (paraphrased from the NDMS START card):

1. Ambulation check — can walk on command → MINOR (green).
2. Respiratory check:
   - Apneic + airway not yet repositioned → try repositioning
     (responder action, out of scope) and re-observe.
   - Apneic after reposition → DECEASED (black).
   - RR abnormal (>30 or <8 adult) → IMMEDIATE (red).
3. Perfusion check:
   - Radial pulse absent OR cap-refill > 2 s → IMMEDIATE.
4. Mental-status check:
   - Can follow simple commands → DELAYED (yellow).
   - Cannot → IMMEDIATE.

The function is deterministic and rule-based. No thresholds to
tune at this layer — tuning happens in signatures/. Returns a
TriageAssessment plus a list of ResponderCue objects.

See docs/PHILOSOPHY.md for why the DECEASED tag is a resource-
allocation decision, not a clinical death pronouncement.
"""

from __future__ import annotations

from ..core.enums import StartTag
from ..core.models import (
    CivilianCasualty,
    ResponderCue,
    TriageAssessment,
    VitalSignsObservation,
)
from ..signatures.ambulation_check import can_ambulate
from ..signatures.breathing_check import classify_breathing
from ..signatures.perfusion_check import classify_perfusion


class StartProtocolError(ValueError):
    """Raised when a casualty is outside START's validated scope.

    Infants (< 1 yr) fall here rather than get a mis-tagged
    assessment. PTT (Pediatric Triage Tape) and a trained
    paediatric first responder are the correct path.
    """


def tag_adult(
    casualty: CivilianCasualty,
) -> tuple[TriageAssessment, list[ResponderCue]]:
    """Run the 1983 adult START algorithm on one casualty.

    Returns ``(assessment, cues)``. Cues are ordered by when
    they fired during the protocol — useful for the responder's
    secondary review.
    """
    cid = casualty.casualty_id
    vitals = casualty.vitals
    cues: list[ResponderCue] = []

    # Step 1: ambulation.
    amb = can_ambulate(vitals)
    if amb is True:
        cues.append(ResponderCue(
            casualty_id=cid,
            kind="ambulation",
            severity="info",
            text=(
                f"Casualty {cid} is walking. START minor. "
                "Direct to walking-wounded collection point."
            ),
        ))
        return _finalise(cid, "minor", "adult",
                         "ambulatory → START minor", cues,
                         flag=False)

    # Step 2: respiratory.
    resp = classify_breathing(vitals, "adult")
    if resp == "apneic":
        # Responder must reposition airway and re-check. This
        # library can't do that — it surfaces an advisory cue
        # and flags the casualty for secondary review with a
        # delayed tag placeholder. In practice the engine is
        # called twice per apneic casualty: once pre-reposition
        # (flag), once post (resolves to immediate or deceased).
        cues.append(ResponderCue(
            casualty_id=cid,
            kind="breathing",
            severity="flag",
            text=(
                f"Casualty {cid} apneic on first check. "
                "Responder: reposition airway and re-observe "
                "before tagging."
            ),
        ))
        return _finalise(
            cid, "delayed", "adult",
            "apneic, airway reposition required before final tag",
            cues, flag=True,
        )
    if resp == "apneic_post_reposition":
        cues.append(ResponderCue(
            casualty_id=cid,
            kind="breathing",
            severity="flag",
            text=(
                f"Casualty {cid} remains apneic after airway "
                "reposition. START deceased (tag). Mark for "
                "secondary review."
            ),
        ))
        return _finalise(
            cid, "deceased", "adult",
            "apneic after airway reposition → START deceased",
            cues, flag=True,
        )
    if resp == "abnormal":
        cues.append(ResponderCue(
            casualty_id=cid,
            kind="breathing",
            severity="flag",
            text=(
                f"Casualty {cid} respiratory rate abnormal "
                f"({_rr_text(vitals)}). START immediate."
            ),
            observed_value=vitals.respiratory_bpm,
        ))
        return _finalise(
            cid, "immediate", "adult",
            f"respiratory rate abnormal ({_rr_text(vitals)}) → "
            "START immediate",
            cues, flag=False,
        )

    # Step 3: perfusion.
    perf = classify_perfusion(vitals)
    if perf == "poor":
        cues.append(ResponderCue(
            casualty_id=cid,
            kind="perfusion",
            severity="flag",
            text=(
                f"Casualty {cid} perfusion inadequate "
                f"({_perfusion_text(vitals)}). START immediate."
            ),
        ))
        return _finalise(
            cid, "immediate", "adult",
            f"perfusion poor ({_perfusion_text(vitals)}) → "
            "START immediate",
            cues, flag=False,
        )

    # Step 4: mental status.
    if vitals.follows_commands is False:
        cues.append(ResponderCue(
            casualty_id=cid,
            kind="mental_status",
            severity="flag",
            text=(
                f"Casualty {cid} does not follow simple commands. "
                "START immediate."
            ),
        ))
        return _finalise(
            cid, "immediate", "adult",
            "fails mental-status command check → START immediate",
            cues, flag=False,
        )

    # All branches cleared — delayed tag.
    reasoning_bits = ["respiratory normal"]
    if perf == "reassuring":
        reasoning_bits.append("perfusion reassuring")
    else:
        reasoning_bits.append("perfusion unknown")
    if vitals.follows_commands is True:
        reasoning_bits.append("follows commands")
    else:
        reasoning_bits.append("mental status not confirmed")
    reasoning = ", ".join(reasoning_bits) + " → START delayed"
    flagged = perf == "unknown" or vitals.follows_commands is None
    cues.append(ResponderCue(
        casualty_id=cid,
        kind="secondary_review" if flagged else "mental_status",
        severity="advisory" if flagged else "info",
        text=(
            f"Casualty {cid} checks clear on all acute branches. "
            "START delayed."
            + ("  Flag for secondary review — some channels "
               "unassessed." if flagged else "")
        ),
    ))
    return _finalise(cid, "delayed", "adult", reasoning, cues, flag=flagged)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _finalise(
    casualty_id: str,
    tag: StartTag,
    age_group: str,
    reasoning: str,
    cues: list[ResponderCue],
    flag: bool,
) -> tuple[TriageAssessment, list[ResponderCue]]:
    assessment = TriageAssessment(
        casualty_id=casualty_id,
        tag=tag,
        age_group=age_group,  # type: ignore[arg-type]
        reasoning=reasoning,
        flag_for_secondary_review=flag,
    )
    return assessment, cues


def _rr_text(vitals: VitalSignsObservation) -> str:
    rr = vitals.respiratory_bpm
    if rr is None:
        return "rate unknown"
    return f"{rr:.0f} /min"


def _perfusion_text(vitals: VitalSignsObservation) -> str:
    if vitals.radial_pulse is False:
        return "radial pulse absent"
    if vitals.capillary_refill_s is not None:
        return f"cap-refill {vitals.capillary_refill_s:.1f}s"
    return "perfusion marginal"
