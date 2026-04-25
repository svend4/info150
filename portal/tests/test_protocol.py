"""Tests for portal.protocol."""

from __future__ import annotations

import pytest

from portal.protocol import Bridge, BridgeKind, PortalEntry, VALID_LEVELS


def _entry(**overrides: object) -> PortalEntry:
    """Build a valid PortalEntry; tests override one field at a time."""
    base: dict[str, object] = dict(
        sibling_id="triage4-fish",
        entry_id="pen-1:gill_rate",
        kind="gill_rate",
        level="urgent",
        location_handle="watershed-A-pen-1",
        observed_value=0.30,
        t_window=(100.0, 160.0),
        payload={"species": "salmon"},
    )
    base.update(overrides)
    return PortalEntry(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# PortalEntry construction
# ---------------------------------------------------------------------------


def test_portal_entry_round_trips_minimal_fields() -> None:
    e = PortalEntry(
        sibling_id="triage4-bird",
        entry_id="station-7:mortality",
        kind="mortality_cluster",
        level="urgent",
        location_handle="watershed-A-station-7",
    )
    assert e.sibling_id == "triage4-bird"
    assert e.entry_id == "station-7:mortality"
    assert e.payload == {}
    assert e.t_window is None
    assert e.observed_value is None


def test_portal_entry_key_property() -> None:
    e = _entry()
    assert e.key == ("triage4-fish", "pen-1:gill_rate")


def test_portal_entry_is_frozen() -> None:
    e = _entry()
    with pytest.raises((AttributeError, TypeError)):
        e.kind = "school_cohesion"  # type: ignore[misc]


def test_portal_entry_payload_accepts_arbitrary_mapping() -> None:
    e = _entry(payload={"species": "salmon", "count": 12, "tags": ("a",)})
    assert e.payload["species"] == "salmon"
    assert e.payload["count"] == 12


# ---------------------------------------------------------------------------
# PortalEntry validation
# ---------------------------------------------------------------------------


def test_portal_entry_rejects_empty_sibling_id() -> None:
    with pytest.raises(ValueError, match="sibling_id"):
        _entry(sibling_id="")


def test_portal_entry_rejects_empty_entry_id() -> None:
    with pytest.raises(ValueError, match="entry_id"):
        _entry(entry_id="")


def test_portal_entry_rejects_empty_kind() -> None:
    with pytest.raises(ValueError, match="kind"):
        _entry(kind="")


def test_portal_entry_rejects_invalid_level() -> None:
    with pytest.raises(ValueError, match="level"):
        _entry(level="critical")


@pytest.mark.parametrize("level", list(VALID_LEVELS))
def test_portal_entry_accepts_every_valid_level(level: str) -> None:
    e = _entry(level=level)
    assert e.level == level


def test_portal_entry_rejects_blank_location_handle() -> None:
    with pytest.raises(ValueError, match="location_handle"):
        _entry(location_handle="   ")


def test_portal_entry_rejects_negative_window_start() -> None:
    with pytest.raises(ValueError, match="t_window"):
        _entry(t_window=(-1.0, 5.0))


def test_portal_entry_rejects_inverted_window() -> None:
    with pytest.raises(ValueError, match="t_window"):
        _entry(t_window=(50.0, 10.0))


def test_portal_entry_permits_zero_length_window() -> None:
    e = _entry(t_window=(50.0, 50.0))
    assert e.t_window == (50.0, 50.0)


# ---------------------------------------------------------------------------
# BridgeKind
# ---------------------------------------------------------------------------


def test_bridge_kind_str_values_stable() -> None:
    """Stringifying a kind yields the policy-stable name."""
    assert BridgeKind.CO_OCCURRENCE.value == "co_occurrence"
    assert BridgeKind.ESCALATION.value == "escalation"
    assert BridgeKind.DOMAIN_NEIGHBOR.value == "domain_neighbor"


def test_bridge_kind_count_is_six() -> None:
    """Six curated kinds — see protocol.py docstring."""
    assert len(list(BridgeKind)) == 6


# ---------------------------------------------------------------------------
# Bridge
# ---------------------------------------------------------------------------


def test_bridge_round_trip() -> None:
    b = Bridge(
        kind=BridgeKind.CO_OCCURRENCE,
        from_key=("triage4-fish", "pen-1:mortality"),
        to_key=("triage4-bird", "station-7:mortality"),
        evidence="both urgent on mortality channel",
    )
    assert b.kind is BridgeKind.CO_OCCURRENCE
    assert b.from_key[0] == "triage4-fish"


def test_bridge_rejects_self_edge() -> None:
    with pytest.raises(ValueError, match="endpoints"):
        Bridge(
            kind=BridgeKind.CO_OCCURRENCE,
            from_key=("triage4-fish", "pen-1"),
            to_key=("triage4-fish", "pen-1"),
            evidence="trivially same",
        )


def test_bridge_rejects_blank_evidence() -> None:
    with pytest.raises(ValueError, match="evidence"):
        Bridge(
            kind=BridgeKind.CO_OCCURRENCE,
            from_key=("triage4-fish", "pen-1"),
            to_key=("triage4-bird", "station-7"),
            evidence="   ",
        )


def test_bridge_is_frozen() -> None:
    b = Bridge(
        kind=BridgeKind.ANALOGY,
        from_key=("triage4-fish", "pen-1"),
        to_key=("triage4-bird", "station-7"),
        evidence="mortality analogy",
    )
    with pytest.raises((AttributeError, TypeError)):
        b.evidence = "tampered"  # type: ignore[misc]
