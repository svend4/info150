"""Tests for portal.coords."""

from __future__ import annotations

import pytest

from portal.coords import (
    ANIMAL_MANAGED,
    ANIMAL_WILD,
    ENVIRONMENTAL,
    INDUSTRIAL_WORKPLACE,
    SIBLING_COORDS,
    axes_set,
    coord_for,
    hamming,
)


# ---------------------------------------------------------------------------
# Bit positions are stable (don't accidentally renumber)
# ---------------------------------------------------------------------------


def test_bit_positions_stable() -> None:
    assert ANIMAL_WILD == 1
    assert ANIMAL_MANAGED == 2
    assert ENVIRONMENTAL == 32


def test_six_distinct_axes() -> None:
    """Six bits — each axis sets exactly one."""
    from portal.coords import ALL_AXES
    bits = [bit for _, bit in ALL_AXES]
    assert len(bits) == 6
    assert sum(bits) == (1 << 6) - 1  # 1+2+4+8+16+32 = 63


# ---------------------------------------------------------------------------
# hamming
# ---------------------------------------------------------------------------


def test_hamming_zero_for_identical() -> None:
    assert hamming(ANIMAL_WILD, ANIMAL_WILD) == 0


def test_hamming_one_for_one_bit_difference() -> None:
    a = ANIMAL_WILD | ENVIRONMENTAL
    b = ANIMAL_WILD                # missing env
    assert hamming(a, b) == 1


def test_hamming_three_for_three_bit_difference() -> None:
    a = ANIMAL_WILD | ENVIRONMENTAL                          # 33
    b = ANIMAL_MANAGED | INDUSTRIAL_WORKPLACE | ENVIRONMENTAL  # 50
    # XOR: 33 ^ 50 = 19 = 0b010011 → 3 bits set
    assert hamming(a, b) == 3


def test_hamming_symmetric() -> None:
    a = ANIMAL_WILD | ENVIRONMENTAL
    b = ANIMAL_MANAGED | INDUSTRIAL_WORKPLACE | ENVIRONMENTAL
    assert hamming(a, b) == hamming(b, a)


def test_hamming_masks_above_six_bits() -> None:
    """Bits above bit 5 must NOT count."""
    polluted = (1 << 7) | ANIMAL_WILD
    clean = ANIMAL_WILD
    assert hamming(polluted, clean) == 0


# ---------------------------------------------------------------------------
# coord_for
# ---------------------------------------------------------------------------


def test_coord_for_known_pilot_siblings() -> None:
    assert coord_for("triage4-wild") == ANIMAL_WILD | ENVIRONMENTAL
    assert coord_for("triage4-bird") == ANIMAL_WILD | ENVIRONMENTAL
    assert coord_for("triage4-fish") == (
        ANIMAL_MANAGED | INDUSTRIAL_WORKPLACE | ENVIRONMENTAL
    )


def test_coord_for_unknown_raises() -> None:
    with pytest.raises(KeyError, match="triage4-farm"):
        coord_for("triage4-farm")


def test_pilot_wild_and_bird_are_neighbours() -> None:
    """The architectural promise: bird + wild are
    domain-adjacent (Hamming 0 in this initial assignment)."""
    assert hamming(coord_for("triage4-wild"), coord_for("triage4-bird")) == 0


def test_pilot_fish_is_three_steps_from_wild() -> None:
    """Aquaculture pen ≠ wildlife reserve."""
    assert hamming(coord_for("triage4-wild"), coord_for("triage4-fish")) == 3


# ---------------------------------------------------------------------------
# axes_set
# ---------------------------------------------------------------------------


def test_axes_set_for_pilot_wild() -> None:
    assert axes_set(coord_for("triage4-wild")) == (
        "animal_wild", "environmental",
    )


def test_axes_set_for_pilot_fish_orders_canonically() -> None:
    """Bit order: wild, managed, ind_individual, ind_collective,
    workplace, environmental."""
    assert axes_set(coord_for("triage4-fish")) == (
        "animal_managed", "industrial_workplace", "environmental",
    )


def test_axes_set_empty_for_zero() -> None:
    assert axes_set(0) == ()


def test_sibling_coords_initial_pilots_only() -> None:
    """The initial registry contains only the three pilot siblings.
    Other siblings opt in voluntarily by adding themselves later."""
    assert set(SIBLING_COORDS.keys()) == {
        "triage4-wild", "triage4-bird", "triage4-fish",
    }
