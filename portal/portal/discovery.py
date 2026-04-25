"""Deterministic bridge-discovery rules.

One function per ``BridgeKind``. All rules are pure
deterministic functions over a list of ``PortalEntry``
inputs — NO ML, NO embeddings, NO time-of-day randomness.
Rules can be re-ordered or disabled freely; downstream
code never depends on emission order beyond what
``BridgeRegistry`` deduplicates.

Why "rules" rather than "discovery" plural: each rule
emits one ``BridgeKind``, so they compose by simple
extend.

Symmetry convention:
- Symmetric kinds (CO_OCCURRENCE, DOMAIN_NEIGHBOR,
  GEOGRAPHIC_NEIGHBOR, TEMPORAL_CORRELATE, ANALOGY) emit
  one direction only — the pair (i, j) where ``i < j`` in
  the input list — to avoid double-counting.
- ESCALATION is asymmetric (watch -> urgent), emitted in
  the direction the discovery rule observed.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from .coords import SIBLING_COORDS, coord_for, hamming
from .protocol import Bridge, BridgeKind, PortalEntry


# Number of leading "-"-separated tokens that must match
# for two location handles to count as geographically
# adjacent. ``"watershed-A-pen-12"`` and
# ``"watershed-A-station-3"`` share the first two tokens.
_GEO_PREFIX_TOKENS: int = 2


def _geo_prefix(handle: str) -> tuple[str, ...]:
    parts = tuple(p for p in handle.split("-") if p)
    return parts[:_GEO_PREFIX_TOKENS]


def discover_co_occurrence(
    entries: Sequence[PortalEntry],
) -> list[Bridge]:
    """Same kind + both urgent, different siblings → co-occurrence.

    Rationale: when two siblings independently fire
    *urgent* on the same channel name (``mortality_floor``,
    ``gait``, …), it is more likely the upstream
    environmental cause is shared than that two unrelated
    events coincidentally landed in the same batch.
    """
    out: list[Bridge] = []
    for i, a in enumerate(entries):
        if a.level != "urgent":
            continue
        for b in entries[i + 1:]:
            if b.sibling_id == a.sibling_id:
                continue
            if a.kind != b.kind:
                continue
            if b.level != "urgent":
                continue
            out.append(Bridge(
                kind=BridgeKind.CO_OCCURRENCE,
                from_key=a.key,
                to_key=b.key,
                evidence=(
                    f"both siblings urgent on channel {a.kind!r}"
                ),
            ))
    return out


def discover_domain_neighbor(
    entries: Sequence[PortalEntry],
) -> list[Bridge]:
    """Different-sibling pairs at Hamming distance ≤ 1, both urgent.

    Rationale: domain-adjacent siblings (``triage4-bird`` +
    ``triage4-wild``: both wild + environmental) firing
    urgent in the same batch suggests the same upstream
    domain event surfaced in two adjacent observation
    pipelines.

    Siblings without a registered coordinate are skipped
    (no error — participation is optional).
    """
    out: list[Bridge] = []
    for i, a in enumerate(entries):
        if a.level != "urgent" or a.sibling_id not in SIBLING_COORDS:
            continue
        ca = coord_for(a.sibling_id)
        for b in entries[i + 1:]:
            if b.sibling_id == a.sibling_id:
                continue
            if b.level != "urgent" or b.sibling_id not in SIBLING_COORDS:
                continue
            cb = coord_for(b.sibling_id)
            d = hamming(ca, cb)
            if d > 1:
                continue
            out.append(Bridge(
                kind=BridgeKind.DOMAIN_NEIGHBOR,
                from_key=a.key,
                to_key=b.key,
                evidence=(
                    f"sibling coords differ by {d} "
                    f"({a.sibling_id} ~ {b.sibling_id})"
                ),
            ))
    return out


def discover_geographic_neighbor(
    entries: Sequence[PortalEntry],
) -> list[Bridge]:
    """Different siblings sharing a location-handle prefix.

    Uses the first ``_GEO_PREFIX_TOKENS`` ``-``-separated
    tokens of each handle. Empty prefixes (handles with no
    delimiter) never match.

    Rationale: siblings observing the same watershed /
    grid-cell from different angles (fish-pens vs ranger
    stations vs bird-acoustic monitors) co-locate the
    cause in space.
    """
    out: list[Bridge] = []
    for i, a in enumerate(entries):
        ap = _geo_prefix(a.location_handle)
        if len(ap) < _GEO_PREFIX_TOKENS:
            continue
        for b in entries[i + 1:]:
            if b.sibling_id == a.sibling_id:
                continue
            bp = _geo_prefix(b.location_handle)
            if ap != bp:
                continue
            out.append(Bridge(
                kind=BridgeKind.GEOGRAPHIC_NEIGHBOR,
                from_key=a.key,
                to_key=b.key,
                evidence=(
                    f"shared location prefix {'-'.join(ap)!r}"
                ),
            ))
    return out


def _windows_overlap(
    a: tuple[float, float], b: tuple[float, float],
) -> bool:
    return not (a[1] < b[0] or b[1] < a[0])


def discover_temporal_correlate(
    entries: Sequence[PortalEntry],
) -> list[Bridge]:
    """Different siblings with overlapping ``t_window``, level ≥ watch.

    Rationale: if a fish-pen alert at t=[100, 160] overlaps
    a bird-station alert at t=[120, 200], they're temporally
    correlated. The ``level >= watch`` filter keeps
    ``steady`` entries from carpeting the registry with
    edges.
    """
    out: list[Bridge] = []
    for i, a in enumerate(entries):
        if a.t_window is None or a.level == "steady":
            continue
        for b in entries[i + 1:]:
            if b.sibling_id == a.sibling_id:
                continue
            if b.t_window is None or b.level == "steady":
                continue
            if not _windows_overlap(a.t_window, b.t_window):
                continue
            out.append(Bridge(
                kind=BridgeKind.TEMPORAL_CORRELATE,
                from_key=a.key,
                to_key=b.key,
                evidence=(
                    f"windows overlap: {a.t_window} ∩ {b.t_window}"
                ),
            ))
    return out


def discover_escalation(
    entries: Sequence[PortalEntry],
) -> list[Bridge]:
    """Watch + urgent on the same kind name → asymmetric escalation.

    Direction: ``watch -> urgent``. Different siblings
    only. Useful when one sibling sees an early signal at
    *watch* tier while a domain-adjacent sibling has
    already escalated to *urgent* — the watch entry should
    inherit attention from the urgent one.
    """
    out: list[Bridge] = []
    for a in entries:
        if a.level != "watch":
            continue
        for b in entries:
            if b.sibling_id == a.sibling_id:
                continue
            if a.kind != b.kind:
                continue
            if b.level != "urgent":
                continue
            out.append(Bridge(
                kind=BridgeKind.ESCALATION,
                from_key=a.key,
                to_key=b.key,
                evidence=(
                    f"watch-tier {a.sibling_id}/{a.kind} adjacent to "
                    f"urgent-tier {b.sibling_id}/{b.kind}"
                ),
            ))
    return out


# Kind-name fragments that mark a "mortality-flavoured"
# channel across siblings. Different siblings name their
# channels differently; ANALOGY uses substring matches
# rather than exact-equality so a fish ``mortality_floor``
# pairs with a bird ``mortality_cluster``.
_MORTALITY_FRAGMENTS: tuple[str, ...] = ("mortality", "die_off", "necrosis")


def discover_analogy(
    entries: Sequence[PortalEntry],
) -> list[Bridge]:
    """Mortality-flavoured urgent pairs across siblings.

    Lower-precision than CO_OCCURRENCE — the kind names
    don't have to match exactly, only share a mortality
    fragment. Most brittle of the six rules; keeps explicit
    evidence so a reviewer can decide whether the analogy
    is meaningful for their consumer.
    """
    out: list[Bridge] = []
    for i, a in enumerate(entries):
        if a.level != "urgent":
            continue
        if not any(f in a.kind for f in _MORTALITY_FRAGMENTS):
            continue
        for b in entries[i + 1:]:
            if b.sibling_id == a.sibling_id:
                continue
            if b.level != "urgent":
                continue
            if not any(f in b.kind for f in _MORTALITY_FRAGMENTS):
                continue
            # Skip exact-equal kinds — those are CO_OCCURRENCE
            # already and ANALOGY is for non-identical names.
            if a.kind == b.kind:
                continue
            out.append(Bridge(
                kind=BridgeKind.ANALOGY,
                from_key=a.key,
                to_key=b.key,
                evidence=(
                    f"mortality-flavoured analogy: "
                    f"{a.kind!r} ~ {b.kind!r}"
                ),
            ))
    return out


def discover_all(entries: Iterable[PortalEntry]) -> list[Bridge]:
    """Run every rule, return concatenated bridges.

    Caller deduplicates via ``BridgeRegistry.extend``.
    """
    items = list(entries)
    bridges: list[Bridge] = []
    bridges.extend(discover_co_occurrence(items))
    bridges.extend(discover_domain_neighbor(items))
    bridges.extend(discover_geographic_neighbor(items))
    bridges.extend(discover_temporal_correlate(items))
    bridges.extend(discover_escalation(items))
    bridges.extend(discover_analogy(items))
    return bridges


__all__ = [
    "discover_all",
    "discover_analogy",
    "discover_co_occurrence",
    "discover_domain_neighbor",
    "discover_escalation",
    "discover_geographic_neighbor",
    "discover_temporal_correlate",
]
