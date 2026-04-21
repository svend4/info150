from __future__ import annotations


class DeteriorationModel:
    """Estimates a deterioration trend from a short history of urgency scores.

    Returns a signed slope in roughly [-1, 1] where positive values mean the
    casualty's urgency is rising (getting worse).
    """

    def trend(self, history: list[float]) -> float:
        if len(history) < 2:
            return 0.0
        deltas = [history[i + 1] - history[i] for i in range(len(history) - 1)]
        slope = sum(deltas) / len(deltas)
        return round(max(-1.0, min(1.0, slope * 3.0)), 3)

    def revisit_recommended(self, history: list[float], threshold: float = 0.1) -> bool:
        return self.trend(history) >= threshold
