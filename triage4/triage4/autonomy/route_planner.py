"""Graph-based route planner.

Adapted from svend4/in4n — ``2-react/src/App.jsx`` (the ``bfsPath``
function used by the force-graph traveler). In4n has no upstream LICENSE
file yet; the algorithm itself is textbook BFS so this is effectively
clean-room rewriting in Python with attribution-for-lineage.

Use in triage4:
- shortest-hop route for a robot / medic across the waypoint or
  mission-sector graph;
- fallback route when the triage graph is sparse (known edges only).
"""

from __future__ import annotations

from collections import deque
from typing import Hashable, Iterable


Edge = tuple[Hashable, Hashable]


def _build_adjacency(
    edges: Iterable[Edge], directed: bool = False
) -> dict[Hashable, list[Hashable]]:
    adj: dict[Hashable, list[Hashable]] = {}
    for a, b in edges:
        adj.setdefault(a, []).append(b)
        if not directed:
            adj.setdefault(b, []).append(a)
    return adj


def bfs_path(
    edges: Iterable[Edge],
    start: Hashable,
    end: Hashable,
    directed: bool = False,
) -> list[Hashable]:
    """Shortest-hop BFS path between ``start`` and ``end``.

    Returns the full path including endpoints, or ``[start]`` if no path
    exists (matching the in4n upstream behaviour).
    """
    if start == end:
        return [start]

    adj = _build_adjacency(edges, directed=directed)
    visited: set[Hashable] = {start}
    queue: deque[tuple[Hashable, list[Hashable]]] = deque([(start, [start])])

    while queue:
        cur, path = queue.popleft()
        for nb in adj.get(cur, []):
            if nb == end:
                return [*path, nb]
            if nb not in visited:
                visited.add(nb)
                queue.append((nb, [*path, nb]))

    return [start]


def all_shortest_paths(
    edges: Iterable[Edge],
    start: Hashable,
    directed: bool = False,
) -> dict[Hashable, list[Hashable]]:
    """Return shortest-hop paths from ``start`` to every reachable node."""
    adj = _build_adjacency(edges, directed=directed)
    paths: dict[Hashable, list[Hashable]] = {start: [start]}
    queue: deque[Hashable] = deque([start])
    while queue:
        cur = queue.popleft()
        for nb in adj.get(cur, []):
            if nb in paths:
                continue
            paths[nb] = [*paths[cur], nb]
            queue.append(nb)
    return paths


def plan_robot_route(
    mission_edges: Iterable[Edge],
    robot_node: Hashable,
    casualty_node: Hashable,
    directed: bool = False,
) -> list[Hashable]:
    """Plan a robot's route from its current node to a casualty node.

    Thin triage4-facing wrapper over ``bfs_path`` that fixes the argument
    order for readability at call sites.
    """
    return bfs_path(mission_edges, robot_node, casualty_node, directed=directed)
