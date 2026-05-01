"""triage4-farm — webcam demo (Phase 10 stationary-camera support).

Paddock-camera input pilot. Captures frames, measures **inter-frame
motion** as an animal-activity proxy, then runs ``WelfareCheckEngine``
over the synthetic demo herd. Reports both alongside.

This is **not** real lameness / gait detection — production deploys
use multi-camera mocap or pressure-mat / accelerometer sensors. The
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

from triage4_farm.perception import (  # noqa: E402
    FrameSourceUnavailable,
    SyntheticFrameSource,
    build_opencv_frame_source,
)
from triage4_farm.sim.synthetic_herd import demo_herd  # noqa: E402
from triage4_farm.welfare_check.welfare_engine import WelfareCheckEngine  # noqa: E402


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
    parser.add_argument("--n-animals", type=int, default=6)
    parser.add_argument("--n-lame", type=int, default=2)
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
        print("[error] not enough frames")
        return 1

    mean_motion = float(np.mean(motion))
    activity_proxy = float(min(1.0, mean_motion * 25.0))

    print(f"[run] frames consumed: {n}")
    print(f"[run] mean motion: {mean_motion:.4f} (herd activity proxy: {activity_proxy:.2f})")
    _hr()

    herd = demo_herd(n_animals=args.n_animals, n_lame=args.n_lame)
    report = WelfareCheckEngine().review(farm_id="WEBCAM_FARM", observations=herd)
    print(f"farm_id: {report.farm_id}  animals: {len(report.scores)}  "
          f"herd_overall: {report.herd_overall:.2f}  alerts: {len(report.alerts)}")
    for s in report.scores:
        print(f"  {s.animal_id}  flag={s.flag:8s}  overall={s.overall:.2f}")
    _hr()
    print(f"camera-observed herd activity: {activity_proxy:.2f}")
    print("(real deployment maps motion → AnimalObservation pose-frame samples)")
    _hr()
    print("✓ webcam demo complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
