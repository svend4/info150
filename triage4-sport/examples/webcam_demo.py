"""triage4-sport — webcam demo (Phase 10 stationary-camera support).

Pilot adoption of the flagship's `frame_source` pattern for sibling-
level camera input. Captures frames from a real coaching/training
webcam (or a synthetic fallback), measures **frame-to-frame motion
intensity** as a proxy for workload, and feeds the result through
``SportPerformanceEngine`` using a synthetic baseline for the
remaining channels.

This is **not a real motion-capture pipeline** — it's a demo that
the sibling can take training-camera input and run a domain-specific
scalar through its engine. A real deployment would replace the
inter-frame-difference heuristic with a proper MoCap rig (MediaPipe,
OpenPose) and feed real movement_samples / workload_samples.

Run from the project root:

    python examples/webcam_demo.py                 # auto-fallback
    python examples/webcam_demo.py --source 0      # force webcam 0
    python examples/webcam_demo.py --synthetic     # force synthetic
    python examples/webcam_demo.py --frames 90     # number of frames

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

from triage4_sport.perception import (  # noqa: E402
    FrameSourceUnavailable,
    SyntheticFrameSource,
    build_opencv_frame_source,
    enumerate_cameras,
    format_camera_table,
    run_camera_preview,
)
from triage4_sport.sim.synthetic_session import demo_baseline, demo_sessions  # noqa: E402
from triage4_sport.sport_engine.monitoring_engine import SportPerformanceEngine  # noqa: E402


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
    """Mean absolute luminance difference between two frames, in [0, 1]."""
    if prev.shape != curr.shape:
        return 0.0
    a = prev.astype(np.float64)
    b = curr.astype(np.float64)
    diff = np.abs(a - b)
    return float(np.mean(diff) / 255.0)


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
    parser.add_argument("--baseline", type=int, default=0,
                        help="index into demo_sessions() to use as base session (0–4)")
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
    print(f"[config] source={source_kind}  baseline_idx={args.baseline}  "
          f"frames={args.frames}  fps={args.fps}")
    _hr()

    motion_series: list[float] = []
    prev_frame: np.ndarray | None = None
    frames_consumed = 0
    with source:
        while frames_consumed < args.frames:
            frame = source.read()
            if frame is None:
                break
            frames_consumed += 1
            if prev_frame is not None:
                motion_series.append(_interframe_motion(prev_frame, frame))
            prev_frame = frame

    if not motion_series:
        print("[error] not enough frames for motion measurement")
        return 1

    mean_motion = float(np.mean(motion_series))
    peak_motion = float(np.max(motion_series))

    print(f"[run] frames consumed: {frames_consumed}")
    print(f"[run] mean inter-frame motion: {mean_motion:.4f}")
    print(f"[run] peak inter-frame motion: {peak_motion:.4f}")
    _hr()

    # Pick a synthetic session as the base, then run it through the
    # engine with the captured baseline. Real deployments would
    # rebuild AthleteObservation from MoCap streams; here the demo
    # shows the integration shape and reports the camera-derived
    # motion metric alongside engine output for context.
    sessions = demo_sessions()
    idx = max(0, min(len(sessions) - 1, args.baseline))
    observation = sessions[idx]
    baseline = demo_baseline()
    report = SportPerformanceEngine().review(observation, baseline=baseline)

    a = report.assessment
    print(f"athlete: {a.athlete_token}")
    print(f"sport:   {observation.sport}")
    print(f"risk_band: {a.risk_band}")
    print(f"overall:  {a.overall:.2f}")
    print(f"  form_asymmetry_safety  : {a.form_asymmetry_safety:.2f}")
    print(f"  workload_load_safety   : {a.workload_load_safety:.2f}")
    print(f"  recovery_hr_safety     : {a.recovery_hr_safety:.2f}")
    print(f"  baseline_deviation     : {a.baseline_deviation_safety:.2f}")
    print(f"coach messages: {len(report.coach_messages)}")
    print(f"trainer notes: {len(report.trainer_notes)}")
    print(f"physician alert: {'yes' if report.physician_alert else 'no'}")
    _hr()
    print(f"camera-observed mean motion: {mean_motion:.4f}  "
          f"peak motion: {peak_motion:.4f}")
    print("(real deployment maps motion → workload_samples in AthleteObservation)")
    _hr()
    print("✓ webcam demo complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
