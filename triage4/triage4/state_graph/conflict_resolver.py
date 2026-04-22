"""K3-2.2 — Conflict resolution across trauma hypotheses.

Closes the "conflict_resolver" cell of the K3 matrix. Sits between
``BodyStateGraph`` (which aggregates evidence into hypothesis scores)
and any consumer that wants a *coherent* ranked list (explainability,
dashboard, handoff).

The problem: evidence can push two mutually-contradictory hypotheses
at the same time ("unresponsive" and "alive_and_talking", for
example). The raw score map has no way to say *these two cannot both
be true*. This module takes:

- the raw hypothesis scores (e.g. from ``BodyStateGraph``),
- a set of **support** pairs (A reinforces B),
- a set of **conflict** pairs (A and B are mutually exclusive),

and returns a ``ResolvedHypotheses`` with:

- per-hypothesis adjusted scores (boosted by supporters, penalised
  by stronger competitors),
- per-conflict-group winners (the strongest hypothesis in each
  exclusion clique),
- a list of reasons explaining each adjustment.

Design goals: pure Python stdlib, deterministic, auditable,
round-tripable. No ML, no solvers — a single-pass score adjustment
that a clinician can read.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# Default knowledge base. Curated from Phase 9c's trauma-hypothesis
# vocabulary — kept short and clinically defensible.
_DEFAULT_SUPPORT: frozenset[frozenset[str]] = frozenset(
    frozenset(pair) for pair in (
        ("hemorrhage_risk", "shock_risk"),
        ("hemorrhage_major", "shock"),
        ("respiratory_distress", "unresponsive"),
        ("severe_trauma_suspicion", "shock_risk"),
    )
)

_DEFAULT_CONFLICT: frozenset[frozenset[str]] = frozenset(
    frozenset(pair) for pair in (
        ("unresponsive", "alive_and_talking"),
        ("minimal_priority", "immediate_priority"),
        ("minimal_priority", "severe_trauma_suspicion"),
        ("stable_breathing", "respiratory_distress"),
    )
)

# Adjustment weights — kept small so the winner of each conflict
# group stays the one the raw scores favour; the resolver refines
# confidence, it does not invert rankings.
_SUPPORT_BOOST = 0.15
_CONFLICT_PENALTY = 0.25
_MIN_SCORE = 0.0
_MAX_SCORE = 1.0


@dataclass
class ResolvedHypothesis:
    """One entry in the resolved ranking."""

    name: str
    raw_score: float
    adjusted_score: float
    suppressed: bool
    reasons: list[str] = field(default_factory=list)


@dataclass
class ConflictGroup:
    """A set of mutually-exclusive hypotheses + the winner within it."""

    members: list[str]
    winner: str | None
    winner_score: float


@dataclass
class ResolvedHypotheses:
    ranked: list[ResolvedHypothesis]
    groups: list[ConflictGroup]


def _clamp(v: float) -> float:
    return max(_MIN_SCORE, min(_MAX_SCORE, float(v)))


class ConflictResolver:
    """Reconcile raw hypothesis scores into a coherent ranking."""

    def __init__(
        self,
        support: frozenset[frozenset[str]] | None = None,
        conflict: frozenset[frozenset[str]] | None = None,
        support_boost: float = _SUPPORT_BOOST,
        conflict_penalty: float = _CONFLICT_PENALTY,
    ) -> None:
        self.support = support if support is not None else _DEFAULT_SUPPORT
        self.conflict = conflict if conflict is not None else _DEFAULT_CONFLICT
        self.support_boost = float(support_boost)
        self.conflict_penalty = float(conflict_penalty)

        # Pre-compute neighbour maps for single-pass lookup.
        self._support_neighbours: dict[str, set[str]] = {}
        for pair in self.support:
            a, b = list(pair)
            self._support_neighbours.setdefault(a, set()).add(b)
            self._support_neighbours.setdefault(b, set()).add(a)

        self._conflict_neighbours: dict[str, set[str]] = {}
        for pair in self.conflict:
            a, b = list(pair)
            self._conflict_neighbours.setdefault(a, set()).add(b)
            self._conflict_neighbours.setdefault(b, set()).add(a)

    def resolve(self, raw_scores: dict[str, float]) -> ResolvedHypotheses:
        if not raw_scores:
            return ResolvedHypotheses(ranked=[], groups=[])

        # 1. Start from raw scores, apply support boosts, conflict
        #    penalties. Each adjustment is bounded by a single constant
        #    step, so adjustments are commutative w.r.t. ordering.
        entries: dict[str, ResolvedHypothesis] = {
            name: ResolvedHypothesis(
                name=name,
                raw_score=_clamp(score),
                adjusted_score=_clamp(score),
                suppressed=False,
            )
            for name, score in raw_scores.items()
        }

        for name, entry in entries.items():
            # Support boost — additive, capped.
            for neighbour in self._support_neighbours.get(name, set()):
                if neighbour in entries:
                    boost = self.support_boost * entries[neighbour].raw_score
                    if boost > 0:
                        entry.adjusted_score = _clamp(entry.adjusted_score + boost)
                        entry.reasons.append(
                            f"supported by {neighbour} (+{boost:.3f})"
                        )

            # Conflict penalty — competitor's raw strength drives it down.
            for competitor in self._conflict_neighbours.get(name, set()):
                if competitor in entries:
                    competitor_score = entries[competitor].raw_score
                    if competitor_score > entry.raw_score:
                        penalty = self.conflict_penalty * competitor_score
                        entry.adjusted_score = _clamp(
                            entry.adjusted_score - penalty
                        )
                        entry.reasons.append(
                            f"outweighed by {competitor} (-{penalty:.3f})"
                        )

        # 2. Group conflict cliques. For each connected component in the
        #    conflict graph restricted to observed hypotheses, pick the
        #    single winner by adjusted score; mark all others suppressed.
        groups = self._build_conflict_groups(entries)
        for group in groups:
            if group.winner is None:
                continue
            for member in group.members:
                if member != group.winner and member in entries:
                    entries[member].suppressed = True
                    if group.winner_score > 0:
                        entries[member].reasons.append(
                            f"suppressed by conflict group winner {group.winner}"
                        )

        # 3. Rank. Suppressed hypotheses sink; ties broken by adjusted score,
        #    then raw score, then name (stable ordering).
        ranked = sorted(
            entries.values(),
            key=lambda e: (
                e.suppressed,
                -e.adjusted_score,
                -e.raw_score,
                e.name,
            ),
        )
        # Round the floats for readability.
        for e in ranked:
            e.adjusted_score = round(e.adjusted_score, 3)
            e.raw_score = round(e.raw_score, 3)
        return ResolvedHypotheses(ranked=ranked, groups=groups)

    # ------------------------------------------------------------------

    def _build_conflict_groups(
        self, entries: dict[str, ResolvedHypothesis]
    ) -> list[ConflictGroup]:
        observed = set(entries)
        visited: set[str] = set()
        groups: list[ConflictGroup] = []

        for seed in sorted(observed):
            if seed in visited:
                continue
            conflicts = self._conflict_neighbours.get(seed, set()) & observed
            if not conflicts:
                continue
            component = self._bfs_conflict_component(seed, observed)
            visited.update(component)
            if len(component) < 2:
                continue
            winner = max(
                component,
                key=lambda n: (entries[n].adjusted_score, entries[n].raw_score, n),
            )
            groups.append(
                ConflictGroup(
                    members=sorted(component),
                    winner=winner,
                    winner_score=round(entries[winner].adjusted_score, 3),
                )
            )
        return groups

    def _bfs_conflict_component(self, seed: str, observed: set[str]) -> set[str]:
        component: set[str] = {seed}
        frontier = [seed]
        while frontier:
            current = frontier.pop()
            for neighbour in self._conflict_neighbours.get(current, set()):
                if neighbour in observed and neighbour not in component:
                    component.add(neighbour)
                    frontier.append(neighbour)
        return component
