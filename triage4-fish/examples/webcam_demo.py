"""triage4-fish — webcam demo (Phase 10 stationary-camera support).

Pen-surface camera input pilot. Captures frames, computes a **water
turbidity proxy** (frame standard deviation — clearer water has more
visual contrast in the surface ripple pattern, murky water tends to
flatten) and an **inter-frame motion proxy** for school activity, then
runs ``AquacultureHealthEngine`` over the first synthetic pen
observation. Reports the engine output alongside the camera signals.

This is **not** real underwater pen monitoring — a production
deployment would feed real water-chemistry sensor data + sonar /
visual school-cohesion measurements into ``PenObservation``. The
frame-source layer is the same.

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

from triage4_fish.pen_health.monitoring_engine import AquacultureHealthEngine  # noqa: E402
from triage4_fish.perception import (  # noqa: E402
    FrameSourceUnavailable,
    SyntheticFrameSource,
    build_opencv_frame_source,
)
from triage4_fish.sim.synthetic_pen import demo_observations  # noqa: E402


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

    contrasts: list[float] = []
    motion: list[float] = []
    prev: np.ndarray | None = None
    n = 0
    with source:
        while n < args.frames:
            frame = source.read()
            if frame is None:
                break
            n += 1
            contrasts.append(float(np.std(frame.astype(np.float64))))
            if prev is not None:
                diff = np.abs(prev.astype(np.float64) - frame.astype(np.float64))
                motion.append(float(np.mean(diff) / 255.0))
            prev = frame
    if not contrasts:
        print("[error] no frames")
        return 1

    mean_contrast = float(np.mean(contrasts))
    mean_motion = float(np.mean(motion)) if motion else 0.0
    # Higher contrast → clearer water (less turbid). Map to safety.
    turbidity_safety = float(min(1.0, mean_contrast / 60.0))

    print(f"[run] frames consumed: {n}")
    print(f"[run] mean frame contrast: {mean_contrast:.2f} "
          f"(turbidity safety proxy: {turbidity_safety:.2f})")
    print(f"[run] mean inter-frame motion: {mean_motion:.4f} "
          f"(school activity proxy)")
    _hr()

    obs_list = demo_observations()
    obs = obs_list[0]
    report = AquacultureHealthEngine().review(obs, farm_id="WEBCAM_FARM")
    s = report.scores[0]
    print(f"farm_id: {report.farm_id}  pen_id: {s.pen_id}")
    print(f"welfare_level: {s.welfare_level}  overall: {s.overall:.2f}")
    print(f"  gill_rate:        {s.gill_rate_safety:.2f}")
    print(f"  school_cohesion:  {s.school_cohesion_safety:.2f}")
    print(f"  sea_lice:         {s.sea_lice_safety:.2f}")
    print(f"  mortality_floor:  {s.mortality_safety:.2f}")
    print(f"  water_chemistry:  {s.water_chemistry_safety:.2f}")
    print(f"alerts: {len(report.alerts)}")
    _hr()
    print(f"camera-observed turbidity proxy: {turbidity_safety:.2f}  "
          f"motion proxy: {mean_motion:.4f}")
    print("(real deployment maps these to PenObservation water_chemistry + school samples)")
    _hr()
    print("✓ webcam demo complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
