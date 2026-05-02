"""triage4-stroll — webcam demo (Phase 10 stationary-camera support).

Personal day-walk advisor. Captures a short window of frames,
extracts inter-frame motion (activity proxy) and mean luminance
(sun-exposure proxy), feeds them into ``StrollAssistant`` along
with operator-supplied pace, duration, terrain, HR, and ambient
temperature, then prints the advisory.

This is **not** real GPS tracking — production deployments would
feed real wearable / smartphone IMU + GPS data into
``StrollSegment``. The frame-source layer is the same.

Run from the project root:

    python examples/webcam_demo.py                     # auto-fallback
    python examples/webcam_demo.py --synthetic         # force synthetic
    python examples/webcam_demo.py --list-cameras      # discover devices

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

from triage4_stroll.perception import (  # noqa: E402
    FrameSourceUnavailable,
    SyntheticFrameSource,
    build_opencv_frame_source,
    enumerate_cameras,
    format_camera_table,
    run_camera_preview,
)
from triage4_stroll.sim.synthetic_stroll import generate_segment  # noqa: E402
from triage4_stroll.walk_assistant.stroll_assistant import StrollAssistant  # noqa: E402


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
                        help="OpenCV source: index (0,1,...), URL, or file path")
    parser.add_argument("--synthetic", action="store_true",
                        help="force synthetic source (skip camera entirely)")
    parser.add_argument("--frames", type=int, default=60,
                        help="frames to collect (default: 60)")
    parser.add_argument("--fps", type=float, default=30.0,
                        help="expected fps (default: 30)")
    parser.add_argument("--list-cameras", action="store_true",
                        help="probe local cameras and exit")
    parser.add_argument("--preview", action="store_true",
                        help="open live preview window before capture")
    parser.add_argument("--terrain", default="flat",
                        choices=["flat", "hilly", "stairs", "mixed"])
    parser.add_argument("--pace", type=float, default=4.5,
                        help="walking pace in km/h")
    parser.add_argument("--duration", type=float, default=15.0,
                        help="minutes since walk started")
    parser.add_argument("--rest", type=float, default=15.0,
                        help="minutes since last rest break")
    parser.add_argument("--temp", type=float, default=22.0,
                        help="ambient air temperature (C)")
    parser.add_argument("--hr", type=float, default=110.0,
                        help="heart-rate snapshot (bpm)")
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
    print(f"[config] source={source_kind}  terrain={args.terrain}  "
          f"pace={args.pace} km/h  duration={args.duration} min  "
          f"frames={args.frames}  fps={args.fps}")
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
    activity = float(min(1.0, mean_motion * 25.0))
    sun_exposure = float(min(1.0, mean_lum / 200.0))

    print(f"[run] frames consumed: {n}")
    print(f"[run] mean motion: {mean_motion:.4f} (activity proxy: {activity:.2f})")
    print(f"[run] mean luminance: {mean_lum:.1f} (sun proxy: {sun_exposure:.2f})")
    _hr()

    seg = generate_segment(
        walker_id="WEBCAM_WALKER",
        terrain=args.terrain,
        pace_kmh=args.pace,
        duration_min=args.duration,
        activity_intensity=activity,
        sun_exposure_proxy=sun_exposure,
        minutes_since_rest=args.rest,
        air_temp_c=args.temp,
        hr_bpm=args.hr,
    )
    advisory = StrollAssistant().review(seg)
    print(advisory.as_text())
    _hr()
    print(f"camera-observed activity: {activity:.2f}  sun: {sun_exposure:.2f}")
    print("(real deployment maps motion/luminance to StrollSegment fields)")
    _hr()
    print("✓ webcam demo complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
