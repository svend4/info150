"""triage4-desk — webcam demo.

Personal desk-worker advisor. Captures a short window of frames,
extracts inter-frame motion (typing-rhythm proxy) and mean
luminance (ambient-light proxy), feeds them into ``DeskAssistant``
along with operator-supplied session timings, posture, and
optional HR / temperature, then prints the advisory.

This is **not** a full posture estimator — production deployments
would feed real pose-detector / blink-detector / keylog data into
``DeskSession``. The frame-source layer is the same.

Run from the project root:

    python examples/webcam_demo.py                        # auto-fallback
    python examples/webcam_demo.py --synthetic            # force synthetic
    python examples/webcam_demo.py --list-cameras         # discover devices
    python examples/webcam_demo.py --work-mode gaming     # pick a profile

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

from triage4_desk.desk_assistant.desk_assistant import DeskAssistant  # noqa: E402
from triage4_desk.perception import (  # noqa: E402
    FrameSourceUnavailable,
    SyntheticFrameSource,
    build_opencv_frame_source,
    enumerate_cameras,
    format_camera_table,
    run_camera_preview,
)
from triage4_desk.sim.synthetic_desk import generate_session  # noqa: E402


def _hr() -> None:
    print("-" * 70)


def _build_source(args: argparse.Namespace):
    if args.synthetic:
        print("[source] forced synthetic")
        return SyntheticFrameSource(
            pattern="moving_square", n_frames=args.frames, fs_hz=args.fps,
            width=64, height=48, seed=0,
        ), "synthetic"

    raw = args.source if args.source is not None else 0
    try:
        source = int(raw)
    except (TypeError, ValueError):
        source = raw

    try:
        return build_opencv_frame_source(source), "webcam"
    except FrameSourceUnavailable as exc:
        print(f"[source] webcam unavailable ({exc}); using synthetic")

    return SyntheticFrameSource(
        pattern="moving_square", n_frames=args.frames, fs_hz=args.fps,
        width=64, height=48, seed=0,
    ), "synthetic-fallback"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=None,
                        help="OpenCV source: index, URL, or file path")
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--frames", type=int, default=60)
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument("--list-cameras", action="store_true")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--work-mode", default="office",
                        choices=["office", "coding", "meeting", "gaming", "streaming"])
    parser.add_argument("--session", type=float, default=35.0,
                        help="continuous minutes at desk")
    parser.add_argument("--break", type=float, default=15.0, dest="break_min",
                        help="minutes since last microbreak")
    parser.add_argument("--stretch", type=float, default=60.0,
                        help="minutes since last stretch / standing break")
    parser.add_argument("--posture", type=float, default=0.85,
                        help="self-rated posture quality [0..1]")
    parser.add_argument("--drowsy", type=float, default=0.0,
                        help="self-rated drowsiness [0..1]")
    parser.add_argument("--distract", type=float, default=0.0,
                        help="self-rated distraction [0..1]")
    parser.add_argument("--temp", type=float, default=22.0,
                        help="workspace temperature (C)")
    parser.add_argument("--hr", type=float, default=78.0,
                        help="heart rate (bpm)")
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
            print("[preview] user cancelled - exiting")
            return 0

    source, source_kind = _build_source(args)
    print(f"[config] source={source_kind}  work_mode={args.work_mode}  "
          f"session={args.session} min  break={args.break_min} min  "
          f"frames={args.frames}")
    _hr()

    motion: list[float] = []
    luminances: list[float] = []
    prev: np.ndarray | None = None
    n = 0
    with source:
        while n < args.frames:
            frame = source.read()
            if frame is None:
                break
            n += 1
            luminances.append(float(np.mean(
                frame[..., 0] * 0.299 + frame[..., 1] * 0.587
                + frame[..., 2] * 0.114
            )))
            if prev is not None:
                diff = np.abs(prev.astype(np.float64) - frame.astype(np.float64))
                motion.append(float(np.mean(diff) / 255.0))
            prev = frame

    if not luminances:
        print("[error] no frames")
        return 1

    mean_motion = float(np.mean(motion)) if motion else 0.0
    mean_lum = float(np.mean(luminances))
    typing_intensity = float(min(1.0, mean_motion * 25.0))
    ambient_light = float(min(1.0, mean_lum / 200.0))

    print(f"[run] frames consumed: {n}")
    print(f"[run] mean motion: {mean_motion:.4f} -> typing_intensity: {typing_intensity:.2f}")
    print(f"[run] mean luminance: {mean_lum:.1f} -> ambient_light: {ambient_light:.2f}")
    _hr()

    s = generate_session(
        worker_id="WEBCAM_WORKER",
        work_mode=args.work_mode,
        session_min=args.session,
        minutes_since_break=args.break_min,
        minutes_since_stretch=args.stretch,
        typing_intensity=typing_intensity,
        screen_motion_proxy=typing_intensity,
        ambient_light_proxy=ambient_light,
        posture_quality=args.posture,
        drowsiness_signal=args.drowsy,
        distraction_signal=args.distract,
        air_temp_c=args.temp,
        hr_bpm=args.hr,
    )
    advisory = DeskAssistant().review(s)
    print(advisory.as_text())
    _hr()
    print("(real deployment maps motion/luminance to DeskSession fields)")
    _hr()
    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
