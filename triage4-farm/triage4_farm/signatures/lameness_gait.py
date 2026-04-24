"""Stand-off lameness score from paired hind-leg joint samples.

Conceptually mirrors triage4-fit's ``compute_rep_symmetry`` but
with a livestock twist: for quadrupeds the dominant lameness
signal is asymmetric vertical motion of the paired hind joints
(hock / fetlock) across the stride, not shoulder-to-hip posture.

Copy-fork, not an import. The fit and farm domains will diverge
further as each gets tuned against real data.

This is an OBSERVATION score, not a diagnosis. See
docs/PHILOSOPHY.md.
"""

from __future__ import annotations

import math
from typing import Iterable

from ..core.models import AnimalObservation, JointPoseSample


# Bilateral hind-leg pairs used by the default lameness signal.
# If the pose estimator upstream names joints differently (or the
# species uses a different anatomy — e.g. keel for chickens),
# pass custom pairs to ``compute_lameness_score``.
DEFAULT_PAIRS: tuple[tuple[str, str], ...] = (
    ("hock_l", "hock_r"),
    ("fetlock_l", "fetlock_r"),
    ("hoof_l", "hoof_r"),
)


def _index_by_joint(frame: Iterable[JointPoseSample]) -> dict[str, JointPoseSample]:
    return {s.joint: s for s in frame}


def compute_lameness_score(
    obs: AnimalObservation,
    pairs: tuple[tuple[str, str], ...] = DEFAULT_PAIRS,
) -> float:
    """Return a gait symmetry score in [0, 1]. 1.0 = textbook sound gait.

    Method: for each frame, for each bilateral pair, compute the
    absolute y-difference (vertical asymmetry is the dominant
    lameness signal — a lame leg rises less). Normalise by a
    body-scale proxy (max back-to-hoof vertical span across the
    observation) so the score is invariant to camera distance.
    Aggregate across frames with the mean, then map to [0, 1]
    via an exponential decay — 5 % of body-scale asymmetry
    scores ~0.78, 10 % ~0.61, 15 % ~0.47.
    """
    if not obs.pose_frames:
        return 1.0

    # Body scale = max vertical span of any joint we can see
    # across the pass. Fall back to 1.0 (normalised coordinates)
    # if we genuinely have no span — protects against degenerate
    # single-joint observations.
    spans: list[float] = []
    for frame in obs.pose_frames:
        ys = [s.y for s in frame]
        if len(ys) >= 2:
            spans.append(max(ys) - min(ys))
    scale = max(spans) if spans else 1.0
    scale = max(scale, 1e-3)

    diffs: list[float] = []
    for frame in obs.pose_frames:
        idx = _index_by_joint(frame)
        for left, right in pairs:
            if left in idx and right in idx:
                diff = abs(idx[left].y - idx[right].y) / scale
                diffs.append(diff)

    if not diffs:
        return 1.0

    mean_asym = sum(diffs) / len(diffs)
    # Same shape as fit's symmetry score. k=5.0 tuned so 10 %
    # asymmetry sits at the "concern" threshold.
    score = math.exp(-5.0 * mean_asym)
    return max(0.0, min(1.0, score))
