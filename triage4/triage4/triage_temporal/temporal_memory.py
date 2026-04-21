from __future__ import annotations

from collections import deque


class TemporalMemory:
    """Stores a short rolling history of triage scores per casualty."""

    def __init__(self, window: int = 8) -> None:
        self.window = window
        self._history: dict[str, deque[float]] = {}

    def push(self, casualty_id: str, score: float) -> None:
        hist = self._history.setdefault(casualty_id, deque(maxlen=self.window))
        hist.append(float(score))

    def history(self, casualty_id: str) -> list[float]:
        return list(self._history.get(casualty_id, []))

    def all(self) -> dict[str, list[float]]:
        return {cid: list(h) for cid, h in self._history.items()}
