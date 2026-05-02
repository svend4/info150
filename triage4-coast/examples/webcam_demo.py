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
    slice_panorama,
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
    parser.add_argument("--n-zones", type=int, default=1,
                        help=("split each frame into N vertical slices, "
                              "each treated as its own zone (use with a "
                              "panoramic / fisheye camera)"))
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

    if args.n_zones < 1:
        print(f"[error] --n-zones must be >= 1, got {args.n_zones}")
        return 2

    source, source_kind = _build_source(args)
    print(f"[config] source={source_kind}  zone={args.zone_id} ({args.zone_kind})  "
          f"in_water={args.in_water:.2f}  frames={args.frames}  fps={args.fps}  "
          f"n_zones={args.n_zones}")
    _hr()

    # Per-slice rolling stats. With --n-zones N we keep N parallel
    # accumulators and fold each frame's slices into them.
    motion: list[list[float]] = [[] for _ in range(args.n_zones)]
    luminances: list[list[float]] = [[] for _ in range(args.n_zones)]
    variances: list[list[float]] = [[] for _ in range(args.n_zones)]
    prev_slices: list[np.ndarray] | None = None
    n = 0
    with source:
        while n < args.frames:
            frame = source.read()
            if frame is None:
                break
            n += 1
            try:
                slices = (
                    [frame] if args.n_zones == 1
                    else slice_panorama(frame, args.n_zones)
                )
            except (TypeError, ValueError) as exc:
                print(f"[error] slice_panorama: {exc}")
                return 2
            for i, sl in enumerate(slices):
                lum = (sl[..., 0] * 0.299 + sl[..., 1] * 0.587
                       + sl[..., 2] * 0.114)
                luminances[i].append(float(np.mean(lum)))
                variances[i].append(float(np.std(lum)))
                if prev_slices is not None and i < len(prev_slices):
                    diff = np.abs(
                        prev_slices[i].astype(np.float64)
                        - sl.astype(np.float64)
                    )
                    motion[i].append(float(np.mean(diff) / 255.0))
            prev_slices = slices

    if not luminances[0]:
        print("[error] no frames")
        return 1

    print(f"[run] frames consumed: {n}")
    _hr()

    zones = []
    for i in range(args.n_zones):
        m = float(np.mean(motion[i])) if motion[i] else 0.0
        v = float(np.mean(variances[i]))
        lu = float(np.mean(luminances[i]))
        density = float(min(1.0, max(m * 25.0, v / 80.0)))
        sun = float(min(1.0, lu / 200.0))
        zone_id = (
            args.zone_id if args.n_zones == 1
            else f"{args.zone_id}-{i:02d}"
        )
        print(f"[zone {zone_id}] motion={m:.4f} var={v:.2f} lum={lu:.1f} "
              f"-> density={density:.2f} sun={sun:.2f}")
        zones.append(generate_zone_observation(
            zone_id=zone_id, zone_kind=args.zone_kind,
            density_pressure=density,
            in_water_motion=args.in_water,
            sun_intensity=sun,
            lost_child_flag=args.lost_child,
        ))

    _hr()
    report = CoastSafetyEngine().review(coast_id="WEBCAM_COAST", zones=zones)
    print(report.as_text())
    _hr()
    print("(real deployment maps motion/luminance to CoastZoneObservation fields)")
    _hr()
    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
