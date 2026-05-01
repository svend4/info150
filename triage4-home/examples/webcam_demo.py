"""triage4-home — webcam demo (Phase 10 stationary-camera support).

Wall-mounted home-camera input pilot. Captures frames, measures
**inter-frame motion** as a resident-activity proxy, then runs
``HomeMonitoringEngine`` over the synthetic demo day-series. Reports
the engine output alongside the camera signal.

**PRIVACY NOTE:** in-home cameras are PII-adjacent. This demo is for
**developer testing only** — production deployments must follow
local privacy law (GDPR / HIPAA / state law) and obtain explicit
resident consent. The library is observation-only and ships with
strict claims-guard text.

This is **not** real fall detection / activity recognition —
production deploys need a proper RGB-skeleton extractor or thermal
+ depth sensors. The frame-source layer is the same.

Run from the project root:

    python examples/webcam_demo.py                 # auto-fallback
    python examples/webcam_demo.py --synthetic     # force synthetic

Optional dep: ``pip install opencv-python``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from triage4_home.core.models import HomeReport  # noqa: E402
from triage4_home.home_monitor.monitoring_engine import HomeMonitoringEngine  # noqa: E402
from triage4_home.perception import (  # noqa: E402
    FrameSourceUnavailable,
    SyntheticFrameSource,
    build_opencv_frame_source,
)
from triage4_home.sim.synthetic_day import demo_baseline, demo_day_series  # noqa: E402


def _hr() -> None:
    print("-" * 70)


def _build_source(args: argparse.Namespace):
    if args.synthetic:
        return SyntheticFrameSource(pattern="moving_square", n_frames=args.frames,
                                    fs_hz=args.fps, width=64, height=48), "synthetic"
    if args.source is not None:
        try:
            return build_opencv_frame_source(args.source), "webcam"
        except FrameSourceUnavailable as exc:
            print(f"[source] webcam unavailable ({exc}); using synthetic")
    try:
        return build_opencv_frame_source(0), "webcam"
    except FrameSourceUnavailable as exc:
        print(f"[source] auto-detect failed ({exc}); using synthetic")
    return SyntheticFrameSource(pattern="moving_square", n_frames=args.frames,
                                fs_hz=args.fps, width=64, height=48), "synthetic"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=None)
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--frames", type=int, default=60)
    parser.add_argument("--fps", type=float, default=30.0)
    args = parser.parse_args(argv)

    print("PRIVACY NOTE: in-home cameras are PII-adjacent. Developer-test only.")
    _hr()

    source, source_kind = _build_source(args)
    print(f"[config] source={source_kind}  frames={args.frames}  fps={args.fps}")
    _hr()

    motion: list[float] = []
    prev: np.ndarray | None = None
    n = 0
    with source:
        while n < args.frames:
            frame = source.read()
            if frame is None:
                break
            n += 1
            if prev is not None:
                diff = np.abs(prev.astype(np.float64) - frame.astype(np.float64))
                motion.append(float(np.mean(diff) / 255.0))
            prev = frame

    if not motion:
        print("[error] not enough frames")
        return 1

    mean_motion = float(np.mean(motion))
    activity_proxy = float(min(1.0, mean_motion * 25.0))

    print(f"[run] frames consumed: {n}")
    print(f"[run] mean motion: {mean_motion:.4f} "
          f"(resident activity proxy: {activity_proxy:.2f})")
    _hr()

    windows = demo_day_series()
    baseline = demo_baseline()
    engine = HomeMonitoringEngine()
    aggregate = HomeReport(residence_id="WEBCAM_RESIDENCE")
    for w in windows:
        score, alerts = engine.review(w, baseline=baseline)
        aggregate.scores.append(score)
        aggregate.alerts.extend(alerts)

    print(f"residence_id: {aggregate.residence_id}  windows: {aggregate.window_count}  "
          f"alerts: {len(aggregate.alerts)}")
    for s in aggregate.scores:
        print(f"  {s.window_id}  level={s.alert_level:9s}  overall={s.overall:.2f}")
    _hr()
    print(f"camera-observed activity: {activity_proxy:.2f}")
    print("(real deployment maps motion → ResidentObservation activity_minutes samples)")
    _hr()
    print("✓ webcam demo complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
