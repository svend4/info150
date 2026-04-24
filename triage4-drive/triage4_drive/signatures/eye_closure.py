"""PERCLOS — Percentage of Eyelid Closure over a time window.

PERCLOS is the NHTSA / Wierwille 1994 drowsiness-detection
standard: the fraction of time the eyelids are closed at least
80 % over a rolling window (typically 1-3 min). Several PERCLOS
variants exist (P70, P80, EM, EyeCloseSpeed); this module
implements the most widely cited P80.

Also exposes a simple microsleep-event count — uninterrupted
runs of closed-eye samples exceeding ``microsleep_min_s``. A
microsleep is a much stronger drowsiness signal than PERCLOS
alone and lets the engine escalate to ``critical`` without
waiting for a minute of averaged data.

Pure function over the eye-state time series. Deterministic.
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import EyeStateSample


# P80 threshold — an eye sample counts as "closed" when the
# closure value is ≥ this. 0.8 is the NHTSA-standard cut-off.
P80_THRESHOLD = 0.8

# Minimum run-length to count as a microsleep. Tuned to 0.5 s
# per Wierwille — eye closures shorter than half a second are
# normal blinks and not drowsiness signals.
DEFAULT_MICROSLEEP_MIN_S = 0.5


def compute_perclos(
    samples: Iterable[EyeStateSample],
    threshold: float = P80_THRESHOLD,
) -> float:
    """Return PERCLOS as a fraction in [0, 1].

    Returns 0.0 when no samples are supplied — calibration-
    layer responsibility to flag the missing channel, not
    this function's job.
    """
    sample_list = list(samples)
    if not sample_list:
        return 0.0
    closed = sum(1 for s in sample_list if s.closure >= threshold)
    return closed / len(sample_list)


def count_microsleeps(
    samples: Iterable[EyeStateSample],
    microsleep_min_s: float = DEFAULT_MICROSLEEP_MIN_S,
    threshold: float = P80_THRESHOLD,
) -> int:
    """Return the number of microsleep events in the window.

    A microsleep event is an uninterrupted run of closed-eye
    samples spanning at least ``microsleep_min_s`` in wall
    time. Uses the sample timestamps (``t_s``) rather than
    sample counts so variable frame rates don't distort the
    result.
    """
    sample_list = sorted(samples, key=lambda s: s.t_s)
    if len(sample_list) < 2:
        return 0

    events = 0
    run_start: float | None = None
    for sample in sample_list:
        if sample.closure >= threshold:
            if run_start is None:
                run_start = sample.t_s
        else:
            if run_start is not None:
                if sample.t_s - run_start >= microsleep_min_s:
                    events += 1
                run_start = None
    # Unterminated closed run at the end of the window.
    if run_start is not None:
        if sample_list[-1].t_s - run_start >= microsleep_min_s:
            events += 1
    return events
