"""Tests for portal.discovery — six rules + composition."""

from __future__ import annotations

from portal.discovery import (
    discover_all,
    discover_analogy,
    discover_co_occurrence,
    discover_domain_neighbor,
    discover_escalation,
    discover_geographic_neighbor,
    discover_temporal_correlate,
)
from portal.protocol import BridgeKind, PortalEntry
from portal.registry import BridgeRegistry


def _entry(
    sibling_id: str,
    entry_id: str,
    kind: str,
    level: str,
    *,
    location_handle: str = "watershed-A-pen-1",
    t_window: tuple[float, float] | None = (100.0, 160.0),
) -> PortalEntry:
    return PortalEntry(
        sibling_id=sibling_id,
        entry_id=entry_id,
        kind=kind,
        level=level,
        location_handle=location_handle,
        t_window=t_window,
    )


# ---------------------------------------------------------------------------
# CO_OCCURRENCE
# ---------------------------------------------------------------------------


def test_co_occurrence_emits_for_matching_kind_urgent_pair() -> None:
    a = _entry("triage4-fish", "pen-1:mortality_floor",
               "mortality_floor", "urgent")
    b = _entry("triage4-bird", "station-7:mortality_floor",
               "mortality_floor", "urgent")
    bridges = discover_co_occurrence([a, b])
    assert len(bridges) == 1
    assert bridges[0].kind is BridgeKind.CO_OCCURRENCE


def test_co_occurrence_skips_same_sibling() -> None:
    a = _entry("triage4-fish", "pen-1:m", "mortality_floor", "urgent")
    b = _entry("triage4-fish", "pen-2:m", "mortality_floor", "urgent")
    assert discover_co_occurrence([a, b]) == []


def test_co_occurrence_skips_when_one_is_watch() -> None:
    a = _entry("triage4-fish", "pen-1:m", "mortality_floor", "urgent")
    b = _entry("triage4-bird", "station-7:m", "mortality_floor", "watch")
    assert discover_co_occurrence([a, b]) == []


def test_co_occurrence_skips_different_kind() -> None:
    a = _entry("triage4-fish", "pen-1:gill", "gill_rate", "urgent")
    b = _entry("triage4-bird", "station-7:m", "mortality_floor", "urgent")
    assert discover_co_occurrence([a, b]) == []


def test_co_occurrence_only_one_direction_per_pair() -> None:
    """Symmetric kind — pair (i, j) emitted once with i<j."""
    a = _entry("triage4-fish", "pen-1:m", "mortality_floor", "urgent")
    b = _entry("triage4-bird", "station-7:m", "mortality_floor", "urgent")
    c = _entry("triage4-wild", "grid-3:m", "mortality_floor", "urgent")
    bridges = discover_co_occurrence([a, b, c])
    assert len(bridges) == 3  # 3 choose 2


# ---------------------------------------------------------------------------
# DOMAIN_NEIGHBOR
# ---------------------------------------------------------------------------


def test_domain_neighbor_pairs_close_siblings() -> None:
    """bird + wild are at Hamming 0."""
    a = _entry("triage4-bird", "station-7:m", "mortality", "urgent")
    b = _entry("triage4-wild", "grid-3:m",     "mortality_event", "urgent")
    bridges = discover_domain_neighbor([a, b])
    assert len(bridges) == 1
    assert bridges[0].kind is BridgeKind.DOMAIN_NEIGHBOR


def test_domain_neighbor_skips_far_siblings() -> None:
    """bird and fish are at Hamming 3 — too far."""
    a = _entry("triage4-bird", "station-7:m", "mortality", "urgent")
    b = _entry("triage4-fish", "pen-1:m",     "mortality_floor", "urgent")
    assert discover_domain_neighbor([a, b]) == []


def test_domain_neighbor_skips_unregistered_sibling() -> None:
    """A sibling without a registered coord is silently skipped."""
    a = _entry("triage4-bird", "s7:m", "mortality", "urgent")
    b = _entry("triage4-farm", "f1:m", "mortality", "urgent")  # not registered
    assert discover_domain_neighbor([a, b]) == []


def test_domain_neighbor_requires_both_urgent() -> None:
    a = _entry("triage4-bird", "s7:m", "mortality", "watch")
    b = _entry("triage4-wild", "g3:m", "mortality_event", "urgent")
    assert discover_domain_neighbor([a, b]) == []


# ---------------------------------------------------------------------------
# GEOGRAPHIC_NEIGHBOR
# ---------------------------------------------------------------------------


