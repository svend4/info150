"""String-literal enums for the veterinary-pet-assessment domain."""

from __future__ import annotations

from typing import Literal


# Species covered at the MVP. Each species has its own
# respiratory / cardiac band and its own pain-behavior list.
SpeciesKind = Literal["dog", "cat", "horse", "rabbit"]

# Triage recommendation surfaced to the vet (NOT the owner;
# owner-facing text uses friendlier wording). Three tiers:
# * can_wait       — no concerning signals; still log for
#                    routine checkup at next appointment.
# * routine_visit  — signals suggest the vet should see
#                    the pet within the next few days.
# * see_today      — strong signals; same-day in-person
#                    exam warranted.
#
# There is deliberately no "emergency" tier — an emergency
# determination requires physician-grade judgement the
# library does not have. The consumer app's UI adds an
# "if you believe this is a life-threatening emergency,
# call an emergency vet now" prompt above every output.
TriageRecommendation = Literal["can_wait", "routine_visit", "see_today"]

# Pain-behavior categories. Species-specific — dogs pant at
# rest when in pain; cats hide; horses weight-shift. The
# upstream classifier tags each observed behavior with one
# of these kinds.
PainBehaviorKind = Literal[
    "tucked_tail",
    "hunched_posture",
    "ear_position",
    "hiding",
    "weight_shifting",
    "panting_at_rest",
]

# Video-quality meta fed into the signature confidence
# calculation. Shaky / low-light / occluded clips get
# scored with wider uncertainty bands — when the library
# can't see clearly, it blends back toward the default
# routine_visit recommendation rather than making a
# confident call either way.
VideoQuality = Literal["good", "shaky", "low_light", "occluded"]


VALID_SPECIES: tuple[SpeciesKind, ...] = ("dog", "cat", "horse", "rabbit")
VALID_RECOMMENDATIONS: tuple[TriageRecommendation, ...] = (
    "can_wait",
    "routine_visit",
    "see_today",
)
VALID_PAIN_BEHAVIORS: tuple[PainBehaviorKind, ...] = (
    "tucked_tail",
    "hunched_posture",
    "ear_position",
    "hiding",
    "weight_shifting",
    "panting_at_rest",
)
VALID_VIDEO_QUALITIES: tuple[VideoQuality, ...] = (
    "good",
    "shaky",
    "low_light",
    "occluded",
)
