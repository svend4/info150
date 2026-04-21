"""7-axis heptagram radar signature.

Adapted from svend4/infom — ``signatures/heptagram.py``. Upstream has no
LICENSE file; for lineage see ``third_party/ATTRIBUTION.md``. Pure Python,
no external dependencies.

Original 7 axes:
    strength, direction, temporal, confidence, scale, context, source.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


N_RAYS = 7

RAY_LABELS: list[str] = [
    "strength",
    "direction",
    "temporal",
    "confidence",
    "scale",
    "context",
    "source",
]


@dataclass
class Ray:
    """Single ray of a heptagram."""

    index: int
    label: str
    length: float  # 0..1
    angle: float  # radians, in XY plane
    curve: float  # 0=straight, 1=max curvature
    z: float  # 3D elevation out of the XY plane

    @property
    def endpoint_3d(self) -> tuple[float, float, float]:
        x = self.length * math.cos(self.angle)
        y = self.length * math.sin(self.angle)
        return (x, y, self.z)

    @property
    def endpoint_2d(self) -> tuple[float, float]:
        return (self.length * math.cos(self.angle), self.length * math.sin(self.angle))


@dataclass
class HeptagramSignature:
    """Seven-ray star aggregating a multidimensional relation."""

    rays: list[Ray]
    center: tuple[float, float, float] = (0.0, 0.0, 0.0)
    is_3d: bool = True
    total_energy: float = 0.0

    def __post_init__(self) -> None:
        self.total_energy = sum(r.length for r in self.rays) / N_RAYS

    @property
    def dominant_ray(self) -> Ray:
        return max(self.rays, key=lambda r: r.length)

    @property
    def symmetry_score(self) -> float:
        lengths = [r.length for r in self.rays]
        mean = sum(lengths) / len(lengths)
        variance = sum((x - mean) ** 2 for x in lengths) / len(lengths)
        return 1.0 / (1.0 + variance * 10)

    def to_vector(self) -> list[float]:
        return (
            [r.length for r in self.rays]
            + [r.curve for r in self.rays]
            + [r.z for r in self.rays]
        )


def heptagram_distance(a: HeptagramSignature, b: HeptagramSignature) -> float:
    """L2 distance over the 21-dim [length, curve, z] vector."""
    va, vb = a.to_vector(), b.to_vector()
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(va, vb)))


def build_heptagram_signature(
    relation_weights: dict[str, float],
) -> HeptagramSignature:
    """Build a HeptagramSignature from a 7-dim weight dict (missing → 0.5)."""
    base_angle = 2 * math.pi / N_RAYS
    rays: list[Ray] = []
    for i, label in enumerate(RAY_LABELS):
        length = max(0.0, min(1.0, float(relation_weights.get(label, 0.5))))
        angle = base_angle * i
        curve = length * 0.3
        z = length * 0.5 * math.sin(angle)
        rays.append(
            Ray(
                index=i,
                label=label,
                length=length,
                angle=angle,
                curve=curve,
                z=z,
            )
        )
    return HeptagramSignature(rays=rays, is_3d=True)


def heptagram_from_edge_weights(
    nodes: list[str],
    edge_weights: list[tuple[str, str, float]],
) -> HeptagramSignature:
    """Derive a HeptagramSignature from a list of weighted edges."""
    if not edge_weights:
        return build_heptagram_signature({})

    weights = [w for _, _, w in edge_weights]
    n_edges = len(weights)
    mean_w = sum(weights) / n_edges
    max_w = max(weights)
    min_w = min(weights)
    variance = sum((w - mean_w) ** 2 for w in weights) / n_edges

    pairs = {(a, b): w for a, b, w in edge_weights}
    directed = sum(
        1
        for a, b, w in edge_weights
        if (b, a) not in pairs or abs(pairs[(b, a)] - w) > 0.1
    )
    direction = directed / n_edges

    return build_heptagram_signature(
        {
            "strength": mean_w,
            "direction": direction,
            "temporal": variance,
            "confidence": 1.0 - (max_w - min_w),
            "scale": min(1.0, n_edges / 10),
            "context": max_w,
            "source": mean_w * (1.0 - variance),
        }
    )
