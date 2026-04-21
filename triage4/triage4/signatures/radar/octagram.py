"""8-axis octagram compass signature (3D).

Adapted from svend4/infom — ``signatures/octagram.py``. Upstream has no
LICENSE file; for lineage see ``third_party/ATTRIBUTION.md``. Pure Python,
no external dependencies.

8 compass directions (N, NE, E, SE, S, SW, W, NW) with semantic axis
labels and optional 3D elevation out of the XY plane.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


N_RAYS = 8

COMPASS: list[str] = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

AXIS_SEMANTICS: dict[tuple[str, str], tuple[str, str]] = {
    ("N", "S"): ("abstract", "concrete"),
    ("E", "W"): ("future", "past"),
    ("NE", "SW"): ("complex", "simple"),
    ("NW", "SE"): ("global", "local"),
}


class SkeletonType(Enum):
    TOWER = "tower"
    SHELL = "shell"
    CONE = "cone"
    FRACTAL = "fractal"
    SPHERE = "sphere"


@dataclass
class OctaRay:
    direction: str
    length: float  # 0..1
    angle_2d: float
    elevation: float
    weight: float

    @property
    def endpoint_3d(self) -> tuple[float, float, float]:
        r = self.length
        x = r * math.cos(self.elevation) * math.cos(self.angle_2d)
        y = r * math.cos(self.elevation) * math.sin(self.angle_2d)
        z = r * math.sin(self.elevation)
        return (x, y, z)


@dataclass
class OctagramSignature:
    rays: list[OctaRay]
    skeleton_type: SkeletonType
    center_3d: tuple[float, float, float] = (0.0, 0.0, 0.0)

    @property
    def dominant_axis(self) -> tuple[str, str]:
        compass_map = {r.direction: r.length for r in self.rays}
        best: tuple[str, str] = ("N", "S")
        best_sum = 0.0
        for (d1, d2), _ in AXIS_SEMANTICS.items():
            s = compass_map.get(d1, 0.0) + compass_map.get(d2, 0.0)
            if s > best_sum:
                best, best_sum = (d1, d2), s
        return best

    @property
    def is_flat(self) -> bool:
        return all(abs(r.elevation) < 0.1 for r in self.rays)

    def to_vector(self) -> list[float]:
        return [r.length for r in self.rays] + [r.elevation for r in self.rays]

    def skeleton_vertices(self) -> list[tuple[float, float, float]]:
        verts = [self.center_3d]
        verts += [r.endpoint_3d for r in self.rays]
        return verts

    def skeleton_edges(self) -> list[tuple[int, int]]:
        edges = [(0, i + 1) for i in range(N_RAYS)]
        for i in range(N_RAYS):
            edges.append((i + 1, (i + 1) % N_RAYS + 1))
        return edges


def octagram_distance(a: OctagramSignature, b: OctagramSignature) -> float:
    va, vb = a.to_vector(), b.to_vector()
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(va, vb)))


def _detect_skeleton_type(rays: list[OctaRay]) -> SkeletonType:
    lengths = [r.length for r in rays]
    elevs = [abs(r.elevation) for r in rays]
    mean_l = sum(lengths) / len(lengths)
    variance = sum((x - mean_l) ** 2 for x in lengths) / len(lengths)
    mean_e = sum(elevs) / len(elevs)

    if variance < 0.02:
        return SkeletonType.SPHERE
    if mean_e > 0.4:
        spiral = sum(
            1 for i in range(len(rays)) if rays[i].elevation > rays[i - 1].elevation
        )
        return SkeletonType.SHELL if spiral > 4 else SkeletonType.CONE
    if lengths[0] > lengths[4] * 1.5:
        return SkeletonType.TOWER
    return SkeletonType.FRACTAL


def build_octagram_signature(
    direction_weights: dict[str, float],
    elevation_profile: dict[str, float] | None = None,
) -> OctagramSignature:
    if elevation_profile is None:
        elevation_profile = {}

    base_angle = 2 * math.pi / N_RAYS
    rays: list[OctaRay] = []
    for i, compass_dir in enumerate(COMPASS):
        length = max(0.0, min(1.0, float(direction_weights.get(compass_dir, 0.5))))
        angle_2d = base_angle * i
        elevation = elevation_profile.get(compass_dir, 0.0)
        if elevation == 0.0:
            elevation = (length - 0.5) * math.pi / 4
        rays.append(
            OctaRay(
                direction=compass_dir,
                length=length,
                angle_2d=angle_2d,
                elevation=elevation,
                weight=length,
            )
        )

    skeleton = _detect_skeleton_type(rays)
    return OctagramSignature(rays=rays, skeleton_type=skeleton)


def build_shell_octagram(n_turns: float = 1.5) -> OctagramSignature:
    """Fibonacci-shell octagram — rays spiral with the golden ratio."""
    phi = (1 + math.sqrt(5)) / 2
    rays: list[OctaRay] = []
    for i, compass_dir in enumerate(COMPASS):
        t = i / N_RAYS
        length = 0.3 + 0.7 * (phi ** (t * n_turns)) / (phi ** n_turns)
        angle_2d = 2 * math.pi * t
        elevation = math.pi / 4 * math.sin(2 * math.pi * t)
        rays.append(
            OctaRay(
                direction=compass_dir,
                length=min(1.0, length),
                angle_2d=angle_2d,
                elevation=elevation,
                weight=length,
            )
        )
    return OctagramSignature(rays=rays, skeleton_type=SkeletonType.SHELL)


def build_tower_octagram(n_levels: int = 4) -> OctagramSignature:
    """Tower octagram — rays arranged as an abstraction hierarchy."""
    _ = n_levels  # reserved for future ``HexGrid``-aware layouts
    directions = dict(zip(COMPASS, [0.9, 0.6, 0.7, 0.5, 0.8, 0.4, 0.6, 0.5]))
    elevations = {
        "N": math.pi / 3,
        "NE": math.pi / 6,
        "E": 0.0,
        "SE": -math.pi / 6,
        "S": -math.pi / 3,
        "SW": -math.pi / 4,
        "W": 0.0,
        "NW": math.pi / 4,
    }
    return build_octagram_signature(directions, elevations)