def test_geographic_neighbor_pairs_shared_prefix() -> None:
    a = _entry("triage4-fish", "pen-1:gill", "gill_rate", "watch",
               location_handle="watershed-A-pen-1")
    b = _entry("triage4-bird", "st-7:m", "mortality_cluster", "watch",
               location_handle="watershed-A-station-7")
    bridges = discover_geographic_neighbor([a, b])
    assert len(bridges) == 1
    assert "watershed-A" in bridges[0].evidence


def test_geographic_neighbor_no_match_for_different_prefix() -> None:
    a = _entry("triage4-fish", "p1:gill", "gill_rate", "watch",
               location_handle="watershed-A-pen-1")
    b = _entry("triage4-bird", "s7:m", "mortality", "watch",
               location_handle="watershed-B-station-7")
    assert discover_geographic_neighbor([a, b]) == []


def test_geographic_neighbor_handles_with_no_dashes_skipped() -> None:
    a = _entry("triage4-fish", "p1:g", "gill_rate", "watch",
               location_handle="opaque1")
    b = _entry("triage4-bird", "s7:m", "mortality", "watch",
               location_handle="opaque2")
    assert discover_geographic_neighbor([a, b]) == []


def test_geographic_neighbor_skips_same_sibling() -> None:
    a = _entry("triage4-fish", "p1:g", "gill_rate", "watch",
               location_handle="watershed-A-pen-1")
    b = _entry("triage4-fish", "p2:g", "gill_rate", "watch",
               location_handle="watershed-A-pen-2")
    assert discover_geographic_neighbor([a, b]) == []


# ---------------------------------------------------------------------------
# TEMPORAL_CORRELATE
# ---------------------------------------------------------------------------


def test_temporal_correlate_pairs_overlapping_windows() -> None:
    a = _entry("triage4-fish", "p1:g", "gill_rate", "watch",
               t_window=(100.0, 200.0))
    b = _entry("triage4-bird", "s7:m", "mortality", "urgent",
               t_window=(150.0, 250.0))
    bridges = discover_temporal_correlate([a, b])
    assert len(bridges) == 1


def test_temporal_correlate_no_overlap_no_bridge() -> None:
    a = _entry("triage4-fish", "p1:g", "gill_rate", "watch",
               t_window=(100.0, 150.0))
    b = _entry("triage4-bird", "s7:m", "mortality", "urgent",
               t_window=(200.0, 300.0))
    assert discover_temporal_correlate([a, b]) == []


def test_temporal_correlate_skips_when_no_window() -> None:
    a = _entry("triage4-fish", "p1:g", "gill_rate", "watch", t_window=None)
    b = _entry("triage4-bird", "s7:m", "mortality", "urgent",
               t_window=(200.0, 300.0))
    assert discover_temporal_correlate([a, b]) == []


def test_temporal_correlate_skips_steady_level() -> None:
    a = _entry("triage4-fish", "p1:g", "gill_rate", "steady",
               t_window=(100.0, 200.0))
    b = _entry("triage4-bird", "s7:m", "mortality", "urgent",
               t_window=(150.0, 250.0))
    assert discover_temporal_correlate([a, b]) == []


# ---------------------------------------------------------------------------
# ESCALATION
# ---------------------------------------------------------------------------


def test_escalation_emits_watch_to_urgent() -> None:
    a = _entry("triage4-fish", "p1:g", "gill_rate", "watch")
    b = _entry("triage4-bird", "s7:g", "gill_rate", "urgent")
    bridges = discover_escalation([a, b])
    assert len(bridges) == 1
    assert bridges[0].from_key == ("triage4-fish", "p1:g")
    assert bridges[0].to_key == ("triage4-bird", "s7:g")


def test_escalation_asymmetric_urgent_to_watch_skipped() -> None:
    """Direction matters: urgent->watch is NOT an escalation."""
    a = _entry("triage4-bird", "s7:g", "gill_rate", "urgent")
    b = _entry("triage4-fish", "p1:g", "gill_rate", "watch")
    bridges = discover_escalation([a, b])
    assert len(bridges) == 1
    assert bridges[0].from_key == ("triage4-fish", "p1:g")  # the watch one


def test_escalation_requires_kind_match() -> None:
    a = _entry("triage4-fish", "p1:g", "gill_rate", "watch")
    b = _entry("triage4-bird", "s7:m", "mortality", "urgent")
    assert discover_escalation([a, b]) == []


