"""Left-right symmetry from paired joint samples over a rep.

Conceptually mirrors K3-1.3 ``SkeletalGraph.asymmetry()`` in
triage4. Implementation is a copy-fork, not an import —
wellness / clinical boundary.

The score is 1.0 when a bilateral exercise moves symmetrically
and drops toward 0.0 as one side diverges from the other. For
each frame we measure the |y-difference| between paired joints,
aggregated across the rep.
"""

from __future__ import annotations

import math
from typing import Iterable

from ..core.models import JointPoseSample, RepObservation


# Mirror pairs used for standard bilateral exercises. If the pose
# estimator upstream uses different joint names, pass a custom
# ``pairs`` argument to ``compute_rep_symmetry``.
DEFAULT_PAIRS: tuple[tuple[str, str], ...] = (
    ("shoulder_l", "shoulder_r"),
    ("elbow_l", "elbow_r"),
    ("wrist_l", "wrist_r"),
    ("hip_l", "hip_r"),
    ("knee_l", "knee_r"),
    ("ankle_l", "ankle_r"),
)


def _index_by_joint(frame: Iterable[JointPoseSample]) -> dict[str, JointPoseSample]:
    return {s.joint: s for s in frame}


def compute_rep_symmetry(
    rep: RepObservation,
    pairs: tuple[tuple[str, str], ...] = DEFAULT_PAIRS,
) -> float:
    """Return a symmetry score in [0, 1] — 1.0 = textbook bilateral.

    Method: for each frame, for each mirror pair, compute the
    absolute y-difference (vertical asymmetry is the dominant
    form-break signal). Normalise by the body-scale proxy
    (max shoulder-to-hip vertical span in the rep) to stay
    invariant to camera distance. Aggregate across frames with
    the mean absolute asymmetry, then map to [0, 1] via an
    exponential decay so small residual asymmetry still scores
    high.
    """
    if not rep.samples:
        return 1.0

    # Body scale = max |shoulder_y − hip_y| across frames. Falls
    # back to 1.0 (normalised coordinates) if shoulders / hips
    # aren't present.
    body_scales: list[float] = []
    for frame in rep.samples:
        idx = _index_by_joint(frame)
        ys: list[float] = []
        for side in ("shoulder_l", "shoulder_r", "hip_l", "hip_r"):
            if side in idx:
                ys.append(idx[side].y)
        if len(ys) >= 2:
            body_scales.append(max(ys) - min(ys))
    scale = max(body_scales) if body_scales else 1.0
    scale = max(scale, 1e-3)  # guard against degenerate observations

    diffs: list[float] = []
    for frame in rep.samples:
        idx = _index_by_joint(frame)
        for left, right in pairs:
            if left in idx and right in idx:
                diff = abs(idx[left].y - idx[right].y) / scale
                diffs.append(diff)

    if not diffs:
        return 1.0

    mean_asym = sum(diffs) / len(diffs)
    # Map [0, +∞) → [1.0, 0.0] via exp(-k * mean_asym). Tuned so
    # that 10 % of body scale asymmetry gives ~0.7, 20 % ~0.5,
    # 50 % ~0.15. These thresholds are stubs; proper calibration
    # waits on real data.
    score = math.exp(-3.5 * mean_asym)
    return max(0.0, min(1.0, score))
