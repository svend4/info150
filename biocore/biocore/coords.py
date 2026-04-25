"""Decimal-coordinate detection for the field-security boundary.

triage4-wild, triage4-bird, and triage4-fish all enforce the
same field-security pattern: any text field that contains
plaintext decimal-degree coordinate pairs is rejected at
construction time. Three siblings, one regex — extraction
threshold met.

The regex deliberately matches obvious decimal-degree
coordinate pairs (lat, lon with at least 2 decimal digits
each) without false-positive matching on single decimals
like grid IDs (``grid-3.4`` should pass; ``1.234, 5.678``
should not).
"""

from __future__ import annotations

import re


# Two floats with 2+ decimal digits each, separated by a
# comma or whitespace. Matches ``1.23, 5.67``,
# ``1.234 -36.789``, ``-1.234,5.678``. Does NOT match
# ``grid-3.4`` (only one float), ``1, 5`` (no decimals),
# or ``1.2 5.6`` (only one decimal each).
DECIMAL_PAIR_RE: re.Pattern[str] = re.compile(
    r"[-+]?\d+\.\d{2,}\s*[,\s]\s*[-+]?\d+\.\d{2,}"
)


def contains_decimal_coords(text: str) -> bool:
    """Return True if ``text`` contains a decimal-coordinate pair.

    Used by ``LocationHandle`` / ``RangerAlert`` /
    ``OrnithologistAlert`` / ``FarmManagerAlert`` /
    ``PenObservation`` constructors to enforce the field-
    security boundary.
    """
    return DECIMAL_PAIR_RE.search(text) is not None


__all__ = ["DECIMAL_PAIR_RE", "contains_decimal_coords"]
