"""triage4-coast - webcam demo (Phase 10 stationary-camera support).

Coast-strip surveillance pilot. Captures frames, computes
inter-frame motion (density proxy) + frame variance
(complementary density signal) + mean luminance (sun-intensity
proxy), feeds them through ``CoastSafetyEngine`` over one zone
of operator-chosen kind, and prints the report.

This is **not** real lifeguard support - production deploys
need person-detection + thermal cameras + in-water object
tracking. The frame-source layer is the same.

Run from the project root:

    python examples/webcam_demo.py                     # auto-fallback
    python examples/webcam_demo.py --synthetic         # force synthetic
    python examples/webcam_demo.py --list-cameras
    python examples/webcam_demo.py --zone-kind water --in-water 0.2

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

from triage4_coast.coast_safety import CoastSafetyEngine  # noqa: E402
from triage4_coast.perception import (  # noqa: E402
    FrameSourceUnavailable,
    SyntheticFrameSource,
    build_opencv_frame_source,
    enumerate_cameras,
    format_camera_table,
    run_camera_preview,
)
from triage4_coast.sim import generate_zone_observation  # noqa: E402


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
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--frames", type=int, default=60)
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument("--list-cameras", action="store_true")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--zone-id", default="WEBCAM_ZONE")
    parser.add_argument("--zone-kind", default="beach",
                        choices=["beach", "promenade", "water", "pier"])
    parser.add_argument("--in-water", type=float, default=0.0,
                        help="operator-set in-water motion proxy [0..1]")
    parser.add_argument("--lost-child", action="store_true",
                        help="set the lost-child operator flag")
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
    print(f"[config] source={source_kind}  zone={args.zone_id} ({args.zone_kind})  "
          f"in_water={args.in_water:.2f}  frames={args.frames}  fps={args.fps}")
    _hr()

    motion: list[float] = []
    luminances: list[float] = []
    variances: list[float] = []
    prev: np.ndarray | None = None
    n = 0
    with source:
        while n < args.frames:
            frame = source.read()
            if frame is None:
                break
            n += 1
            lum = (frame[..., 0] * 0.299 + frame[..., 1] * 0.587
                   + frame[..., 2] * 0.114)
            luminances.append(float(np.mean(lum)))
            variances.append(float(np.std(lum)))
            if prev is not None:
                diff = np.abs(prev.astype(np.float64) - frame.astype(np.float64))
                motion.append(float(np.mean(diff) / 255.0))
            prev = frame

    if not luminances:
        print("[error] no frames")
        return 1

    mean_motion = float(np.mean(motion)) if motion else 0.0
    mean_var = float(np.mean(variances))
    mean_lum = float(np.mean(luminances))
    density = float(min(1.0, max(mean_motion * 25.0, mean_var / 80.0)))
    sun = float(min(1.0, mean_lum / 200.0))

    print(f"[run] frames consumed: {n}")
    print(f"[run] mean motion: {mean_motion:.4f}  variance: {mean_var:.2f}  "
          f"-> density proxy: {density:.2f}")
    print(f"[run] mean luminance: {mean_lum:.1f}  -> sun proxy: {sun:.2f}")
    _hr()

    obs = generate_zone_observation(
        zone_id=args.zone_id, zone_kind=args.zone_kind,
        density_pressure=density,
        in_water_motion=args.in_water,
        sun_intensity=sun,
        lost_child_flag=args.lost_child,
    )
    report = CoastSafetyEngine().review(coast_id="WEBCAM_COAST", zones=[obs])
    print(report.as_text())
    _hr()
    print("(real deployment maps motion/luminance to CoastZoneObservation fields)")
    _hr()
    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
