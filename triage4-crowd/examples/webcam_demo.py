"""triage4-crowd — webcam demo (Phase 10 stationary-camera support).

Venue / event-overhead camera input pilot. Captures frames, computes
**inter-frame motion** as a crowd-flow proxy and **frame variance**
as a density proxy, then runs ``VenueMonitorEngine`` over the
synthetic demo venue. Reports the engine output alongside the camera
signals.

This is **not** real crowd density estimation — production deploys
use stereo-cam or LiDAR for density, person-detection + tracking for
flow vectors. The frame-source layer is the same.

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

from triage4_crowd.perception import (  # noqa: E402
    FrameSourceUnavailable,
    SyntheticFrameSource,
    build_opencv_frame_source,
)
from triage4_crowd.sim.synthetic_venue import demo_venue  # noqa: E402
from triage4_crowd.venue_monitor.monitoring_engine import VenueMonitorEngine  # noqa: E402


def _hr() -> None:
    print("-" * 70)


def _build_source(args: argparse.Namespace):
    if args.synthetic:
        print("[source] forced synthetic")
        return SyntheticFrameSource(
            pattern="moving_square", n_frames=args.frames, fs_hz=args.fps, width=64, height=48, seed=0,
        ), "synthetic"

    raw = args.source if args.source is not None else 0
    # cv2.VideoCapture treats "0" (str) and 0 (int) differently
    # on Windows. Convert numeric strings → int up-front.
    try:
        source = int(raw)
    except (TypeError, ValueError):
        source = raw

    try:
        return build_opencv_frame_source(source), "webcam"
    except FrameSourceUnavailable as exc:
        print(f"[source] webcam unavailable ({exc}); using synthetic")

    return SyntheticFrameSource(
        pattern="moving_square", n_frames=args.frames, fs_hz=args.fps, width=64, height=48, seed=0,
    ), "synthetic-fallback"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=None)
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--frames", type=int, default=60)
    parser.add_argument("--fps", type=float, default=30.0)
    args = parser.parse_args(argv)

    source, source_kind = _build_source(args)
    print(f"[config] source={source_kind}  frames={args.frames}  fps={args.fps}")
    _hr()

    motion: list[float] = []
    densities: list[float] = []
    prev: np.ndarray | None = None
    n = 0
    with source:
        while n < args.frames:
            frame = source.read()
            if frame is None:
                break
            n += 1
            densities.append(float(np.std(frame.astype(np.float64))))
            if prev is not None:
                diff = np.abs(prev.astype(np.float64) - frame.astype(np.float64))
                motion.append(float(np.mean(diff) / 255.0))
            prev = frame

    if not densities:
        print("[error] no frames")
        return 1

    mean_motion = float(np.mean(motion)) if motion else 0.0
    mean_density = float(np.mean(densities))
    flow_proxy = float(min(1.0, mean_motion * 25.0))
    density_proxy = float(min(1.0, mean_density / 80.0))

    print(f"[run] frames consumed: {n}")
    print(f"[run] mean inter-frame motion: {mean_motion:.4f} "
          f"(flow proxy: {flow_proxy:.2f})")
    print(f"[run] mean frame variance: {mean_density:.2f} "
          f"(density proxy: {density_proxy:.2f})")
    _hr()

    zones = demo_venue()
    report = VenueMonitorEngine().review(venue_id="WEBCAM_VENUE", zones=zones)
    print(f"venue_id: {report.venue_id}  zones: {len(report.scores)}  "
          f"alerts: {len(report.alerts)}")
    for s in report.scores:
        print(f"  {s.zone_id}  level={s.alert_level:7s}  overall={s.overall:.2f}")
    _hr()
    print(f"camera-observed flow: {flow_proxy:.2f}  density: {density_proxy:.2f}")
    print("(real deployment maps to ZoneObservation density/flow/pressure samples)")
    _hr()
    print("✓ webcam demo complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
