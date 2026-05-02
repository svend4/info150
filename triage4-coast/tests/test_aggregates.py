"""Aggregates over the SQLite history store."""

from __future__ import annotations

import time

import pytest

from triage4_coast.ui import aggregates, history


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("TRIAGE4_COAST_HISTORY_DB", str(tmp_path / "h.sqlite"))
    history.reset()
    yield
    history.reset()


class TestHourlyZoneDensity:
    def test_empty(self) -> None:
        rows = aggregates.hourly_zone_density(zone_id="Z1")
        assert rows == []

    def test_buckets_by_hour(self) -> None:
        now = time.time()
        history.record_scores(
            zone_id="Z1", channels={"overall": 0.5}, ts_unix=now - 60,
        )
        history.record_scores(
            zone_id="Z1", channels={"overall": 0.7}, ts_unix=now - 30,
        )
        history.record_scores(
            zone_id="Z1", channels={"overall": 0.3}, ts_unix=now - 4000,
        )
        rows = aggregates.hourly_zone_density(zone_id="Z1")
        # Two buckets: 0 hours ago (current hour) and 1 hour ago.
        ages = sorted(r["hour_ago"] for r in rows)
        assert ages == [0.0, 1.0]
        # The current-hour bucket has the average of 0.5 and 0.7.
        cur = next(r for r in rows if r["hour_ago"] == 0.0)
        assert cur["mean_value"] == pytest.approx(0.6)
        assert cur["n_samples"] == 2.0

    def test_invalid_args(self) -> None:
        with pytest.raises(ValueError):
            aggregates.hourly_zone_density(zone_id="")
        with pytest.raises(ValueError):
            aggregates.hourly_zone_density(zone_id="Z1", hours=0)
        with pytest.raises(ValueError):
            aggregates.hourly_zone_density(zone_id="Z1", hours=10_000)


class TestLevelCountsOverTime:
    def test_no_zones(self) -> None:
        rows = aggregates.coast_level_counts_over_time(zone_ids=[])
        assert rows == []

    def test_buckets_classify_by_threshold(self) -> None:
        now = time.time()
        # Z1 → urgent (overall < 0.45)
        history.record_scores(
            zone_id="Z1", channels={"overall": 0.30}, ts_unix=now - 60,
        )
        # Z2 → watch (overall < 0.65)
        history.record_scores(
            zone_id="Z2", channels={"overall": 0.55}, ts_unix=now - 60,
        )
        # Z3 → ok
        history.record_scores(
            zone_id="Z3", channels={"overall": 0.90}, ts_unix=now - 60,
        )
        rows = aggregates.coast_level_counts_over_time(
            zone_ids=["Z1", "Z2", "Z3"], hours=1, bucket_minutes=5,
        )
        assert len(rows) == 1
        b = rows[0]
        assert b["urgent"] == 1.0
        assert b["watch"] == 1.0
        assert b["ok"] == 1.0

    def test_invalid_args(self) -> None:
        with pytest.raises(ValueError):
            aggregates.coast_level_counts_over_time(
                zone_ids=["Z1"], hours=0,
            )
        with pytest.raises(ValueError):
            aggregates.coast_level_counts_over_time(
                zone_ids=["Z1"], bucket_minutes=0,
            )
