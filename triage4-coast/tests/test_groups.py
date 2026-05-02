"""Tour-group registry — register / checkin / state derivation."""

from __future__ import annotations

import time

import pytest

from triage4_coast.ui import groups


@pytest.fixture(autouse=True)
def isolated_registry():
    groups.reset()
    yield
    groups.reset()


class TestRegister:
    def test_happy_path(self) -> None:
        g = groups.register(
            name="Helsinki Tours", expected_count=12,
            meeting_zone_id="Z1-beach", operator_id="op1",
        )
        assert g.name == "Helsinki Tours"
        assert g.expected_count == 12
        assert g.last_known_count == 12
        assert g.state == "active"
        assert len(g.history) == 1

    def test_initial_count_below_expected(self) -> None:
        g = groups.register(
            name="Late arrivals", expected_count=10, initial_count=8,
        )
        assert g.last_known_count == 8

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(ValueError, match="name"):
            groups.register(name="   ", expected_count=10)

    def test_huge_count_rejected(self) -> None:
        with pytest.raises(ValueError, match="expected_count"):
            groups.register(name="X", expected_count=500)

    def test_initial_above_expected(self) -> None:
        with pytest.raises(ValueError, match="initial_count"):
            groups.register(name="X", expected_count=10, initial_count=11)


class TestCheckin:
    def test_full_count_stays_active(self) -> None:
        g = groups.register(name="X", expected_count=10)
        g2 = groups.checkin(group_id=g.group_id, count=10)
        assert g2.state == "active"
        assert len(g2.history) == 2

    def test_missing_member_triggers_alert(self) -> None:
        g = groups.register(name="X", expected_count=10)
        g2 = groups.checkin(group_id=g.group_id, count=8)
        assert g2.state == "alert"

    def test_within_tolerance_stays_active(self) -> None:
        g = groups.register(name="X", expected_count=10)
        g2 = groups.checkin(group_id=g.group_id, count=9)
        assert g2.state == "active"

    def test_unknown_group_raises(self) -> None:
        with pytest.raises(KeyError):
            groups.checkin(group_id="bogus", count=5)

    def test_complete_blocks_further_checkins(self) -> None:
        g = groups.register(name="X", expected_count=10)
        groups.complete(g.group_id)
        with pytest.raises(ValueError, match="complete"):
            groups.checkin(group_id=g.group_id, count=5)


class TestStateDerivation:
    def test_overdue_triggers_alert(self) -> None:
        g = groups.register(name="X", expected_count=10)
        # Force last_checkin to be 10 min in the past.
        g.last_checkin_ts_unix = time.time() - 600
        derived = g.derive_state(now=time.time())
        assert derived == "alert"

    def test_complete_stays_complete(self) -> None:
        g = groups.register(name="X", expected_count=10)
        g.state = "complete"
        g.last_checkin_ts_unix = time.time() - 10_000
        derived = g.derive_state(now=time.time())
        assert derived == "complete"


class TestListAll:
    def test_alert_groups_first(self) -> None:
        g_ok = groups.register(name="OK", expected_count=10)
        g_alert = groups.register(name="MISSING", expected_count=10)
        groups.checkin(group_id=g_alert.group_id, count=5)  # triggers alert
        groups.complete(g_ok.group_id)
        all_groups = groups.list_all()
        states = [g.state for g in all_groups]
        # alert should come before complete
        alert_idx = states.index("alert")
        complete_idx = states.index("complete")
        assert alert_idx < complete_idx


class TestRemove:
    def test_remove_unknown(self) -> None:
        with pytest.raises(KeyError):
            groups.remove("bogus")

    def test_remove_then_get_fails(self) -> None:
        g = groups.register(name="X", expected_count=10)
        groups.remove(g.group_id)
        with pytest.raises(KeyError):
            groups.get(g.group_id)


class TestEndpointShape:
    """Smoke through FastAPI."""

    def test_full_flow(self) -> None:
        from fastapi.testclient import TestClient
        from triage4_coast.ui.dashboard_api import app
        c = TestClient(app)
        # create
        r = c.post("/groups", json={
            "name": "FlowTest", "expected_count": 8,
            "meeting_zone_id": "Z1", "operator_id": "op1",
        })
        assert r.status_code == 200
        gid = r.json()["group_id"]
        # checkin missing member
        r2 = c.post(f"/groups/{gid}/checkin", json={"count": 5, "note": "two stragglers"})
        assert r2.status_code == 200
        assert r2.json()["state"] == "alert"
        # list
        r3 = c.get("/groups")
        assert any(g["group_id"] == gid for g in r3.json()["groups"])
        # complete
        r4 = c.post(f"/groups/{gid}/complete")
        assert r4.json()["state"] == "complete"
        # remove
        r5 = c.delete(f"/groups/{gid}")
        assert r5.status_code == 200
        # 404 after
        r6 = c.get(f"/groups/{gid}")
        assert r6.status_code == 404
