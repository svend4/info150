"""String-literal enums for the civilian-disaster-response domain.

Same `Literal[...]` + plain strings pattern as the other
siblings. START tag names are the field-standard colour-coded
categories used on civilian triage tape: Immediate (red),
Delayed (yellow), Minor (green), Deceased (black).
"""

from __future__ import annotations

from typing import Literal


# Canonical 1983 START tag set. Same wording in JumpSTART for
# pediatric casualties — the algorithm differs but the tag
# alphabet is shared.
StartTag = Literal["immediate", "delayed", "minor", "deceased"]

# Selects the triage algorithm branch. "adult" → START,
# "pediatric" → JumpSTART (1-7 years old). Infants (< 1 yr)
# are explicitly out of scope; the protocol layer refuses to
# tag them rather than produce a misleading result.
AgeGroup = Literal["adult", "pediatric"]

# What a responder cue is about. Parallels the CueKind enums
# in the fit / farm siblings but with disaster-response
# channels.
CueKind = Literal[
    "ambulation",
    "breathing",
    "perfusion",
    "mental_status",
    "secondary_review",
]

# Cue severity — drives UI colour on the responder tablet.
CueSeverity = Literal["info", "advisory", "flag"]


VALID_TAGS: tuple[StartTag, ...] = (
    "immediate",
    "delayed",
    "minor",
    "deceased",
)
VALID_AGE_GROUPS: tuple[AgeGroup, ...] = ("adult", "pediatric")
VALID_CUE_KINDS: tuple[CueKind, ...] = (
    "ambulation",
    "breathing",
    "perfusion",
    "mental_status",
    "secondary_review",
)
VALID_SEVERITIES: tuple[CueSeverity, ...] = ("info", "advisory", "flag")
