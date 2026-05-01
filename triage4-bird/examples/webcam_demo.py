"""triage4-bird — webcam demo (Phase 10 stationary-camera support).

Bird-feeder / station-camera input pilot. Captures frames, measures
**frame-difference motion** (a proxy for "bird is at the feeder"),
then runs ``AvianHealthEngine`` over the first synthetic observation
and reports both the engine output and the camera-observed motion.

This is **not** real bird detection or audio capture — a production
deployment would feed real call_samples (audio capture) and pose
samples (visual extractor) into ``BirdObservation``. The frame-source
layer is the same.

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

from triage4_bird.bird_health.monitoring_engine import AvianHealthEngine  # noqa: E402
from triage4_bird.perception import (  # noqa: E402
    FrameSourceUnavailable,
    SyntheticFrameSource,
    build_opencv_frame_source,
)
from triage4_bird.sim.synthetic_station import demo_observations  # noqa: E402


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


def _interframe_motion(prev: np.ndarray, curr: np.ndarray) -> float:
    if prev.shape != curr.shape:
        return 0.0
    return float(np.mean(np.abs(prev.astype(np.float64) - curr.astype(np.float64))) / 255.0)


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
    prev: np.ndarray | None = None
    n = 0
    with source:
        while n < args.frames:
            frame = source.read()
            if frame is None:
                break
            n += 1
            if prev is not None:
                motion.append(_interframe_motion(prev, frame))
            prev = frame

    if not motion:
        print("[error] not enough frames")
        return 1

    mean_motion = float(np.mean(motion))
    activity_threshold = 0.02
    active_frames = sum(1 for m in motion if m > activity_threshold)
    presence_rate = active_frames / max(1, len(motion))

    print(f"[run] frames consumed: {n}")
    print(f"[run] mean inter-frame motion: {mean_motion:.4f}")
    print(f"[run] frames above activity threshold: {active_frames}/{len(motion)} "
          f"({presence_rate * 100:.1f}%)")
    _hr()

    obs_list = demo_observations()
    obs = obs_list[0]
    report = AvianHealthEngine().review(obs)
    s = report.scores[0]
    print(f"station_id: {report.station_id}  obs_token: {s.obs_token}")
    print(f"alert_level: {s.alert_level}  overall: {s.overall:.2f}")
    print(f"  call:     {s.call_presence_safety:.2f}")
    print(f"  distress: {s.distress_safety:.2f}")
    print(f"  vitals:   {s.vitals_safety:.2f}")
    print(f"  thermal:  {s.thermal_safety:.2f}")
    print(f"  cluster:  {s.mortality_cluster_safety:.2f}")
    print(f"alerts: {len(report.alerts)}")
    _hr()
    print(f"camera-observed presence rate: {presence_rate * 100:.1f}%  "
          f"(motion-above-threshold proxy for 'bird at feeder')")
    print("(real deployment maps motion → call/wingbeat/thermal samples)")
    _hr()
    print("✓ webcam demo complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
