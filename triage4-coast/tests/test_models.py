"""Model validation: CoastZoneObservation + CoastScore + CoastOpsAlert."""

from __future__ import annotations

import pytest

from triage4_coast.core.models import (
    CoastOpsAlert,
    CoastReport,
    CoastScore,
    CoastZoneObservation,
)


def _ok_obs(**overrides: object) -> CoastZoneObservation:
    base: dict[str, object] = dict(
        zone_id="Z1",
        zone_kind="beach",
        window_duration_s=60.0,
        density_pressure=0.3,
        in_water_motion=0.0,
        sun_intensity=0.4,
        lost_child_flag=False,
    )
    base.update(overrides)
    return CoastZoneObservation(**base)  # type: ignore[arg-type]


class TestCoastZoneObservation:
    def test_happy_path(self) -> None:
        o = _ok_obs()
        assert o.zone_kind == "beach"

    def test_empty_zone_id(self) -> None:
        with pytest.raises(ValueError, match="zone_id"):
            _ok_obs(zone_id="")

    def test_invalid_zone_kind(self) -> None:
        with pytest.raises(ValueError, match="zone_kind"):
            _ok_obs(zone_kind="moonscape")

    def test_window_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="window_duration_s"):
            _ok_obs(window_duration_s=0.0)

    def test_density_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="density_pressure"):
            _ok_obs(density_pressure=1.5)


class TestCoastScore:
    def test_invalid_alert_level(self) -> None:
        with pytest.raises(ValueError, match="alert_level"):
            CoastScore(
                zone_id="Z1", zone_kind="beach",
                alert_level="critical",  # type: ignore[arg-type]
                density_safety=0.5, drowning_safety=0.5,
                sun_safety=0.5, lost_child_safety=1.0, overall=0.5,
            )

    def test_score_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="overall"):
            CoastScore(
                zone_id="Z1", zone_kind="beach",
                alert_level="ok",
                density_safety=0.5, drowning_safety=0.5,
                sun_safety=0.5, lost_child_safety=1.0, overall=1.5,
            )


class TestCoastOpsAlert:
    def test_happy_path(self) -> None:
        a = CoastOpsAlert(zone_id="Z1", kind="density", level="watch", text="busy")
        assert a.kind == "density"

    def test_empty_text_rejected(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            CoastOpsAlert(zone_id="Z1", kind="density", level="watch", text="  ")

    @pytest.mark.parametrize(
        "bad_word", ["injured", "diagnose", "treat ", "dangerous", "medical"],
    )
    def test_forbidden_words(self, bad_word: str) -> None:
        with pytest.raises(ValueError, match="forbidden"):
            CoastOpsAlert(
                zone_id="Z1", kind="density", level="watch",
                text=f"Crowd looks {bad_word} - check visually.",
            )


class TestCoastReport:
    def test_empty_coast_id(self) -> None:
        with pytest.raises(ValueError, match="coast_id"):
            CoastReport(coast_id="")

    def test_alerts_at_level(self) -> None:
        report = CoastReport(coast_id="C1")
        report.alerts.append(
            CoastOpsAlert(zone_id="Z1", kind="density", level="urgent", text="busy")
        )
        report.alerts.append(
            CoastOpsAlert(zone_id="Z1", kind="sun", level="watch", text="bright")
        )
        assert len(report.alerts_at_level("urgent")) == 1
        assert len(report.alerts_at_level("watch")) == 1

    def test_as_text(self) -> None:
        report = CoastReport(coast_id="DEMO_COAST")
        text = report.as_text()
        assert "DEMO_COAST" in text
