"""Perfusion branch of START.

Protocol-standard choice: radial pulse OR capillary refill,
whichever is usable given the scene conditions. START treats
them as equivalent checks for shock risk — the ``poor`` result
from either one escalates the casualty to ``immediate``.

Adult START:
- radial pulse absent       → immediate
- cap-refill > 2 s          → immediate
- both reassuring           → go to mental-status check

JumpSTART doesn't use perfusion the same way for pediatrics —
it skips straight to an "AVPU" mental-status check after a
normal respiratory read. Pediatric casualties route through
``classify_perfusion`` only as a fallback when the adult
branch is explicitly requested.
"""

from __future__ import annotations

from typing import Literal

from ..core.models import VitalSignsObservation


PerfusionStatus = Literal[
    "poor",         # radial pulse absent or cap-refill > 2 s
    "reassuring",   # both reassuring (or one reassuring, other unknown)
    "unknown",      # no perfusion channels were assessable
]


_ADULT_CAPILLARY_REFILL_CAP_S = 2.0


def classify_perfusion(vitals: VitalSignsObservation) -> PerfusionStatus:
    """Return a compact perfusion status for the protocol layer."""
    pulse = vitals.radial_pulse
    refill = vitals.capillary_refill_s

    if pulse is False:
        return "poor"
    if refill is not None and refill > _ADULT_CAPILLARY_REFILL_CAP_S:
        return "poor"

    if pulse is True:
        return "reassuring"
    if refill is not None and refill <= _ADULT_CAPILLARY_REFILL_CAP_S:
        return "reassuring"
    return "unknown"
