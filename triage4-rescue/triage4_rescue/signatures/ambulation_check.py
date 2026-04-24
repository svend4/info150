"""Ambulation check — the very first branch of START.

START's first sorting question is almost trivial: "can the
casualty walk on command?" Anyone who can walk is tagged
``minor`` and sent to the walking-wounded collection point.
That clears the low-acuity casualties out of the responder's
attention in seconds.

This module is a pure function over the vitals dataclass. No
thresholds to tune — the check is binary. Kept as its own
module so the engine code reads as a sequence of named
protocol branches rather than a single long function.
"""

from __future__ import annotations

from ..core.models import VitalSignsObservation


def can_ambulate(vitals: VitalSignsObservation) -> bool | None:
    """Return True / False if the ambulation question was
    answered, None if it wasn't asked yet.

    The protocol layer treats ``None`` as "move on to the
    respiratory branch" — a casualty who wasn't assessed for
    ambulation (because they were found trapped under debris)
    still gets the full algorithm.
    """
    return vitals.can_walk
