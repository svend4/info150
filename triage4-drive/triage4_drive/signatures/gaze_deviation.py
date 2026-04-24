"""Gaze-deviation — fraction of time gaze is off-task.

The "task" for a driver is: road + side mirrors + rearview.
Everything else (dashboard-staring, phone, passenger, closed
eyes) accumulates distraction time. The signature returns the
fraction of the window spent off-task, with a small grace
allowance on the dashboard region — glances at the dashboard
are normal driving behaviour up to ~0.5 s per glance.

Returns 0.0 for an empty sample list — calibration layer
treats missing channels separately.
"""

from __future__ import annotations

from typing import Iterable

from ..core.enums import ON_TASK_REGIONS
from ..core.models import GazeSample


def compute_distraction_index(
    samples: Iterable[GazeSample],
    grace_dashboard_s: float = 0.5,
) -> float:
    """Return the distraction index in [0, 1].

    Distraction = (time off-task beyond grace) / (total time
    in window). Sample timestamps drive the calculation so
    uneven sample rates don't bias the result.
    """
    sample_list = sorted(samples, key=lambda s: s.t_s)
    if len(sample_list) < 2:
        return 0.0

    total_s = sample_list[-1].t_s - sample_list[0].t_s
    if total_s <= 0:
        return 0.0

    off_task_s = 0.0
    current_region = sample_list[0].region
    region_start = sample_list[0].t_s
    for sample in sample_list[1:]:
        if sample.region != current_region:
            # Close out the previous region.
            dur = sample.t_s - region_start
            off_task_s += _off_task_contribution(
                current_region, dur, grace_dashboard_s
            )
            current_region = sample.region
            region_start = sample.t_s
    # Close out the last region.
    dur = sample_list[-1].t_s - region_start
    off_task_s += _off_task_contribution(
        current_region, dur, grace_dashboard_s
    )

    return max(0.0, min(1.0, off_task_s / total_s))


def _off_task_contribution(
    region: str,
    duration_s: float,
    grace_dashboard_s: float,
) -> float:
    """How much of a single-region run counts as off-task."""
    if region in ON_TASK_REGIONS:
        return 0.0
    if region == "dashboard":
        # Grace allowance — dashboard glances up to the grace
        # duration are free; beyond that, the surplus is
        # off-task.
        return max(0.0, duration_s - grace_dashboard_s)
    # off_road: every second counts.
    return duration_s
