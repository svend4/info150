"""triage4 — Phase 10 Stage 2 webcam demo.

Runs the perception → Eulerian vitals path against a real frame
source. Tries, in order:

1. A USB webcam via ``build_opencv_frame_source(0)`` — real camera.
2. A ``SyntheticFrameSource`` pulsing at a known HR — falls back
   automatically if OpenCV is missing or no webcam is connected.

Real-YOLO detection is attempted if ``ultralytics`` is installed,
otherwise ``LoopbackYOLODetector`` is used with a single canned
bounding box so the rest of the pipeline still runs.

The script is deliberately CI-safe: without cv2 or ultralytics it
falls through to the synthetic path and still exits 0.

Run from the project root:

    python examples/webcam_triage_demo.py                   # auto-fallback
    python examples/webcam_triage_demo.py --source 0        # force webcam
    python examples/webcam_triage_demo.py --synthetic       # force synthetic
    python examples/webcam_triage_demo.py --frames 90       # length
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from triage4.perception import (  # noqa: E402
    DetectorUnavailable,
    FrameSourceUnavailable,
    LoopbackYOLODetector,
    SyntheticFrameSource,
    build_opencv_frame_source,
    build_ultralytics_detector,
    enumerate_cameras,
    format_camera_table,
    run_camera_preview,
)
from triage4.triage_reasoning.vitals_estimation import VitalsEstimator  # noqa: E402


def _hr() -> None:
    print("-" * 70)


def _build_frame_source(args: argparse.Namespace):
    if args.synthetic:
        print("[source] forced synthetic")
        return SyntheticFrameSource(
            pattern="pulse",
            n_frames=args.frames,
            fs_hz=args.fps,
            hr_hz=1.2,
            width=64, height=48, seed=0,
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
        pattern="pulse", n_frames=args.frames, fs_hz=args.fps, hr_hz=1.2,
        width=64, height=48, seed=0,
    ), "synthetic-fallback"


def _build_detector():
    try:
        return build_ultralytics_detector(), "ultralytics"
    except DetectorUnavailable as exc:
        print(f"[detector] ultralytics unavailable ({exc}); using loopback")
        # Preload one canned detection per frame so the pipeline still runs.
        canned = [[{"bbox": [8.0, 8.0, 56.0, 40.0], "score": 0.92}]] * 600
        return LoopbackYOLODetector(canned_detections=canned), "loopback"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=None, help="OpenCV source (index / URL / file)")
    parser.add_argument("--synthetic", action="store_true", help="force synthetic source")
    parser.add_argument("--frames", type=int, default=90, help="frames to collect")
    parser.add_argument("--fps", type=float, default=30.0, help="expected fps")
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

    source, source_kind = _build_frame_source(args)
    detector, detector_kind = _build_detector()

    print(f"[config] source={source_kind}  detector={detector_kind}  "
          f"frames={args.frames}  fps={args.fps}")
    _hr()

    # Collect frames + a single ROI-mean time-series for Eulerian HR.
    luminance: list[float] = []
    n_detections = 0
    frames_consumed = 0

    with source:
        while frames_consumed < args.frames:
            frame = source.read()
            if frame is None:
                break
            frames_consumed += 1

            # 1. detector — run once per frame, count hits
            try:
                dets = detector.detect(frame)
            except Exception as exc:  # real YOLO can raise on degenerate input
                print(f"[detector] raised {exc!r} — skipping frame")
                dets = []
            n_detections += len(dets)

            # 2. Eulerian time-series — use the whole frame in the
            #    synthetic case; use the first detection's bbox when
            #    one is present (more clinically useful — it's the
            #    face / torso region).
            if dets:
                bbox = dets[0]["bbox"]
                x1, y1, x2, y2 = (int(v) for v in bbox)
                x1 = max(0, min(frame.shape[1] - 1, x1))
                y1 = max(0, min(frame.shape[0] - 1, y1))
                x2 = max(x1 + 1, min(frame.shape[1], x2))
                y2 = max(y1 + 1, min(frame.shape[0], y2))
                roi = frame[y1:y2, x1:x2]
            else:
                roi = frame

            # Mean luminance (grey) — cheap, works on any RGB frame.
            lum = float(np.mean(roi[..., 0] * 0.299
                                 + roi[..., 1] * 0.587
                                 + roi[..., 2] * 0.114))
            luminance.append(lum)

    print(f"[run] frames consumed: {frames_consumed}")
    print(f"[run] detections total: {n_detections}")
    print(f"[run] luminance samples: {len(luminance)}")

    _hr()

    # 3. FFT-based HR estimate from the luminance time-series.
    if len(luminance) >= 32:
        estimator = VitalsEstimator()
        try:
            # Use the same series for breathing + perfusion — we only
            # care about the HR band for this demo.
            est = estimator.estimate(
                breathing_curve=luminance,
                perfusion_series=luminance,
                fs_hz=args.fps,
            )
            print(f"[vitals] estimated HR: {est.heart_rate_bpm:.1f} bpm"
                  f"  (confidence {est.hr_confidence:.2f})")
            print(f"[vitals] estimated RR: {est.respiration_rate_bpm:.1f} bpm"
                  f"  (confidence {est.rr_confidence:.2f})")
        except Exception as exc:
            print(f"[vitals] estimator raised: {exc!r}")
    else:
        print(f"[vitals] too few samples ({len(luminance)}) — need >= 32")

    _hr()
    print("✓ webcam demo complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
