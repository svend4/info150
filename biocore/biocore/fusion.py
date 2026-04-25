"""Weighted-fusion + channel-urgent-override helpers.

Tier-2 extraction. Twelve of the fourteen engines share three
fusion-related patterns at byte-level similarity, hence the
biocore extraction:

1. **Weight normalisation** — every engine's ``__init__``
   accepts an optional ``weights`` dict, sums it, raises on
   non-positive total, and re-scales so the values sum to
   exactly 1.0.

2. **Weighted overall score** — every engine fuses per-
   channel safety scores with the normalised weights into
   a single ``overall`` value clamped to [0, 1].

3. **Channel-urgent mortal-sign override** — most engines
   force ``overall`` into the urgent tier whenever ANY
   per-channel score falls below the channel-urgent
   threshold, even when the weighted average alone would
   not. Same shape across triage4-farm / triage4-drive /
   triage4-home / triage4-site / triage4-crowd /
   triage4-aqua / triage4-pet / triage4-clinic /
   triage4-wild / triage4-bird / triage4-sport /
   triage4-fish.

What's deliberately NOT extracted:

- The 3-tier label mapping (``ok / watch / urgent``,
  ``self_care / schedule / urgent_review``, ``steady /
  monitor / hold``, etc) — the labels are per-sibling
  ``Literal`` types and extracting them would force a
  shared vocabulary that erases per-sibling specificity.
  The 4-line inline if/elif staircase in each engine is
  cheaper to keep than abstract.
- The cross-modal corroborative-alert pattern (bird +
  fish) — only two siblings, below the §7 ≥ 3 threshold.
- Per-channel weighting tuning — each sibling's weights
  are domain-specific (audio-first for bird, multi-modal
  for fish, etc).
"""

from __future__ import annotations

from typing import Mapping


def normalise_weights(weights: Mapping[str, float]) -> dict[str, float]:
    """Return a copy of ``weights`` re-scaled to sum to 1.0.

    Raises ``ValueError`` if the input is empty or sums
    to a non-positive total. Used in every engine's
    ``__init__`` to validate caller-supplied weights.

    Negative individual weights are permitted as long as
    the total is positive — defensive callers may want to
    pass ``0.0`` for a disabled channel.
    """
    if not weights:
        raise ValueError("weights mapping must not be empty")
    items = dict(weights)
    total = sum(items.values())
    if total <= 0:
        raise ValueError(
            f"weight total must be positive, got {total}"
        )
    return {k: v / total for k, v in items.items()}


def weighted_overall(
    weights: Mapping[str, float],
    channel_scores: Mapping[str, float],
) -> float:
    """Weighted sum of channel safety scores, clamped to [0, 1].

    Both arguments must share the same key set.
    ``weights`` should already be normalised (sum to 1.0)
    via ``normalise_weights``. ``channel_scores`` are the
    per-channel safety values produced by the signature
    layer.

    Raises ``KeyError`` if a weight key is missing from
    ``channel_scores``.
    """
    overall = 0.0
    for name, w in weights.items():
        if name not in channel_scores:
            raise KeyError(
                f"channel_scores missing weight key {name!r}"
            )
        overall += w * channel_scores[name]
    return max(0.0, min(1.0, overall))


def apply_channel_floor(
    overall: float,
    channel_scores: Mapping[str, float],
    urgent_threshold: float,
    overall_floor: float,
    *,
    epsilon: float = 0.01,
) -> float:
    """Mortal-sign-style channel-urgent override.

    If any value in ``channel_scores`` is strictly below
    ``urgent_threshold``, force ``overall`` to be at most
    ``overall_floor - epsilon``. Otherwise return
    ``overall`` unchanged.

    The default ``epsilon = 0.01`` matches the catalog
    convention (siblings use ``overall_urgent - 0.01``)
    so the level-mapping that follows downstream lands
    cleanly in the urgent tier rather than on its
    boundary.

    The output is clamped to [0, 1].
    """
    if any(score < urgent_threshold for score in channel_scores.values()):
        overall = min(overall, overall_floor - epsilon)
    return max(0.0, min(1.0, overall))


__all__ = [
    "apply_channel_floor",
    "normalise_weights",
    "weighted_overall",
]
