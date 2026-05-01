"""triage4-wild — webcam demo (Phase 10 stationary-camera support).

Trail-camera input pilot. Captures frames, measures **inter-frame
motion** (proxy for "animal moved through frame"), then runs
``WildlifeHealthEngine`` over the first synthetic reserve
observation. Reports the engine output alongside the camera signal.

This is **not** real wildlife detection — a production deployment
would feed real pose / thermal / body-condition extracted samples
into ``WildlifeObservation``. The frame-source layer is the same.

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

from triage4_wild.perception import (  # noqa: E402
    FrameSourceUnavailable,
    SyntheticFrameSource,
    build_opencv_frame_source,
)
from triage4_wild.sim.synthetic_reserve import demo_observations  # noqa: E402
from triage4_wild.wildlife_health.monitoring_engine import WildlifeHealthEngine  # noqa: E402


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
        print("[error] no frames")
        return 1

    mean_motion = float(np.mean(motion))
    threshold = 0.02
    motion_events = sum(1 for m in motion if m > threshold)
    presence_rate = motion_events / max(1, len(motion))

    print(f"[run] frames consumed: {n}")
    print(f"[run] mean inter-frame motion: {mean_motion:.4f}")
    print(f"[run] motion events above threshold: {motion_events}/{len(motion)} "
          f"({presence_rate * 100:.1f}%)")
    _hr()

    obs_list = demo_observations()
    obs = obs_list[0]
    report = WildlifeHealthEngine().review(obs, reserve_id="WEBCAM_RESERVE")
    s = report.scores[0]
    print(f"reserve_id: {report.reserve_id}  obs_token: {s.obs_token}")
    print(f"alert_level: {s.alert_level}  overall: {s.overall:.2f}")
    print(f"  gait:           {s.gait_safety:.2f}")
    print(f"  thermal:        {s.thermal_safety:.2f}")
    print(f"  postural:       {s.postural_safety:.2f}")
    print(f"  body_condition: {s.body_condition_safety:.2f}")
    print(f"  threat_signal:  {s.threat_signal:.2f}")
    print(f"alerts: {len(report.alerts)}")
    _hr()
    print(f"camera-observed motion-event rate: {presence_rate * 100:.1f}%")
    print("(real deployment maps this to WildlifeObservation pose/gait samples)")
    _hr()
    print("✓ webcam demo complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
