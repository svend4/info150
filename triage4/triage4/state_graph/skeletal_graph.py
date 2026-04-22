"""K3-1.3 — Dynamic skeletal graph.

Closes the "dynamic skeletal graph" cell of the K3 matrix. Sits next
to ``perception/body_regions.py`` (K3-1.2, static polygon regions)
and extends it along the time axis: instead of a single snapshot, a
``SkeletalGraph`` records joint positions and per-joint wound
intensity across multiple frames.

Three triage-useful derivations fall out once the time dimension is
in place:

- **Limb asymmetry** — left-vs-right contrast in motion or wound
  intensity; strong asymmetry is a clinical flag.
- **Wound evolution** — per-joint intensity trend (rising / stable /
  falling) across observation windows.
- **Motion score** — how much a joint moved; zero motion on a joint
  that should be moving is itself a clinical flag.

Topology is a fixed 13-joint humanoid skeleton — deliberately
simple, deterministic, auditable. No pose-estimator dependency
(real pose data can feed this graph through the `record` API once
the detector path lands).

Design goals: stdlib only (no numpy in the module surface), pure-
Python math, dataclass-heavy, deterministic, bounded history.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


# Canonical 13-joint humanoid skeleton. Kept small; matches the
# `BodyRegions` decomposition so consumers can cross-map.
_JOINTS: tuple[str, ...] = (
    "head",
    "neck",
    "shoulder_l", "shoulder_r",
    "elbow_l",    "elbow_r",
    "wrist_l",    "wrist_r",
    "hip_l",      "hip_r",
    "knee_l",     "knee_r",
    "pelvis",
)

# Bones — undirected edges in the skeletal graph.
_BONES: tuple[tuple[str, str], ...] = (
    ("head", "neck"),
    ("neck", "shoulder_l"), ("neck", "shoulder_r"),
    ("shoulder_l", "elbow_l"), ("shoulder_r", "elbow_r"),
    ("elbow_l", "wrist_l"),    ("elbow_r", "wrist_r"),
    ("neck", "pelvis"),
    ("pelvis", "hip_l"), ("pelvis", "hip_r"),
    ("hip_l", "knee_l"), ("hip_r", "knee_r"),
)

# Left/right pairs used for limb-asymmetry analysis.
_MIRROR_PAIRS: tuple[tuple[str, str], ...] = (
    ("shoulder_l", "shoulder_r"),
    ("elbow_l", "elbow_r"),
    ("wrist_l", "wrist_r"),
    ("hip_l", "hip_r"),
    ("knee_l", "knee_r"),
)

_MAX_HISTORY_DEFAULT = 256


@dataclass(frozen=True)
class JointObservation:
    """A single time-stamped observation of one joint."""

    t: float
    x: float
    y: float
    wound_intensity: float = 0.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.wound_intensity <= 1.0:
            raise ValueError(
                f"wound_intensity must be in [0, 1], got {self.wound_intensity}"
            )
        if not all(math.isfinite(v) for v in (self.t, self.x, self.y)):
            raise ValueError("t / x / y must be finite")


@dataclass
class JointTrend:
    joint: str
    n_observations: int
    motion_score: float
    wound_slope: float
    wound_mean: float


@dataclass
class AsymmetryReport:
    pair: tuple[str, str]
    motion_asymmetry: float
    wound_asymmetry: float


@dataclass
class SkeletalSnapshot:
    """Most-recent positions / wounds per joint."""

    joints: dict[str, tuple[float, float]]
    wounds: dict[str, float]
    t: float


class UnknownJoint(KeyError):
    """Raised when an observation references a joint outside the canonical set."""


class SkeletalGraph:
    """Time-evolving 13-joint humanoid graph with wound intensity per joint.

    Bounded history — keeps the most recent ``max_history`` frames per
    joint. Missing joints are allowed; any method that reports on a
    joint with zero observations returns a conservative "no signal"
    value instead of raising.
    """

    JOINTS: tuple[str, ...] = _JOINTS
    BONES: tuple[tuple[str, str], ...] = _BONES
    MIRROR_PAIRS: tuple[tuple[str, str], ...] = _MIRROR_PAIRS

    def __init__(self, max_history: int = _MAX_HISTORY_DEFAULT) -> None:
        if max_history < 2:
            raise ValueError("max_history must be >= 2")
        self._max_history = int(max_history)
        self._history: dict[str, list[JointObservation]] = {
            joint: [] for joint in _JOINTS
        }

    # -- ingestion -------------------------------------------------------

    def record(
        self,
        t: float,
        joints: dict[str, tuple[float, float]],
        wounds: dict[str, float] | None = None,
    ) -> None:
        """Append a single frame across any subset of joints."""
        wounds = wounds or {}
        for joint, (x, y) in joints.items():
            if joint not in self._history:
                raise UnknownJoint(joint)
            obs = JointObservation(
                t=float(t), x=float(x), y=float(y),
                wound_intensity=float(wounds.get(joint, 0.0)),
            )
            lane = self._history[joint]
            lane.append(obs)
            if len(lane) > self._max_history:
                del lane[: len(lane) - self._max_history]

    # -- views ----------------------------------------------------------

    def latest(self) -> SkeletalSnapshot | None:
        """Most-recent positions / wounds across joints that have any data."""
        all_obs: list[JointObservation] = [
            obs for lane in self._history.values() for obs in lane
        ]
        if not all_obs:
            return None

        t_max = max(obs.t for obs in all_obs)
        joints: dict[str, tuple[float, float]] = {}
        wounds: dict[str, float] = {}
        for joint, lane in self._history.items():
            if not lane:
                continue
            last = lane[-1]
            joints[joint] = (round(last.x, 3), round(last.y, 3))
            wounds[joint] = round(last.wound_intensity, 3)
        return SkeletalSnapshot(joints=joints, wounds=wounds, t=round(t_max, 3))

    def joint_trend(self, joint: str) -> JointTrend:
        """Per-joint motion + wound summary."""
        if joint not in self._history:
            raise UnknownJoint(joint)
        lane = self._history[joint]
        n = len(lane)
        if n == 0:
            return JointTrend(
                joint=joint, n_observations=0,
                motion_score=0.0, wound_slope=0.0, wound_mean=0.0,
            )

        motion_score = self._motion_score(lane)
        wound_slope = self._linear_slope([obs.t for obs in lane],
                                         [obs.wound_intensity for obs in lane])
        wound_mean = sum(obs.wound_intensity for obs in lane) / n

        return JointTrend(
            joint=joint,
            n_observations=n,
            motion_score=round(motion_score, 4),
            wound_slope=round(wound_slope, 4),
            wound_mean=round(wound_mean, 4),
        )

    def asymmetry(
        self, pairs: tuple[tuple[str, str], ...] | None = None,
    ) -> list[AsymmetryReport]:
        """Left-vs-right contrast in motion and wound intensity."""
        pairs = pairs or _MIRROR_PAIRS
        reports: list[AsymmetryReport] = []
        for left, right in pairs:
            l_trend = self.joint_trend(left)
            r_trend = self.joint_trend(right)
            if l_trend.n_observations == 0 or r_trend.n_observations == 0:
                continue
            motion_a = self._abs_normalised(l_trend.motion_score, r_trend.motion_score)
            wound_a = self._abs_normalised(l_trend.wound_mean, r_trend.wound_mean)
            reports.append(
                AsymmetryReport(
                    pair=(left, right),
                    motion_asymmetry=round(motion_a, 4),
                    wound_asymmetry=round(wound_a, 4),
                )
            )
        return reports

    # -- serialization --------------------------------------------------

    def as_json(self) -> dict:
        latest = self.latest()
        return {
            "joints": list(_JOINTS),
            "bones": [list(b) for b in _BONES],
            "mirror_pairs": [list(p) for p in _MIRROR_PAIRS],
            "latest": None if latest is None else {
                "t": latest.t,
                "joints": latest.joints,
                "wounds": latest.wounds,
            },
            "n_observations": {j: len(lane) for j, lane in self._history.items()},
        }

    # -- internals ------------------------------------------------------

    @staticmethod
    def _motion_score(lane: list[JointObservation]) -> float:
        """Total path length per observed second, clipped to [0, 1].

        Path length is direct and robust; dividing by the observed
        time span normalises for irregular sampling.
        """
        if len(lane) < 2:
            return 0.0
        total = 0.0
        for prev, curr in zip(lane, lane[1:]):
            total += math.hypot(curr.x - prev.x, curr.y - prev.y)
        span = max(1e-9, lane[-1].t - lane[0].t)
        return max(0.0, min(1.0, total / span / 10.0))

    @staticmethod
    def _linear_slope(xs: list[float], ys: list[float]) -> float:
        """Least-squares slope with guard for degenerate inputs."""
        n = len(xs)
        if n < 2:
            return 0.0
        mean_x = sum(xs) / n
        mean_y = sum(ys) / n
        num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
        den = sum((x - mean_x) ** 2 for x in xs)
        if den <= 1e-12:
            return 0.0
        return num / den

    @staticmethod
    def _abs_normalised(a: float, b: float) -> float:
        """|a-b| / max(|a|+|b|, ε), clipped to [0, 1]."""
        denom = max(abs(a) + abs(b), 1e-6)
        return max(0.0, min(1.0, abs(a - b) / denom))
