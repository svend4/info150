"""triage4-drive — webcam demo (Phase 10 stationary-camera support).

Pilot adoption of the flagship's `frame_source` pattern for sibling-
level camera input. Captures frames from a real USB / dash webcam
(or a synthetic fallback), measures **face presence** per frame
using OpenCV's bundled Haar cascade (when opencv-python is
installed), and uses the absence-rate as a PERCLOS proxy fed into
``DriverObservation.eye_samples``.

This is **not a real eye-aspect-ratio extractor** — it's a
demonstration that the sibling can take dashcam input and feed a
domain-specific scalar series into its engine. A real deployment
would replace the face-presence heuristic with a proper face-mesh +
eye-landmark pipeline (mediapipe / dlib's face_recognition).

Run from the project root:

    python examples/webcam_demo.py                 # auto-fallback (synthetic if no webcam)
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

from triage4_drive.core.models import DriverObservation, EyeStateSample  # noqa: E402
from triage4_drive.driver_monitor.monitoring_engine import DriverMonitoringEngine  # noqa: E402
from triage4_drive.perception import (  # noqa: E402
    FrameSourceUnavailable,
    SyntheticFrameSource,
    build_opencv_frame_source,
)


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


def _build_face_detector():
    """Return a callable ``(frame) -> bool`` that detects face presence.

    Uses OpenCV's bundled Haar cascade when available. Falls back to a
    luminance-variance heuristic when cv2 is missing — that's what
    the synthetic source path uses anyway.
    """
    try:
        import cv2

        cascade_path = (
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        cascade = cv2.CascadeClassifier(cascade_path)
        if cascade.empty():
            raise RuntimeError("Haar cascade load failed")

        def detect(frame: np.ndarray) -> bool:
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            faces = cascade.detectMultiScale(
                gray, scaleFactor=1.2, minNeighbors=4, minSize=(20, 20),
            )
            return len(faces) > 0

        return detect, "haar-cascade"
    except Exception:
        # Fallback — flag "face present" if frame variance is non-trivial.
        # Synthetic moving_square pattern has variance, so this returns
        # True often enough for the engine path to be exercised.
        def detect(frame: np.ndarray) -> bool:
            return float(np.std(frame.astype(np.float64))) > 5.0

        return detect, "luminance-variance-fallback"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=None, help="OpenCV source (index / URL / file)")
    parser.add_argument("--synthetic", action="store_true", help="force synthetic source")
    parser.add_argument("--frames", type=int, default=60, help="frames to collect")
    parser.add_argument("--fps", type=float, default=30.0, help="expected fps")
    args = parser.parse_args(argv)

    source, source_kind = _build_source(args)
    detect, detect_kind = _build_face_detector()
    print(f"[config] source={source_kind}  detector={detect_kind}  "
          f"frames={args.frames}  fps={args.fps}")
    _hr()

    eye_samples: list[EyeStateSample] = []
    face_present_count = 0
    frames_consumed = 0
    with source:
        while frames_consumed < args.frames:
            frame = source.read()
            if frame is None:
                break
            t = frames_consumed / args.fps
            present = detect(frame)
            if present:
                face_present_count += 1
            # Eye closure proxy: 0.0 when face is detected (driver looking
            # at road), 1.0 when face is missing (turned away / eyes shut).
            closure = 0.0 if present else 1.0
            eye_samples.append(EyeStateSample(t_s=float(t), closure=closure))
            frames_consumed += 1

    if not eye_samples:
        print("[error] no frames captured")
        return 1

    presence_rate = face_present_count / max(1, frames_consumed)
    duration_s = max(1.0, frames_consumed / args.fps)

    print(f"[run] frames consumed: {frames_consumed}")
    print(f"[run] face present in: {face_present_count}/{frames_consumed} "
          f"frames ({presence_rate * 100:.1f}%)")
    print(f"[run] window duration: {duration_s:.1f}s")
    _hr()

    observation = DriverObservation(
        session_id="WEBCAM_DEMO",
        window_duration_s=duration_s,
        eye_samples=eye_samples,
        # Other channels left empty — the engine handles missing
        # channels by treating them as neutral / no-evidence.
        gaze_samples=[],
        posture_samples=[],
        can_samples=[],
    )
    score, alerts = DriverMonitoringEngine().review(observation)

    print(f"alert_level: {score.alert_level}")
    print(f"overall risk:    {score.overall:.2f}")
    print(f"perclos:         {score.perclos:.2f}")
    print(f"distraction:     {score.distraction:.2f}")
    print(f"incapacitation:  {score.incapacitation:.2f}")
    print(f"alerts: {len(alerts)}")
    for a in alerts:
        print(f"  [{a.level}] {a.kind}: {a.text}")
    _hr()
    print("✓ webcam demo complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
