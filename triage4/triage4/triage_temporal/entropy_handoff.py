"""Entropy-based handoff trigger.

Part of Phase 9c (innovation pack 2, idea #11). A casualty is ready
for medic handoff **when the observation stream stops adding
information** — the Shannon entropy of the priority distribution over
time plateaus.

Intuition: if the system has seen one casualty six times and every
observation produces the same priority, the entropy drops fast and
stabilises; further observations are wasted. If priority keeps shifting
between bands, entropy stays high and a handoff would be premature.

Usage:
    trigger = EntropyHandoffTrigger()
    for obs_priority in per_observation_priorities:
        trigger.observe("C1", obs_priority)
    if trigger.should_handoff("C1"):
        send_to_medic("C1")
"""

from __future__ import annotations

import math
from collections import defaultdict, deque
from dataclasses import dataclass


_BANDS = ("immediate", "delayed", "minimal", "expectant", "unknown")


@dataclass
class HandoffSignal:
    casualty_id: str
    entropy: float
    delta: float            # latest change in entropy
    n_observations: int
    should_handoff: bool


def _distribution(history: list[str]) -> dict[str, float]:
    total = len(history)
    if total == 0:
        return {b: 0.0 for b in _BANDS}
    counts: dict[str, int] = defaultdict(int)
    for h in history:
        counts[h] += 1
    return {b: counts[b] / total for b in _BANDS}


def _shannon_entropy(distribution: dict[str, float]) -> float:
    total = 0.0
    for p in distribution.values():
        if p > 0.0:
            total -= p * math.log2(p)
    return total


class EntropyHandoffTrigger:
    """Track per-casualty priority history and trigger handoff when stable."""

    def __init__(
        self,
        window: int = 8,
        min_observations: int = 3,
        entropy_threshold: float = 0.8,
        delta_threshold: float = 0.05,
    ) -> None:
        if window < 2:
            raise ValueError(f"window must be >= 2, got {window}")
        if min_observations < 1:
            raise ValueError(
                f"min_observations must be >= 1, got {min_observations}"
            )
        if entropy_threshold <= 0.0:
            raise ValueError(
                f"entropy_threshold must be > 0, got {entropy_threshold}"
            )
        if delta_threshold <= 0.0:
            raise ValueError(
                f"delta_threshold must be > 0, got {delta_threshold}"
            )

        self.window = int(window)
        self.min_observations = int(min_observations)
        self.entropy_threshold = float(entropy_threshold)
        self.delta_threshold = float(delta_threshold)

        self._history: dict[str, deque[str]] = defaultdict(
            lambda: deque(maxlen=self.window)
        )
        self._last_entropy: dict[str, float] = {}

    def observe(self, casualty_id: str, priority: str) -> HandoffSignal:
        if priority not in _BANDS:
            raise ValueError(
                f"priority '{priority}' is not a known triage band"
            )
        self._history[casualty_id].append(priority)

        history_list = list(self._history[casualty_id])
        entropy = _shannon_entropy(_distribution(history_list))
        prev = self._last_entropy.get(casualty_id, entropy)
        delta = abs(entropy - prev)
        self._last_entropy[casualty_id] = entropy

        n = len(history_list)
        should_handoff = (
            n >= self.min_observations
            and entropy <= self.entropy_threshold
            and delta <= self.delta_threshold
        )

        return HandoffSignal(
            casualty_id=casualty_id,
            entropy=round(entropy, 3),
            delta=round(delta, 3),
            n_observations=n,
            should_handoff=bool(should_handoff),
        )

    def should_handoff(self, casualty_id: str) -> bool:
        history_list = list(self._history.get(casualty_id, []))
        if len(history_list) < self.min_observations:
            return False
        entropy = _shannon_entropy(_distribution(history_list))
        prev = self._last_entropy.get(casualty_id, entropy)
        return (
            entropy <= self.entropy_threshold
            and abs(entropy - prev) <= self.delta_threshold
        )

    def history(self, casualty_id: str) -> list[str]:
        return list(self._history.get(casualty_id, []))
