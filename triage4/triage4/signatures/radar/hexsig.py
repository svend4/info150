"""Q6 hypercube positional signature.

Adapted from svend4/infom — ``signatures/hexsig.py``. Upstream has no
LICENSE file; for lineage see ``third_party/ATTRIBUTION.md``. Pure Python,
no external dependencies.

Q6 = 6-dimensional binary hypercube (64 nodes, diameter 6). A fingerprint
is a 6-bit code assigned to an entity by average-pooling a high-dim
embedding into 6 chunks and thresholding each chunk at the mean.

Triage use case:
- Fast categorical fingerprint of a casualty's multi-axis profile
  (severity / deterioration / occlusion / cooperativeness / posture / …).
- Hamming distance on 6 bits = ~ instantaneous nearest-neighbour.
- Voronoi and Delaunay in Q6 give a compact clustering substrate.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass


N_DIMS = 6
N_NODES = 64  # 2 ** N_DIMS
MAX_DIST = N_DIMS
DEGREE = N_DIMS

DISTANCE_SPECTRUM = [math.comb(N_DIMS, r) for r in range(N_DIMS + 1)]


@dataclass
class HexSignature:
    """Position of an entity inside Q6."""

    hex_id: int
    voronoi_id: int
    hamming_r: int
    bits: tuple[int, ...]

    @property
    def archetype_bits(self) -> dict[str, int]:
        """Named axes of the Q6 position (from upstream semantics)."""
        b = self.bits
        return {
            "material": b[0],
            "dynamic": b[1],
            "complex": b[2],
            "ordered": b[3],
            "local": b[4],
            "explicit": b[5],
        }


# --- basic Q6 operations -----------------------------------------------------


def to_bits(h: int) -> tuple[int, ...]:
    return tuple((h >> i) & 1 for i in range(N_DIMS))


def from_bits(bits: tuple[int, ...]) -> int:
    return sum(b << i for i, b in enumerate(bits))


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def neighbors(h: int) -> list[int]:
    return [h ^ (1 << i) for i in range(N_DIMS)]


def antipode(h: int) -> int:
    return h ^ (N_NODES - 1)


def hamming_ball(center: int, radius: int) -> list[int]:
    return [h for h in range(N_NODES) if hamming(center, h) <= radius]


def hamming_sphere(center: int, radius: int) -> list[int]:
    return [h for h in range(N_NODES) if hamming(center, h) == radius]


def bfs_distances(start: int) -> list[int]:
    dist = [-1] * N_NODES
    dist[start] = 0
    queue: deque[int] = deque([start])
    while queue:
        h = queue.popleft()
        for nb in neighbors(h):
            if dist[nb] < 0:
                dist[nb] = dist[h] + 1
                queue.append(nb)
    return dist


def shortest_path(a: int, b: int) -> list[int]:
    """BFS shortest path from a to b in Q6."""
    if a == b:
        return [a]
    dist = bfs_distances(a)
    path = [b]
    cur = b
    while cur != a:
        for nb in neighbors(cur):
            if dist[nb] == dist[cur] - 1:
                path.append(nb)
                cur = nb
                break
    path.reverse()
    return path


def metric_interval(u: int, v: int) -> list[int]:
    """All nodes lying on at least one shortest u→v path."""
    d_uv = hamming(u, v)
    du = bfs_distances(u)
    dv = bfs_distances(v)
    return [h for h in range(N_NODES) if du[h] + dv[h] == d_uv]


def median(points: list[int]) -> int:
    """Bitwise-majority Steiner point."""
    result = 0
    for bit in range(N_DIMS):
        ones = sum((p >> bit) & 1 for p in points)
        if ones > len(points) / 2:
            result |= 1 << bit
    return result


# --- Voronoi / Delaunay ------------------------------------------------------


def voronoi_cells(centers: list[int]) -> dict[int, list[int]]:
    cells: dict[int, list[int]] = {c: [] for c in centers}
    for h in range(N_NODES):
        nearest = min(centers, key=lambda c: hamming(h, c))
        cells[nearest].append(h)
    return cells


def delaunay_graph(centers: list[int]) -> list[tuple[int, int]]:
    cells = voronoi_cells(centers)
    edges: set[tuple[int, int]] = set()
    for c1 in centers:
        for node in cells[c1]:
            for nb in neighbors(node):
                for c2 in centers:
                    if c2 != c1 and nb in cells[c2]:
                        edge = (min(c1, c2), max(c1, c2))
                        edges.add(edge)
    return list(edges)


# --- Sphere packing ----------------------------------------------------------


def packing_number(radius: int) -> list[int]:
    """Greedy packing of Q6 with non-overlapping Hamming balls of given radius."""
    covered: set[int] = set()
    centers: list[int] = []
    for h in range(N_NODES):
        if h not in covered:
            centers.append(h)
            covered.update(hamming_ball(h, radius))
    return centers


def is_perfect_code(centers: list[int], radius: int) -> bool:
    all_nodes: set[int] = set()
    for c in centers:
        ball = set(hamming_ball(c, radius))
        if ball & all_nodes:
            return False
        all_nodes |= ball
    return len(all_nodes) == N_NODES


# --- embedding projection ----------------------------------------------------


def embed_to_q6(embedding: list[float]) -> int:
    """Project a continuous embedding of any length to a 6-bit Q6 id."""
    n = len(embedding)
    if n <= N_DIMS:
        vals = [embedding[i] if i < n else 0.0 for i in range(N_DIMS)]
    else:
        chunk = n / N_DIMS
        vals = []
        for d in range(N_DIMS):
            start = int(d * chunk)
            end = int((d + 1) * chunk)
            if end <= start:
                end = start + 1
            chunk_vals = embedding[start:end]
            vals.append(sum(chunk_vals) / len(chunk_vals))

    mean = sum(vals) / N_DIMS
    if all(abs(v - mean) < 1e-10 for v in vals):
        bits = [1 if v > 0.5 else 0 for v in vals]
    else:
        bits = [1 if v > mean else 0 for v in vals]
    return from_bits(tuple(bits))


def build_hex_signature(
    embedding: list[float], voronoi_centers: list[int] | None = None
) -> HexSignature:
    hex_id = embed_to_q6(embedding)
    bits = to_bits(hex_id)

    if voronoi_centers:
        vid = min(voronoi_centers, key=lambda c: hamming(hex_id, c))
        r = hamming(hex_id, vid)
    else:
        vid = hex_id
        r = 0

    return HexSignature(hex_id=hex_id, voronoi_id=vid, hamming_r=r, bits=bits)
