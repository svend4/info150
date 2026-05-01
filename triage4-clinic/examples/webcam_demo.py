"""triage4-clinic — webcam demo (Phase 10 stationary-camera support).

Patient self-cam input pilot (telemedicine pre-screening). Captures
frames, uses an OpenCV face-presence proxy as a "patient is in front
of the camera" signal, then runs ``ClinicalPreTriageEngine`` over the
synthetic demo submissions. Reports the engine output alongside the
camera signal.

**STRONG PRIVACY NOTE:** clinic camera input is **PHI** (Protected
Health Information). This demo is for **developer testing only**.
Real deployments must follow HIPAA / GDPR / local clinical-data law,
encrypt data at rest + in transit, log every access, and obtain
explicit patient informed consent. The library is decision-support
only and ships with strict claims-guard text — no diagnosis, no
treatment recommendation. See ../docs/PHILOSOPHY.md.

This is **not** a real clinical-vitals extractor — production deploys
need rPPG (heart-rate from face), respiratory-pattern from chest, and
acoustic models. The frame-source layer is the same.

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

from triage4_clinic.clinic_triage.triage_engine import ClinicalPreTriageEngine  # noqa: E402
from triage4_clinic.perception import (  # noqa: E402
    FrameSourceUnavailable,
    SyntheticFrameSource,
    build_opencv_frame_source,
)
from triage4_clinic.sim.synthetic_self_report import demo_submissions  # noqa: E402


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
    try:
        import cv2

        path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        cascade = cv2.CascadeClassifier(path)
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
        def detect(frame: np.ndarray) -> bool:
            return float(np.std(frame.astype(np.float64))) > 5.0
        return detect, "luminance-fallback"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=None)
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--frames", type=int, default=60)
    parser.add_argument("--fps", type=float, default=30.0)
    args = parser.parse_args(argv)

    print("STRONG PRIVACY NOTE: clinic camera = PHI. Developer-test only.")
    print("Production deployments must satisfy HIPAA / GDPR / local law.")
    _hr()

    source, source_kind = _build_source(args)
    detect, detect_kind = _build_face_detector()
    print(f"[config] source={source_kind}  detector={detect_kind}  "
          f"frames={args.frames}  fps={args.fps}")
    _hr()

    presence = 0
    n = 0
    with source:
        while n < args.frames:
            frame = source.read()
            if frame is None:
                break
            n += 1
            if detect(frame):
                presence += 1

    if not n:
        print("[error] no frames")
        return 1

    presence_rate = presence / n
    print(f"[run] frames consumed: {n}")
    print(f"[run] face presence: {presence}/{n} ({presence_rate * 100:.1f}%)")
    _hr()

    submissions = demo_submissions()
    engine = ClinicalPreTriageEngine()
    print(f"running ClinicalPreTriageEngine over {len(submissions)} synthetic "
          "self-report submissions")
    for obs in submissions[:3]:
        report = engine.review(obs)
        a = report.assessment
        print(f"  patient {a.patient_token}  recommendation={a.recommendation}  "
              f"overall={a.overall:.2f}")
    _hr()
    print(f"camera-observed face presence: {presence_rate * 100:.1f}%")
    print("(real deployment maps frames → cardiac/respiratory rPPG samples — PHI)")
    _hr()
    print("✓ webcam demo complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
