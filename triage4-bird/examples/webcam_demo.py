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
    enumerate_cameras,
    format_camera_table,
    run_camera_preview,
)
from triage4_bird.sim.synthetic_station import demo_observations  # noqa: E402


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


def _interframe_motion(prev: np.ndarray, curr: np.ndarray) -> float:
    if prev.shape != curr.shape:
        return 0.0
    return float(np.mean(np.abs(prev.astype(np.float64) - curr.astype(np.float64))) / 255.0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=None,
                        help="OpenCV source: index (0,1,...), URL, or file path")
    parser.add_argument("--synthetic", action="store_true",
                        help="force synthetic source (skip camera entirely)")
    parser.add_argument("--frames", type=int, default=60,
                        help="frames to collect (default: 60)")
    parser.add_argument("--fps", type=float, default=30.0,
                        help="expected fps (default: 30)")
    parser.add_argument("--list-cameras", action="store_true",
                        help="probe local cameras and exit (no engine run)")
    parser.add_argument("--preview", action="store_true",
                        help="open live preview window before capture (SPACE: continue, Q: quit)")
    args = parser.parse_args(argv)

    if args.list_cameras:
        try:
            rows = enumerate_cameras(max_index=10)
        except FrameSourceUnavailable as exc:
            print(f"[error] {exc}")
            return 2
        print(format_camera_table(rows))
        return 0

    if args.preview and not args.synthetic:
        raw = args.source if args.source is not None else 0
        try:
            preview_source = int(raw)
        except (TypeError, ValueError):
            preview_source = raw
        try:
            decision = run_camera_preview(preview_source)
        except FrameSourceUnavailable as exc:
            print(f"[preview] unavailable ({exc}); continuing without preview")
            decision = "continue"
        if decision == "quit":
            print("[preview] user cancelled — exiting")
            return 0

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
