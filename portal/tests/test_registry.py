"""Tests for portal.registry."""

from __future__ import annotations

from portal.protocol import Bridge, BridgeKind
from portal.registry import BridgeRegistry


_FISH_PEN = ("triage4-fish", "pen-1:mortality")
_BIRD_STA = ("triage4-bird", "station-7:mortality")
_WILD_GRD = ("triage4-wild", "grid-3:mortality")


def _b(
    kind: BridgeKind,
    from_key: tuple[str, str] = _FISH_PEN,
    to_key: tuple[str, str] = _BIRD_STA,
    evidence: str = "test",
) -> Bridge:
    return Bridge(
        kind=kind, from_key=from_key, to_key=to_key, evidence=evidence,
    )


def test_empty_registry_has_zero_length() -> None:
    r = BridgeRegistry()
    assert len(r) == 0
    assert list(r) == []


def test_add_returns_true_when_new() -> None:
    r = BridgeRegistry()
    assert r.add(_b(BridgeKind.CO_OCCURRENCE)) is True
    assert len(r) == 1


def test_add_returns_false_on_exact_duplicate() -> None:
    """Same (kind, from_key, to_key) → not re-inserted."""
    r = BridgeRegistry()
    r.add(_b(BridgeKind.CO_OCCURRENCE, evidence="first"))
    inserted = r.add(_b(BridgeKind.CO_OCCURRENCE, evidence="second"))
    assert inserted is False
    assert len(r) == 1


def test_different_kinds_same_endpoints_both_kept() -> None:
    """Same endpoints + different kind = different edges."""
    r = BridgeRegistry()
    r.add(_b(BridgeKind.CO_OCCURRENCE))
    r.add(_b(BridgeKind.ANALOGY))
    assert len(r) == 2


def test_direction_matters_for_dedup() -> None:
    """A→B and B→A are stored separately (kinds like ESCALATION are
    asymmetric)."""
    r = BridgeRegistry()
    r.add(_b(BridgeKind.ESCALATION, from_key=_FISH_PEN, to_key=_BIRD_STA))
    r.add(_b(BridgeKind.ESCALATION, from_key=_BIRD_STA, to_key=_FISH_PEN))
    assert len(r) == 2


def test_extend_returns_count_of_newly_inserted() -> None:
    r = BridgeRegistry()
    inserted = r.extend([
        _b(BridgeKind.CO_OCCURRENCE),
        _b(BridgeKind.CO_OCCURRENCE),  # duplicate
        _b(BridgeKind.ANALOGY),
    ])
    assert inserted == 2
    assert len(r) == 2


def test_by_kind_filters() -> None:
    r = BridgeRegistry()
    r.add(_b(BridgeKind.CO_OCCURRENCE, to_key=_BIRD_STA))
    r.add(_b(BridgeKind.CO_OCCURRENCE, to_key=_WILD_GRD))
    r.add(_b(BridgeKind.ANALOGY, to_key=_BIRD_STA))
    co = r.by_kind(BridgeKind.CO_OCCURRENCE)
    an = r.by_kind(BridgeKind.ANALOGY)
    assert len(co) == 2
    assert len(an) == 1


def test_by_kind_returns_empty_for_unseen() -> None:
    r = BridgeRegistry()
    r.add(_b(BridgeKind.CO_OCCURRENCE))
    assert r.by_kind(BridgeKind.GEOGRAPHIC_NEIGHBOR) == []


def test_incident_to_finds_both_directions() -> None:
    r = BridgeRegistry()
    r.add(_b(BridgeKind.CO_OCCURRENCE, from_key=_FISH_PEN, to_key=_BIRD_STA))
    r.add(_b(BridgeKind.ANALOGY,       from_key=_BIRD_STA, to_key=_WILD_GRD))
    r.add(_b(BridgeKind.ESCALATION,    from_key=_WILD_GRD, to_key=_FISH_PEN))
    bird_edges = r.incident_to(_BIRD_STA)
    assert len(bird_edges) == 2  # one as from_, one as to_


def test_incident_to_returns_empty_for_unrelated_key() -> None:
    r = BridgeRegistry()
    r.add(_b(BridgeKind.CO_OCCURRENCE))
    assert r.incident_to(("triage4-farm", "does-not-exist")) == []


def test_iter_yields_bridges_in_insertion_order() -> None:
    r = BridgeRegistry()
    b1 = _b(BridgeKind.CO_OCCURRENCE, evidence="first")
    b2 = _b(BridgeKind.ANALOGY, evidence="second")
    r.add(b1)
    r.add(b2)
    out = list(r)
    assert out[0].kind is BridgeKind.CO_OCCURRENCE
    assert out[1].kind is BridgeKind.ANALOGY
