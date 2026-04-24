"""Respiratory-rate branch of START / JumpSTART.

START adult thresholds (1983, NDMS-authored):
- RR > 30 /min            → immediate
- RR < 30 /min, spontaneous → go to perfusion check

JumpSTART pediatric thresholds (Romig 1995):
- RR < 15 or > 45 /min    → immediate
- 15-45 /min, spontaneous → go to perfusion check

Apneic casualties: both algorithms require an airway-reposition
retry once. Still apneic after reposition = deceased tag
(resource-allocation decision, not a clinical death
pronouncement — see docs/PHILOSOPHY.md). JumpSTART extends
the check by trying a pulse-check first: an apneic child with
a pulse gets 5 rescue breaths before being tagged, but that
clinical act is out of scope for this library.

This module returns a compact string classification that
``start_protocol`` turns into a tag + reasoning trace.
"""

from __future__ import annotations

from typing import Literal

from ..core.enums import AgeGroup
from ..core.models import VitalSignsObservation


RespiratoryStatus = Literal[
    "apneic",             # no spontaneous breathing, reposition not yet tried
    "apneic_post_reposition",
    "abnormal",           # too fast or too slow for the age group
    "normal",             # within the age-group band
]


# Adult: anything > 30 bpm is tagged immediate under START. The
# lower bound isn't protocol-defined (START doesn't tag bradypnea
# alone), but a casualty breathing < 8 bpm after a disaster is an
# airway / head-injury concern the responder should at least be
# flagged about — we return "abnormal" and the engine treats it
# as immediate.
_ADULT_RR_UPPER = 30.0
_ADULT_RR_LOWER = 8.0

# JumpSTART: 15-45 is the normal band.
_PED_RR_LOWER = 15.0
_PED_RR_UPPER = 45.0


def classify_breathing(
    vitals: VitalSignsObservation,
    age_group: AgeGroup,
) -> RespiratoryStatus:
    """Return a compact status that the protocol layer consumes."""
    rr = vitals.respiratory_bpm
    if rr is None or rr == 0:
        if vitals.airway_repositioned:
            return "apneic_post_reposition"
        return "apneic"

    if age_group == "adult":
        if rr > _ADULT_RR_UPPER or rr < _ADULT_RR_LOWER:
            return "abnormal"
        return "normal"
    # pediatric (JumpSTART)
    if rr > _PED_RR_UPPER or rr < _PED_RR_LOWER:
        return "abnormal"
    return "normal"
