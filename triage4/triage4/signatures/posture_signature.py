"""Posture instability signature.

Part of triage4 Phase 7 (multimodal). Reads body-region polygons (see
``triage4.perception.body_regions``) and produces a posture descriptor:

- ``posture_instability_score`` — how much the body deviates from a
  standing / balanced layout;
- ``asymmetry_score`` — left/right asymmetry of arms and legs;
- ``collapse_score`` — whether torso is low (horizontal) compared to legs,
  suggesting the casualty is lying down or collapsed.

Compared to the real pose-driven implementation, this is intentionally
simple: it works off the polygon centroids and their relative geometry,
so it runs with the existing ``BodyRegionPolygonizer`` output.
"""

from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np


Polygon = Sequence[tuple[float, float]]


def _centroid(polygon: Polygon) -> tuple[float, float]:
    pts = np.asarray(polygon, dtype=np.float64)
    if pts.size == 0:
        return (0.0, 0.0)
    return (float(pts[:, 0].mean()), float(pts[:, 1].mean()))


def _bbox(polygon: Polygon) -> tuple[float, float, float, float]:
    pts = np.asarray(polygon, dtype=np.float64)
    if pts.size == 0:
        return (0.0, 0.0, 0.0, 0.0)
    return (
        float(pts[:, 0].min()),
        float(pts[:, 1].min()),
        float(pts[:, 0].max()),
        float(pts[:, 1].max()),
    )


class PostureSignatureExtractor:
    """Posture descriptor from named body-region polygons."""

    def extract(self, regions: Mapping[str, Polygon]) -> dict:
        required = {"head", "torso", "left_arm", "right_arm", "left_leg", "right_leg"}
        if not required.issubset(regions.keys()):
            return {
                "posture_instability_score": 0.0,
                "asymmetry_score": 0.0,
                "collapse_score": 0.0,
                "quality_score": 0.0,
            }

        head_c = _centroid(regions["head"])
        torso_c = _centroid(regions["torso"])
        l_arm_c = _centroid(regions["left_arm"])
        r_arm_c = _centroid(regions["right_arm"])
        l_leg_c = _centroid(regions["left_leg"])
        r_leg_c = _centroid(regions["right_leg"])

        torso_box = _bbox(regions["torso"])
        torso_h = torso_box[3] - torso_box[1]
        torso_w = torso_box[2] - torso_box[0]

        # Scale used to normalise distances. Fall back to 1.0 so we never
        # divide by zero even on a degenerate polygonisation.
        scale = max(1.0, torso_h)

        # Left/right arm and leg asymmetry (y-axis offset of matching pair).
        arm_asym = abs(l_arm_c[1] - r_arm_c[1]) / scale
        leg_asym = abs(l_leg_c[1] - r_leg_c[1]) / scale
        asymmetry = float(min(1.0, 0.5 * (arm_asym + leg_asym) * 1.5))

        # Collapse: torso wider than tall or head dropping below torso bottom.
        # Returns a value in [0, 1]; high when the body is laid out like a
        # fallen silhouette instead of a standing one.
        torso_ratio = torso_w / max(torso_h, 1e-6)
        head_below_torso_base = head_c[1] > torso_box[3]
        collapse_ratio = max(0.0, torso_ratio - 0.55) / 1.5
        collapse = float(
            min(
                1.0,
                collapse_ratio + (0.5 if head_below_torso_base else 0.0),
            )
        )

        # Torso-leg alignment: the torso centroid should be roughly above the
        # mid-point of the legs in a standing pose. Any lateral shift is
        # posture instability.
        legs_midx = 0.5 * (l_leg_c[0] + r_leg_c[0])
        lateral_shift = abs(torso_c[0] - legs_midx) / max(torso_w, 1e-6)
        lateral_instability = float(min(1.0, lateral_shift * 1.5))

        posture_instability = float(
            min(1.0, 0.5 * collapse + 0.3 * asymmetry + 0.2 * lateral_instability)
        )

        quality = 1.0 if torso_h > 1.0 else 0.3

        return {
            "posture_instability_score": round(posture_instability, 3),
            "asymmetry_score": round(asymmetry, 3),
            "collapse_score": round(collapse, 3),
            "quality_score": round(quality, 3),
        }
