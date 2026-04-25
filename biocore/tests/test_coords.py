"""Tests for biocore.coords."""

from __future__ import annotations

import pytest

from biocore.coords import DECIMAL_PAIR_RE, contains_decimal_coords


# ---------------------------------------------------------------------------
# Positive cases — these MUST be flagged as decimal coords
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "1.234, 5.678",
        "1.234,5.678",
        "-1.234, 5.678",
        "1.234, -5.678",
        "-1.234, -5.678",
        "1.234 5.678",
        "+1.234, +5.678",
        "60.5678, -5.4321",
        "Animal at 60.123, -5.678 today.",
        "URGENT: bird seen 1.23 -36.78 zone-A.",
        # Three-decimal precision, mixed whitespace.
        "60.123  ,  -5.678",
    ],
)
def test_contains_decimal_coords_positive(text: str):
    assert contains_decimal_coords(text)
    assert DECIMAL_PAIR_RE.search(text) is not None


# ---------------------------------------------------------------------------
# Negative cases — these should NOT be flagged
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "",
        "grid-A7",
        "zone-central",
        "subgrid-3.4a",          # single decimal, not a pair
        "pen-A1",
        "version 1.0.0",         # multiple decimals but not lat/lon shape
        "1.2 5.6",               # only one decimal each
        "1, 5",                  # no decimals
        "1.234",                 # single decimal alone
        "ratio 1.5:1.5",         # one-decimal precision
        "elephant at grid-A7",
        "the temperature was 36.7 degrees",  # single decimal
        "approximately 1.5 m/s walking speed",
    ],
)
def test_contains_decimal_coords_negative(text: str):
    assert not contains_decimal_coords(text)
    assert DECIMAL_PAIR_RE.search(text) is None


# ---------------------------------------------------------------------------
# DECIMAL_PAIR_RE direct exposure
# ---------------------------------------------------------------------------


def test_decimal_pair_re_is_compiled_pattern():
    """Public API contract — the regex is exposed as a
    compiled pattern, not just via the predicate. Used by
    triage4-wild / triage4-bird / triage4-fish for
    additional matching contexts."""
    import re
    assert isinstance(DECIMAL_PAIR_RE, re.Pattern)


def test_decimal_pair_re_matches_at_any_offset():
    text = "alert text some content 1.234, -5.678 trailing"
    m = DECIMAL_PAIR_RE.search(text)
    assert m is not None
    assert "1.234" in m.group(0)
