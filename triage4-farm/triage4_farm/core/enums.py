"""String-literal enums for the livestock welfare domain.

Follows triage4's `Literal[...]` + plain strings pattern, same
as triage4-fit. No `enum.Enum` — lightweight serialisation and
comparable in tests without boilerplate.
"""

from __future__ import annotations

from typing import Literal


# Species the welfare engine is tuned for. Each species has its
# own signature bands (respiratory rate, typical gait cadence,
# core-temp proxy). Extending the list means extending
# species_profiles.
Species = Literal["dairy_cow", "pig", "chicken"]

# Per-animal welfare flag. NOT a triage priority — the system
# is observation-only, so the "urgent" tier still means
# "farmer should call the vet", not "act now".
WelfareFlag = Literal["well", "concern", "urgent"]

# What the alert is about — corresponds to the signature
# channels the welfare engine watches.
AlertKind = Literal["lameness", "respiratory", "thermal", "behaviour"]


VALID_SPECIES: tuple[Species, ...] = ("dairy_cow", "pig", "chicken")
VALID_FLAGS: tuple[WelfareFlag, ...] = ("well", "concern", "urgent")
VALID_ALERT_KINDS: tuple[AlertKind, ...] = (
    "lameness",
    "respiratory",
    "thermal",
    "behaviour",
)
