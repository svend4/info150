"""In-memory typed bridge registry.

No persistence. No external store. The registry is a thin
container the discovery layer fills in and the CLI / consumers
read out. Kept minimal on purpose — once we have a real
consumer that needs persistence we can add it without
changing this surface.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from .protocol import Bridge, BridgeKind


class BridgeRegistry:
    """Append-only set of typed bridges.

    Edges are deduplicated on the
    ``(kind, from_key, to_key)`` triple. Direction matters
    for asymmetric kinds (``ESCALATION``) so we do not
    canonicalise endpoint order.
    """

    def __init__(self) -> None:
        self._edges: list[Bridge] = []
        self._seen: set[tuple[BridgeKind, tuple[str, str], tuple[str, str]]] \
            = set()

    def add(self, bridge: Bridge) -> bool:
        """Add a bridge; return True if newly inserted."""
        key = (bridge.kind, bridge.from_key, bridge.to_key)
        if key in self._seen:
            return False
        self._seen.add(key)
        self._edges.append(bridge)
        return True

    def extend(self, bridges: Iterable[Bridge]) -> int:
        """Bulk-add; return count of newly inserted edges."""
        count = 0
        for b in bridges:
            if self.add(b):
                count += 1
        return count

    def by_kind(self, kind: BridgeKind) -> list[Bridge]:
        return [b for b in self._edges if b.kind == kind]

    def incident_to(self, entry_key: tuple[str, str]) -> list[Bridge]:
        """All bridges where ``entry_key`` is either endpoint."""
        return [
            b for b in self._edges
            if b.from_key == entry_key or b.to_key == entry_key
        ]

    def __len__(self) -> int:
        return len(self._edges)

    def __iter__(self) -> Iterator[Bridge]:
        return iter(self._edges)


__all__ = ["BridgeRegistry"]
