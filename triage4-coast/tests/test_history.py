"""SQLite history store — record / fetch / purge."""

from __future__ import annotations

import time

import pytest

from triage4_coast.ui import history


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("TRIAGE4_COAST_HISTORY_DB", str(tmp_path / "h.sqlite"))
    history.reset()
    yield
    history.reset()


class TestRecordScores:
    def test_round_trip(self) -> None:
        history.record_scores(
            zone_id="Z1",
            channels={"density_safety": 0.9, "overall": 0.8},
        )
        rows = history.fetch_history(zone_id="Z1", channel="density_safety")
        assert len(rows) == 1
        assert rows[0][1] == pytest.approx(0.9)

    def test_two_channels_two_rows(self) -> None:
        history.record_scores(
            zone_id="Z1", channels={"density_safety": 0.5, "overall": 0.6},
        )
        d = history.fetch_history(zone_id="Z1", channel="density_safety")
        o = history.fetch_history(zone_id="Z1", channel="overall")
        assert len(d) == 1 and len(o) == 1

    def test_empty_zone_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="zone_id"):
            history.record_scores(zone_id="", channels={"x": 1.0})


class TestFetchHistory:
    def test_filter_by_zone(self) -> None:
        history.record_scores(zone_id="Z1", channels={"overall": 0.5})
        history.record_scores(zone_id="Z2", channels={"overall": 0.7})
        z1 = history.fetch_history(zone_id="Z1", channel="overall")
        assert len(z1) == 1
        assert z1[0][1] == pytest.approx(0.5)

    def test_ordering_oldest_first(self) -> None:
        t0 = time.time()
        history.record_scores(
            zone_id="Z1", channels={"overall": 0.4}, ts_unix=t0,
        )
        history.record_scores(
            zone_id="Z1", channels={"overall": 0.6}, ts_unix=t0 + 5.0,
        )
        rows = history.fetch_history(zone_id="Z1", channel="overall")
        assert rows[0][0] < rows[1][0]
        assert rows[0][1] == pytest.approx(0.4)
        assert rows[1][1] == pytest.approx(0.6)

    def test_since_cutoff(self) -> None:
        t0 = time.time()
        history.record_scores(
            zone_id="Z1", channels={"overall": 0.4}, ts_unix=t0 - 100.0,
        )
        history.record_scores(
            zone_id="Z1", channels={"overall": 0.6}, ts_unix=t0,
        )
        rows = history.fetch_history(
            zone_id="Z1", channel="overall", since_unix=t0 - 50.0,
        )
        assert len(rows) == 1
        assert rows[0][1] == pytest.approx(0.6)

    def test_invalid_args(self) -> None:
        with pytest.raises(ValueError):
            history.fetch_history(zone_id="", channel="overall")
        with pytest.raises(ValueError):
            history.fetch_history(zone_id="Z1", channel="")
        with pytest.raises(ValueError):
            history.fetch_history(zone_id="Z1", channel="overall", limit=0)


class TestPurge:
    def test_purge_drops_old_rows(self) -> None:
        t0 = time.time()
        history.record_scores(
            zone_id="Z1", channels={"overall": 0.1}, ts_unix=t0 - 7200.0,
        )
        history.record_scores(
            zone_id="Z1", channels={"overall": 0.9}, ts_unix=t0,
        )
        deleted = history.purge_older_than(max_age_s=3600.0)
        assert deleted == 1
        rows = history.fetch_history(zone_id="Z1", channel="overall")
        assert len(rows) == 1

    def test_purge_invalid_age(self) -> None:
        with pytest.raises(ValueError):
            history.purge_older_than(max_age_s=0.0)
