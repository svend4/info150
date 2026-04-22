"""Tests for the K3-3.3 forecast layer."""

from __future__ import annotations

import pytest

from triage4.mission_coordination.mission_triage import (
    MissionSignature,
    MissionTriageResult,
)
from triage4.world_replay.forecast_layer import (
    CasualtyForecast,
    ForecastLayer,
    MissionForecast,
)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_swapped_priority_bands():
    with pytest.raises(ValueError):
        ForecastLayer(immediate_band=0.3, delayed_band=0.6)


def test_project_casualty_rejects_negative_horizon():
    with pytest.raises(ValueError):
        ForecastLayer().project_casualty([0.5], minutes_ahead=-1.0)


def test_project_mission_rejects_empty_history():
    with pytest.raises(ValueError):
        ForecastLayer().project_mission([], minutes_ahead=5.0)


# ---------------------------------------------------------------------------
# Casualty forecast
# ---------------------------------------------------------------------------


def test_casualty_forecast_empty_history_returns_zero():
    fc = ForecastLayer().project_casualty([], minutes_ahead=5.0)
    assert isinstance(fc, CasualtyForecast)
    assert fc.projected_score == 0.0
    assert fc.projected_priority == "minimal"
    assert fc.confidence == 0.0
    assert "no score history" in fc.reasons


def test_casualty_forecast_single_observation_stays_flat():
    fc = ForecastLayer().project_casualty([0.7], minutes_ahead=10.0)
    assert fc.projected_score == 0.7
    assert fc.slope_per_minute == 0.0


def test_casualty_forecast_rising_trend_raises_score():
    history = [0.1, 0.2, 0.3, 0.4, 0.5]
    fc = ForecastLayer().project_casualty(history, minutes_ahead=5.0)
    assert fc.projected_score > 0.5
    assert fc.slope_per_minute > 0.0


def test_casualty_forecast_falling_trend_lowers_score():
    history = [0.8, 0.7, 0.6, 0.5, 0.4]
    fc = ForecastLayer().project_casualty(history, minutes_ahead=5.0)
    assert fc.projected_score < 0.4
    assert fc.slope_per_minute < 0.0


def test_casualty_forecast_clips_to_unit_interval():
    history = [0.85, 0.88, 0.90, 0.93, 0.95]
    fc = ForecastLayer().project_casualty(history, minutes_ahead=100.0)
    assert fc.projected_score <= 1.0


def test_casualty_forecast_flat_history_has_high_confidence():
    history = [0.5, 0.5, 0.5, 0.5]
    fc = ForecastLayer().project_casualty(history, minutes_ahead=3.0)
    assert fc.confidence >= 0.9
    assert fc.slope_per_minute == pytest.approx(0.0, abs=1e-6)


def test_casualty_forecast_noisy_history_lowers_confidence():
    history = [0.1, 0.9, 0.2, 0.8, 0.1, 0.9]
    fc = ForecastLayer().project_casualty(history, minutes_ahead=2.0)
    assert fc.confidence < 0.5
    assert any("noisy" in r for r in fc.reasons)


def test_casualty_forecast_band_thresholds_respected():
    fc = ForecastLayer().project_casualty([0.7], minutes_ahead=0.0)
    assert fc.projected_priority == "immediate"


def test_custom_band_thresholds_applied():
    layer = ForecastLayer(immediate_band=0.80, delayed_band=0.20)
    fc = layer.project_casualty([0.5], minutes_ahead=0.0)
    # 0.5 is below the custom immediate band but above delayed → "delayed".
    assert fc.projected_priority == "delayed"


# ---------------------------------------------------------------------------
# Mission forecast
# ---------------------------------------------------------------------------


def _calm_signature() -> MissionSignature:
    return MissionSignature(
        casualty_density=0.2,
        immediate_fraction=0.1,
        unresolved_sector_fraction=0.1,
        medic_utilisation=0.2,
        time_budget_burn=0.1,
    )


def _stressed_signature() -> MissionSignature:
    return MissionSignature(
        casualty_density=0.8,
        immediate_fraction=0.7,
        unresolved_sector_fraction=0.6,
        medic_utilisation=0.9,
        time_budget_burn=0.7,
    )


