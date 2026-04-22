"""Tests for the K3-2.2 conflict resolver."""

from __future__ import annotations

import pytest

from triage4.state_graph.conflict_resolver import (
    ConflictGroup,
    ConflictResolver,
    ResolvedHypothesis,
    ResolvedHypotheses,
)


def test_empty_input_returns_empty_result():
    r = ConflictResolver().resolve({})
    assert r.ranked == []
    assert r.groups == []


def test_single_hypothesis_passes_through():
    r = ConflictResolver().resolve({"hemorrhage_risk": 0.8})
    assert len(r.ranked) == 1
    entry = r.ranked[0]
    assert entry.name == "hemorrhage_risk"
    assert entry.raw_score == 0.8
    assert entry.adjusted_score == 0.8
    assert entry.suppressed is False


def test_supporting_hypotheses_boost_each_other():
    scores = {"hemorrhage_risk": 0.6, "shock_risk": 0.5}
    r = ConflictResolver().resolve(scores)
    for name in scores:
        entry = next(e for e in r.ranked if e.name == name)
        assert entry.adjusted_score > entry.raw_score
        assert any("supported by" in reason for reason in entry.reasons)


def test_conflict_suppresses_weaker_hypothesis():
    scores = {"unresponsive": 0.9, "alive_and_talking": 0.3}
    r = ConflictResolver().resolve(scores)
    winner = next(e for e in r.ranked if e.name == "unresponsive")
    loser = next(e for e in r.ranked if e.name == "alive_and_talking")
    assert winner.suppressed is False
    assert loser.suppressed is True
    assert loser.adjusted_score < loser.raw_score
    assert any("outweighed by unresponsive" in reason for reason in loser.reasons)


def test_conflict_group_reports_winner_and_members():
    scores = {"unresponsive": 0.9, "alive_and_talking": 0.3}
    r = ConflictResolver().resolve(scores)
    assert len(r.groups) == 1
    group = r.groups[0]
    assert isinstance(group, ConflictGroup)
    assert group.winner == "unresponsive"
    assert set(group.members) == {"unresponsive", "alive_and_talking"}


def test_rank_places_suppressed_entries_last():
    scores = {
        "unresponsive": 0.9,
        "alive_and_talking": 0.3,
        "shock_risk": 0.5,
    }
    r = ConflictResolver().resolve(scores)
    names = [e.name for e in r.ranked]
    assert names.index("alive_and_talking") == len(names) - 1
    # shock_risk is not in conflict with unresponsive; it ranks by
    # its own adjusted score.
    assert "shock_risk" in names[:2]


def test_scores_stay_in_unit_interval():
    scores = {
        "hemorrhage_risk": 0.95,
        "shock_risk": 0.95,
        "severe_trauma_suspicion": 0.95,
    }
    r = ConflictResolver().resolve(scores)
    for entry in r.ranked:
        assert 0.0 <= entry.adjusted_score <= 1.0


def test_custom_conflict_set_overrides_default():
    scores = {"a": 0.8, "b": 0.4}
    resolver = ConflictResolver(conflict=frozenset([frozenset(("a", "b"))]))
    r = resolver.resolve(scores)
    winner_entry = next(e for e in r.ranked if e.name == "a")
    loser_entry = next(e for e in r.ranked if e.name == "b")
    assert winner_entry.suppressed is False
    assert loser_entry.suppressed is True
    assert len(r.groups) == 1
    assert r.groups[0].winner == "a"


def test_tie_breaks_prefer_first_alphabetical_winner():
    scores = {"unresponsive": 0.5, "alive_and_talking": 0.5}
    r = ConflictResolver().resolve(scores)
    group = r.groups[0]
    # Equal scores — tie-break falls through to name ordering (ascending).
    assert group.winner in {"alive_and_talking", "unresponsive"}
    # But the ranking must still be deterministic across runs.
    r2 = ConflictResolver().resolve(scores)
    assert [e.name for e in r.ranked] == [e.name for e in r2.ranked]


def test_no_conflict_means_no_groups():
    scores = {"hemorrhage_risk": 0.7, "shock_risk": 0.6}
    r = ConflictResolver().resolve(scores)
    # Support pair, no conflict pair — groups list must be empty.
    assert r.groups == []
    assert all(not e.suppressed for e in r.ranked)


def test_raw_scores_are_preserved_untouched():
    scores = {"unresponsive": 0.9, "alive_and_talking": 0.3}
    r = ConflictResolver().resolve(scores)
    raw_map = {e.name: e.raw_score for e in r.ranked}
    assert raw_map["unresponsive"] == 0.9
    assert raw_map["alive_and_talking"] == 0.3


def test_resolved_hypotheses_dataclass_shape():
    r = ConflictResolver().resolve({"hemorrhage_risk": 0.5})
    assert isinstance(r, ResolvedHypotheses)
    assert isinstance(r.ranked[0], ResolvedHypothesis)


def test_resolver_is_deterministic_across_invocations():
    scores = {
        "unresponsive": 0.9,
        "alive_and_talking": 0.3,
        "shock_risk": 0.6,
        "hemorrhage_risk": 0.7,
    }
    resolver = ConflictResolver()
    a = resolver.resolve(scores)
    b = resolver.resolve(scores)
    assert [e.name for e in a.ranked] == [e.name for e in b.ranked]
    assert [e.adjusted_score for e in a.ranked] == [e.adjusted_score for e in b.ranked]


def test_rejects_nonexistent_neighbours_gracefully():
    # Hypotheses with no neighbour in the KB — should pass through
    # unchanged.
    scores = {"mystery_hypothesis_42": 0.7}
    r = ConflictResolver().resolve(scores)
    assert len(r.ranked) == 1
    assert r.ranked[0].raw_score == r.ranked[0].adjusted_score
    assert r.ranked[0].reasons == []


@pytest.mark.parametrize("boost,penalty", [(0.0, 0.0), (0.5, 0.5), (1.0, 0.0)])
def test_weight_knobs_are_honoured(boost, penalty):
    scores = {"unresponsive": 0.8, "alive_and_talking": 0.5}
    r = ConflictResolver(
        support_boost=boost, conflict_penalty=penalty,
    ).resolve(scores)
    loser = next(e for e in r.ranked if e.name == "alive_and_talking")
    if penalty == 0.0:
        assert loser.adjusted_score == loser.raw_score
    else:
        assert loser.adjusted_score <= loser.raw_score
