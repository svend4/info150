"""K3-3.3 — Forecast layer.

Closes the "forecast_layer" cell of the K3 matrix. Sits next to the
existing ``TimelineStore`` + ``ReplayEngine`` (backward-looking
history) and adds a forward-looking projection.

Two forecasts are supported:

- **Casualty-level** — given a short history of urgency scores (e.g.
  ``adjusted_score`` from ``UncertaintyModel``), project the score
  ``minutes_ahead`` minutes into the future and infer the priority
  band. Uses the existing ``DeteriorationModel`` trend + a tunable
  drift multiplier. Returns a conservative ``CasualtyForecast`` with
  projected score, band, and confidence.

- **Mission-level** — given a current ``MissionSignature`` plus a
  short history of signatures, project each of the five channels
  forward by linear extrapolation and run the result back through
  ``mission_triage.classify_mission`` to get a future
  ``MissionPriority``. Returns a ``MissionForecast``.

Design goals:
- No numpy / scipy — pure-Python linear extrapolation is plenty for
  the 3–30 point windows this layer sees.
- Conservative bias: a forecast is only as confident as the slope is
  stable. Noisy histories return low confidence.
- Deterministic, auditable, no online learning.
- Projected outputs stay inside the validated ranges of
  ``MissionSignature`` (each channel in ``[0, 1]``), so downstream
  consumers cannot accidentally push invalid state into
  ``classify_mission``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from triage4.mission_coordination.mission_triage import (
    MissionSignature,
    MissionTriageResult,
    classify_mission,
)
from triage4.triage_temporal.deterioration_model import DeteriorationModel


Priority = Literal["immediate", "delayed", "minimal"]


# Defaults tuned against the existing score-fusion priority bands
# (see ``score_fusion.priority_from_score``). Deliberately
# conservative — the forecast never *raises* a casualty past the
# current band without a clear positive slope.
_IMMEDIATE_BAND = 0.65
_DELAYED_BAND = 0.35

# Mission-level channels we extrapolate.
_MISSION_CHANNELS = (
    "casualty_density",
    "immediate_fraction",
    "unresolved_sector_fraction",
    "medic_utilisation",
    "time_budget_burn",
)


@dataclass
class CasualtyForecast:
    projected_score: float
    projected_priority: Priority
    slope_per_minute: float
    confidence: float
    reasons: list[str] = field(default_factory=list)


@dataclass
class MissionForecast:
    projected_signature: MissionSignature
    projected_result: MissionTriageResult
    minutes_ahead: float
    per_channel_slope: dict[str, float]
    reasons: list[str] = field(default_factory=list)


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def _linear_slope(xs: list[float], ys: list[float]) -> float:
    """Least-squares slope. Zero on degenerate inputs."""
    n = len(xs)
    if n < 2:
        return 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den = sum((x - mean_x) ** 2 for x in xs)
    if den <= 1e-12:
        return 0.0
    return num / den


def _trend_stability(scores: list[float]) -> float:
    """How well does a linear fit explain the scores, in [0, 1].

    Conservative R^2-style stability: 1.0 means perfectly linear,
    0.0 means the residuals are as big as the variance.
    """
    n = len(scores)
    if n < 3:
        # Too few points to reliably detect non-linearity.
        return 0.5
    mean_y = sum(scores) / n
    xs = [float(i) for i in range(n)]
    slope = _linear_slope(xs, scores)
    # Fitted line: y_hat = mean_y + slope * (x - mean_x).
    mean_x = sum(xs) / n
    ss_tot = sum((y - mean_y) ** 2 for y in scores)
    ss_res = sum(
        (y - (mean_y + slope * (x - mean_x))) ** 2
        for x, y in zip(xs, scores)
    )
    if ss_tot <= 1e-12:
        # Constant history — perfectly stable by definition.
        return 1.0
    r2 = 1.0 - ss_res / ss_tot
    return max(0.0, min(1.0, r2))


class ForecastLayer:
    """Forward-looking projection for casualties and missions."""

    def __init__(
        self,
        deterioration_model: DeteriorationModel | None = None,
        immediate_band: float = _IMMEDIATE_BAND,
        delayed_band: float = _DELAYED_BAND,
    ) -> None:
        if not 0.0 < delayed_band < immediate_band < 1.0:
            raise ValueError(
                "require 0 < delayed_band < immediate_band < 1"
            )
        self._model = deterioration_model or DeteriorationModel()
        self._immediate_band = float(immediate_band)
        self._delayed_band = float(delayed_band)

    # -- casualty ------------------------------------------------------

    def project_casualty(
        self,
        score_history: list[float],
        minutes_ahead: float = 5.0,
    ) -> CasualtyForecast:
        """Project a casualty's urgency ``minutes_ahead`` minutes out.

        The history is a short time-series of post-UncertaintyModel
        adjusted scores, most recent last. ``minutes_ahead`` is
        interpreted as the forecast horizon in the same unit as the
        history (one step per minute is the default assumption;
        callers can scale ``minutes_ahead`` to match their sampling
        rate).
        """
        if minutes_ahead < 0:
            raise ValueError("minutes_ahead must be >= 0")
        if not score_history:
            return CasualtyForecast(
                projected_score=0.0,
                projected_priority="minimal",
                slope_per_minute=0.0,
                confidence=0.0,
                reasons=["no score history"],
            )

        history = [_clamp01(s) for s in score_history]
        current = history[-1]

        if len(history) < 2:
            return CasualtyForecast(
                projected_score=round(current, 3),
                projected_priority=self._priority_from_score(current),
                slope_per_minute=0.0,
                confidence=0.3,
                reasons=["single observation — projection equals current"],
            )

        xs = [float(i) for i in range(len(history))]
        slope = _linear_slope(xs, history)
        # Blend in the deterioration-model slope for continuity with
        # the existing temporal reasoning path.
        trend = self._model.trend(history)
        blended_slope = 0.5 * slope + 0.5 * (trend / 3.0)

        projected = _clamp01(current + blended_slope * minutes_ahead)
        stability = _trend_stability(history)

        reasons: list[str] = []
        reasons.append(
            f"last score {current:.2f}, slope {blended_slope:+.3f} per minute"
        )
        if stability < 0.4:
            reasons.append("history is noisy — forecast confidence lowered")
        if abs(blended_slope) < 1e-3:
            reasons.append("near-flat trend — projection close to current")

        return CasualtyForecast(
            projected_score=round(projected, 3),
            projected_priority=self._priority_from_score(projected),
            slope_per_minute=round(blended_slope, 4),
            confidence=round(stability, 3),
            reasons=reasons,
        )

    # -- mission -------------------------------------------------------

    def project_mission(
        self,
        signature_history: list[MissionSignature],
        minutes_ahead: float = 5.0,
        weights: dict[str, float] | None = None,
    ) -> MissionForecast:
        """Project the mission signature ``minutes_ahead`` out and classify."""
        if minutes_ahead < 0:
            raise ValueError("minutes_ahead must be >= 0")
        if not signature_history:
            raise ValueError("signature_history must not be empty")

        current = signature_history[-1]
        slopes = self._mission_slopes(signature_history)

        projected_kwargs: dict[str, float] = {}
        for channel in _MISSION_CHANNELS:
            current_v = float(getattr(current, channel))
            new_v = _clamp01(current_v + slopes[channel] * minutes_ahead)
            projected_kwargs[channel] = new_v

        projected = MissionSignature(**projected_kwargs)
        result = classify_mission(projected, weights=weights)

        reasons: list[str] = []
        reasons.extend(result.reasons)
        rising = [
            c for c, s in slopes.items()
            if s > 1e-3 and c in {"immediate_fraction", "medic_utilisation"}
        ]
        if rising:
            reasons.append(
                f"projected to escalate on: {', '.join(sorted(rising))}"
            )
        if len(signature_history) < 3:
            reasons.append("short history — forecast is indicative, not reliable")

        return MissionForecast(
            projected_signature=projected,
            projected_result=result,
            minutes_ahead=float(minutes_ahead),
            per_channel_slope={k: round(v, 4) for k, v in slopes.items()},
            reasons=reasons,
        )

    # -- internals -----------------------------------------------------

    def _priority_from_score(self, score: float) -> Priority:
        if score >= self._immediate_band:
            return "immediate"
        if score >= self._delayed_band:
            return "delayed"
        return "minimal"

    @staticmethod
    def _mission_slopes(
        history: list[MissionSignature],
    ) -> dict[str, float]:
        xs = [float(i) for i in range(len(history))]
        slopes: dict[str, float] = {}
        for channel in _MISSION_CHANNELS:
            ys = [float(getattr(s, channel)) for s in history]
            slopes[channel] = _linear_slope(xs, ys)
        return slopes