def test_escalation_skips_same_sibling() -> None:
    a = _entry("triage4-fish", "p1:g", "gill_rate", "watch")
    b = _entry("triage4-fish", "p2:g", "gill_rate", "urgent")
    assert discover_escalation([a, b]) == []


# ---------------------------------------------------------------------------
# ANALOGY
# ---------------------------------------------------------------------------


def test_analogy_pairs_mortality_flavoured_kinds() -> None:
    a = _entry("triage4-fish", "p1:m", "mortality_floor", "urgent")
    b = _entry("triage4-bird", "s7:m", "mortality_cluster", "urgent")
    bridges = discover_analogy([a, b])
    assert len(bridges) == 1
    assert bridges[0].kind is BridgeKind.ANALOGY


def test_analogy_skips_when_kinds_exactly_equal() -> None:
    """Exact-equal kinds belong to CO_OCCURRENCE, not ANALOGY."""
    a = _entry("triage4-fish", "p1:m", "mortality_floor", "urgent")
    b = _entry("triage4-bird", "s7:m", "mortality_floor", "urgent")
    assert discover_analogy([a, b]) == []


def test_analogy_skips_non_mortality_kinds() -> None:
    a = _entry("triage4-fish", "p1:g", "gill_rate", "urgent")
    b = _entry("triage4-bird", "s7:c", "call_distress", "urgent")
    assert discover_analogy([a, b]) == []


def test_analogy_requires_both_urgent() -> None:
    a = _entry("triage4-fish", "p1:m", "mortality_floor", "urgent")
    b = _entry("triage4-bird", "s7:m", "mortality_cluster", "watch")
    assert discover_analogy([a, b]) == []


# ---------------------------------------------------------------------------
# discover_all + integration with registry
# ---------------------------------------------------------------------------


def test_discover_all_runs_every_rule() -> None:
    """Build a fixture that triggers each of the six rules."""
    entries = [
        # fish urgent mortality_floor — pairs with bird's same-kind
        # urgent (CO_OCCURRENCE) and with wild's mortality_event
        # (ANALOGY).
        _entry("triage4-fish", "p1:m", "mortality_floor", "urgent",
               location_handle="watershed-A-pen-1",
               t_window=(100.0, 200.0)),
        # bird urgent mortality_floor — same kind as fish (CO_OCCURRENCE).
        # bird+wild are domain-adjacent (DOMAIN_NEIGHBOR).
        _entry("triage4-bird", "s7:m", "mortality_floor", "urgent",
               location_handle="watershed-A-station-7",
               t_window=(150.0, 250.0)),
        # wild urgent mortality_event — different fragment, fires
        # ANALOGY with fish; DOMAIN_NEIGHBOR with bird; same prefix
        # → GEOGRAPHIC_NEIGHBOR with fish + bird.
        _entry("triage4-wild", "g3:m", "mortality_event", "urgent",
               location_handle="watershed-A-grid-3",
               t_window=(180.0, 260.0)),
        # bird watch on mortality_floor in another watershed —
        # provides ESCALATION (watch → urgent) with fish/bird above.
        _entry("triage4-wild", "g4:m", "mortality_floor", "watch",
               location_handle="watershed-B-grid-4",
               t_window=(50.0, 80.0)),
    ]
    bridges = discover_all(entries)
    kinds = {b.kind for b in bridges}
    assert BridgeKind.CO_OCCURRENCE in kinds       # fish↔bird mortality_floor
    assert BridgeKind.ANALOGY in kinds             # mortality_event ↔ floor
    assert BridgeKind.DOMAIN_NEIGHBOR in kinds     # bird↔wild
    assert BridgeKind.GEOGRAPHIC_NEIGHBOR in kinds # watershed-A trio
    assert BridgeKind.TEMPORAL_CORRELATE in kinds  # overlapping urgent
    assert BridgeKind.ESCALATION in kinds          # watch → urgent


def test_discover_all_handles_empty() -> None:
    assert discover_all([]) == []


def test_discover_all_into_registry_dedupes_repeat_calls() -> None:
    """Running discover_all twice on the same input → registry stays
    the same size after the second pass."""
    entries = [
        _entry("triage4-fish", "p1:m", "mortality_floor", "urgent"),
        _entry("triage4-bird", "s7:m", "mortality_floor", "urgent"),
    ]
    r = BridgeRegistry()
    r.extend(discover_all(entries))
    size_after_first = len(r)
    r.extend(discover_all(entries))
    assert len(r) == size_after_first
