"""Operator broadcast registry / audit log."""

from __future__ import annotations

import pytest

from triage4_coast.ui import broadcast


@pytest.fixture(autouse=True)
def isolated_log():
    broadcast.reset()
    yield
    broadcast.reset()


class TestRecord:
    def test_happy_path(self) -> None:
        e = broadcast.record(kind="shade_advisory", message="Move to shade.")
        assert e.kind == "shade_advisory"
        assert e.zone_id is None
        assert e.operator_id is None

    def test_invalid_kind(self) -> None:
        with pytest.raises(ValueError, match="kind"):
            broadcast.record(kind="bogus", message="x")

    def test_empty_message(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            broadcast.record(kind="lost_child", message="   ")

    def test_oversize_message(self) -> None:
        with pytest.raises(ValueError, match="500"):
            broadcast.record(kind="lost_child", message="x" * 501)

    def test_zone_id_optional(self) -> None:
        e = broadcast.record(
            kind="clear_water", message="Clear the water.", zone_id="Z3",
        )
        assert e.zone_id == "Z3"

    def test_zone_id_empty_string_rejected(self) -> None:
        with pytest.raises(ValueError, match="zone_id"):
            broadcast.record(kind="clear_water", message="x", zone_id="")


class TestRecent:
    def test_newest_first(self) -> None:
        broadcast.record(kind="shade_advisory", message="msg1")
        broadcast.record(kind="lost_child", message="msg2")
        rows = broadcast.recent()
        assert rows[0].kind == "lost_child"
        assert rows[1].kind == "shade_advisory"

    def test_limit(self) -> None:
        for i in range(5):
            broadcast.record(kind="shade_advisory", message=f"m{i}")
        rows = broadcast.recent(limit=3)
        assert len(rows) == 3

    def test_limit_must_be_positive(self) -> None:
        with pytest.raises(ValueError):
            broadcast.recent(limit=0)


class TestRingBuffer:
    def test_ring_caps_at_500(self) -> None:
        for i in range(550):
            broadcast.record(kind="shade_advisory", message=f"m{i}")
        rows = broadcast.recent(limit=500)
        assert len(rows) == 500
        # Oldest 50 should have been dropped.
        msgs = [r.message for r in rows]
        assert "m0" not in msgs
        assert "m549" in msgs
