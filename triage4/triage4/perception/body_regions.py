from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


Polygon = list[tuple[float, float]]


@dataclass
class BodyRegions:
    head: Polygon
    torso: Polygon
    left_arm: Polygon
    right_arm: Polygon
    left_leg: Polygon
    right_leg: Polygon

    def as_dict(self) -> dict[str, Polygon]:
        return {
            "head": self.head,
            "torso": self.torso,
            "left_arm": self.left_arm,
            "right_arm": self.right_arm,
            "left_leg": self.left_leg,
            "right_leg": self.right_leg,
        }


class BodyRegionPolygonizer:
    """Minimal tangram-like body decomposition.

    Simulation-friendly. Builds head / torso / arms / legs polygons from a bbox
    or a center point. Later replaceable by a pose-driven implementation.
    """

    def build_from_bbox(self, bbox: Iterable[float]) -> dict[str, Polygon]:
        x1, y1, x2, y2 = (float(v) for v in bbox)
        w = max(1.0, x2 - x1)
        h = max(1.0, y2 - y1)

        cx = x1 + w * 0.5

        head_h = h * 0.18
        torso_h = h * 0.32
        arm_h = h * 0.28
        leg_h = h * 0.32

        shoulder_y = y1 + head_h
        torso_y2 = shoulder_y + torso_h
        hip_y = torso_y2
        foot_y = min(y2, hip_y + leg_h)

        head_w = w * 0.34
        torso_w = w * 0.42
        arm_w = w * 0.18
        leg_w = w * 0.16
        leg_gap = w * 0.06

        head = self._rect(cx - head_w / 2, y1, cx + head_w / 2, shoulder_y)
        torso = self._rect(cx - torso_w / 2, shoulder_y, cx + torso_w / 2, torso_y2)
        left_arm = self._rect(
            cx - torso_w / 2 - arm_w,
            shoulder_y + torso_h * 0.06,
            cx - torso_w / 2,
            shoulder_y + arm_h,
        )
        right_arm = self._rect(
            cx + torso_w / 2,
            shoulder_y + torso_h * 0.06,
            cx + torso_w / 2 + arm_w,
            shoulder_y + arm_h,
        )
        left_leg = self._rect(cx - leg_gap / 2 - leg_w, hip_y, cx - leg_gap / 2, foot_y)
        right_leg = self._rect(cx + leg_gap / 2, hip_y, cx + leg_gap / 2 + leg_w, foot_y)

        return BodyRegions(
            head=head,
            torso=torso,
            left_arm=left_arm,
            right_arm=right_arm,
            left_leg=left_leg,
            right_leg=right_leg,
        ).as_dict()

    def build_from_center(
        self,
        center_x: float,
        center_y: float,
        width: float = 12.0,
        height: float = 26.0,
    ) -> dict[str, Polygon]:
        half_w = width / 2
        half_h = height / 2
        bbox = [
            center_x - half_w,
            center_y - half_h,
            center_x + half_w,
            center_y + half_h,
        ]
        return self.build_from_bbox(bbox)

    @staticmethod
    def _rect(x1: float, y1: float, x2: float, y2: float) -> Polygon:
        return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
