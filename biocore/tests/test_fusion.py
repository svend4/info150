"""Tests for biocore.fusion."""

from __future__ import annotations

import pytest

from biocore.fusion import (
    apply_channel_floor,
    normalise_weights,
    weighted_overall,
)


# ---------------------------------------------------------------------------
# normalise_weights
# ---------------------------------------------------------------------------


def test_normalise_already_summing_to_one():
    out = normalise_weights({"a": 0.4, "b": 0.6})
    assert out == {"a": 0.4, "b": 0.6}


def test_normalise_summing_to_other():
    out = normalise_weights({"a": 1.0, "b": 1.0})
    assert out == {"a": 0.5, "b": 0.5}


def test_normalise_summing_to_other_three_channels():
    out = normalise_weights({"a": 2.0, "b": 1.0, "c": 1.0})
    assert out["a"] == pytest.approx(0.5)
    assert out["b"] == pytest.approx(0.25)
    assert out["c"] == pytest.approx(0.25)


def test_normalise_returns_copy_not_mutation():
    weights = {"a": 1.0, "b": 1.0}
    out = normalise_weights(weights)
    out["a"] = 99.0
    assert weights["a"] == 1.0


def test_normalise_rejects_empty():
    with pytest.raises(ValueError, match="must not be empty"):
        normalise_weights({})


def test_normalise_rejects_zero_total():
    with pytest.raises(ValueError, match="must be positive"):
        normalise_weights({"a": 0.0, "b": 0.0})


def test_normalise_rejects_negative_total():
    with pytest.raises(ValueError, match="must be positive"):
        normalise_weights({"a": -1.0, "b": -2.0})


def test_normalise_permits_one_zero_when_total_positive():
    out = normalise_weights({"a": 0.0, "b": 1.0})
    assert out == {"a": 0.0, "b": 1.0}


# ---------------------------------------------------------------------------
# weighted_overall
# ---------------------------------------------------------------------------


def test_weighted_overall_simple():
    overall = weighted_overall(
        weights={"a": 0.5, "b": 0.5},
        channel_scores={"a": 1.0, "b": 0.0},
    )
    assert overall == 0.5


def test_weighted_overall_all_safe():
    overall = weighted_overall(
        weights={"a": 0.4, "b": 0.6},
        channel_scores={"a": 1.0, "b": 1.0},
    )
    assert overall == 1.0


def test_weighted_overall_all_urgent():
    overall = weighted_overall(
        weights={"a": 0.4, "b": 0.6},
        channel_scores={"a": 0.0, "b": 0.0},
    )
    assert overall == 0.0


def test_weighted_overall_clamps_to_unit():
    """Floating-point error or unnormalised weights might
    push overall slightly outside [0, 1]. Clamp."""
    overall = weighted_overall(
        weights={"a": 1.5, "b": 0.0},
        channel_scores={"a": 1.0, "b": 0.0},
    )
    assert overall == 1.0


def test_weighted_overall_missing_channel_key_raises():
    with pytest.raises(KeyError, match="channel_scores"):
        weighted_overall(
            weights={"a": 0.5, "b": 0.5},
            channel_scores={"a": 1.0},  # missing 'b'
        )


def test_weighted_overall_extra_channel_keys_ignored():
    """If channel_scores contains keys not in weights, they
    are simply ignored (signature pipeline may produce
    auxiliary scores the engine doesn't fuse)."""
    overall = weighted_overall(
        weights={"a": 1.0},
        channel_scores={"a": 0.6, "b": 0.0, "c": 0.1},
    )
    assert overall == 0.6


# ---------------------------------------------------------------------------
# apply_channel_floor
# ---------------------------------------------------------------------------


def test_apply_floor_no_channel_below_returns_unchanged():
    overall = apply_channel_floor(
        overall=0.85,
        channel_scores={"a": 0.7, "b": 0.9},
        urgent_threshold=0.45,
        overall_floor=0.55,
    )
    assert overall == 0.85