def test_mission_forecast_stable_history_projects_same_band():
    history = [_calm_signature() for _ in range(5)]
    fc = ForecastLayer().project_mission(history, minutes_ahead=3.0)
    assert isinstance(fc, MissionForecast)
    assert isinstance(fc.projected_result, MissionTriageResult)
    assert fc.projected_result.priority == "wind_down"
    for slope in fc.per_channel_slope.values():
        assert abs(slope) < 1e-6


def test_mission_forecast_rising_pressure_escalates():
    # Ramp every channel so escalation is inevitable.
    history = [
        MissionSignature(
            casualty_density=0.2 + 0.1 * i,
            immediate_fraction=0.1 + 0.1 * i,
            unresolved_sector_fraction=0.1 + 0.1 * i,
            medic_utilisation=0.2 + 0.1 * i,
            time_budget_burn=0.1 + 0.1 * i,
        )
        for i in range(5)
    ]
    fc = ForecastLayer().project_mission(history, minutes_ahead=3.0)
    assert fc.projected_result.priority == "escalate"
    for channel, slope in fc.per_channel_slope.items():
        assert slope > 0.0, f"expected positive slope on {channel}"


def test_mission_forecast_clips_channels_to_unit_interval():
    history = [_stressed_signature() for _ in range(5)]
    fc = ForecastLayer().project_mission(history, minutes_ahead=100.0)
    sig = fc.projected_signature
    for ch in (
        "casualty_density", "immediate_fraction", "unresolved_sector_fraction",
        "medic_utilisation", "time_budget_burn",
    ):
        v = getattr(sig, ch)
        assert 0.0 <= v <= 1.0


def test_mission_forecast_preserves_reasons_from_classifier():
    history = [_stressed_signature() for _ in range(3)]
    fc = ForecastLayer().project_mission(history, minutes_ahead=1.0)
    # classify_mission surfaces several reasons when under pressure —
    # they must travel through to the forecast.
    assert fc.reasons
    assert any(
        "dominate" in r or "saturated" in r or "unresolved" in r
        for r in fc.reasons
    )


def test_mission_forecast_short_history_warns():
    history = [_calm_signature(), _calm_signature()]
    fc = ForecastLayer().project_mission(history, minutes_ahead=1.0)
    assert any("indicative" in r for r in fc.reasons)


def test_mission_forecast_minutes_ahead_zero_returns_current():
    current = _calm_signature()
    fc = ForecastLayer().project_mission([current], minutes_ahead=0.0)
    assert fc.projected_signature.casualty_density == pytest.approx(
        current.casualty_density, abs=1e-6,
    )


def test_mission_forecast_accepts_custom_weights():
    history = [_stressed_signature() for _ in range(3)]
    custom = {
        "casualty_density": 0.10,
        "immediate_fraction": 0.60,
        "unresolved_sector_fraction": 0.10,
        "medic_utilisation": 0.10,
        "time_budget_burn": 0.10,
    }
    fc = ForecastLayer().project_mission(
        history, minutes_ahead=1.0, weights=custom,
    )
    assert fc.projected_result.priority in {"escalate", "sustain", "wind_down"}
    # Contributions must reflect the custom weights (immediate dominates).
    contribs = fc.projected_result.contributions
    assert contribs["immediate_fraction"] >= max(
        contribs["casualty_density"],
        contribs["medic_utilisation"],
    )


def test_mission_forecast_is_deterministic():
    history = [
        MissionSignature(
            casualty_density=0.3 + 0.05 * i,
            immediate_fraction=0.2 + 0.05 * i,
            unresolved_sector_fraction=0.1,
            medic_utilisation=0.4 + 0.05 * i,
            time_budget_burn=0.2 + 0.05 * i,
        )
        for i in range(4)
    ]
    a = ForecastLayer().project_mission(history, minutes_ahead=2.0)
    b = ForecastLayer().project_mission(history, minutes_ahead=2.0)
    assert a.projected_signature == b.projected_signature
    assert a.projected_result.priority == b.projected_result.priority


def test_casualty_forecast_is_deterministic():
    history = [0.1, 0.3, 0.5, 0.6, 0.8]
    a = ForecastLayer().project_casualty(history, minutes_ahead=3.0)
    b = ForecastLayer().project_casualty(history, minutes_ahead=3.0)
    assert a.projected_score == b.projected_score
    assert a.projected_priority == b.projected_priority