def test_apply_floor_one_channel_below_forces_below_floor():
    overall = apply_channel_floor(
        overall=0.85,
        channel_scores={"a": 0.30, "b": 0.9},
        urgent_threshold=0.45,
        overall_floor=0.55,
    )
    # overall floored at 0.55 - epsilon (default 0.01) = 0.54.
    assert overall == 0.54


def test_apply_floor_already_below_floor_unchanged():
    """If overall is already well below the floor, the
    helper does NOT raise it back up — the floor is
    one-sided (it caps overall, never raises it)."""
    overall = apply_channel_floor(
        overall=0.20,
        channel_scores={"a": 0.30, "b": 0.9},
        urgent_threshold=0.45,
        overall_floor=0.55,
    )
    # Already below 0.54 → returned as-is.
    assert overall == 0.20


def test_apply_floor_threshold_boundary():
    """Strictly below the threshold triggers; equal does not."""
    # equal — does NOT trigger.
    out_eq = apply_channel_floor(
        overall=0.85,
        channel_scores={"a": 0.45, "b": 0.9},
        urgent_threshold=0.45,
        overall_floor=0.55,
    )
    assert out_eq == 0.85
    # one micro below — DOES trigger.
    out_below = apply_channel_floor(
        overall=0.85,
        channel_scores={"a": 0.4499, "b": 0.9},
        urgent_threshold=0.45,
        overall_floor=0.55,
    )
    assert out_below == 0.54


def test_apply_floor_custom_epsilon():
    overall = apply_channel_floor(
        overall=0.85,
        channel_scores={"a": 0.30, "b": 0.9},
        urgent_threshold=0.45,
        overall_floor=0.50,
        epsilon=0.05,
    )
    # 0.50 - 0.05 = 0.45.
    assert overall == 0.45


def test_apply_floor_clamps_negative_floor_to_zero():
    """If overall_floor - epsilon goes negative, the
    helper clamps to 0."""
    overall = apply_channel_floor(
        overall=0.85,
        channel_scores={"a": 0.0, "b": 0.9},
        urgent_threshold=0.45,
        overall_floor=0.005,  # tiny — minus epsilon goes negative
    )
    assert overall == 0.0


def test_apply_floor_handles_empty_channels():
    """No channels supplied — no override fires."""
    overall = apply_channel_floor(
        overall=0.85,
        channel_scores={},
        urgent_threshold=0.45,
        overall_floor=0.55,
    )
    assert overall == 0.85


# ---------------------------------------------------------------------------
# Integration — full fusion pattern as used by engines
# ---------------------------------------------------------------------------


def test_fusion_full_pipeline_steady_case():
    """Integration: the three helpers compose into the
    fusion pattern every engine uses — normalise, weight,
    floor."""
    weights = normalise_weights(
        {"a": 0.4, "b": 0.3, "c": 0.3},
    )
    channel_scores = {"a": 0.95, "b": 0.85, "c": 0.92}
    overall = weighted_overall(weights, channel_scores)
    overall = apply_channel_floor(
        overall, channel_scores,
        urgent_threshold=0.45, overall_floor=0.55,
    )
    # All channels well above urgent threshold, weighted
    # average ~0.91, no floor applied.
    assert 0.85 < overall < 1.0


def test_fusion_full_pipeline_urgent_case():
    weights = normalise_weights({"a": 0.4, "b": 0.3, "c": 0.3})
    channel_scores = {"a": 0.95, "b": 0.20, "c": 0.92}
    overall = weighted_overall(weights, channel_scores)
    # Weighted alone would be ~0.71 — fine. But channel b
    # below 0.45 forces floor.
    overall = apply_channel_floor(
        overall, channel_scores,
        urgent_threshold=0.45, overall_floor=0.55,
    )
    # Floored at 0.54.
    assert overall == 0.54
