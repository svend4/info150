"""triage4-rescue — webcam demo (Phase 10 stationary-camera support).

Stand-off / scene-camera input pilot (mass-casualty triage support).
Captures frames, measures **frame variance** as a "casualty count"
proxy and **inter-frame motion** as a "scene activity" proxy, then
runs ``StartProtocolEngine`` over the synthetic demo incident.
Reports both alongside.

**STRONG PRIVACY NOTE:** mass-casualty scene footage contains PHI-
equivalent imagery. This demo is for **developer testing only**.
Real deployments must follow incident-response data-handling rules
(many jurisdictions have specific provisions), encrypt at rest, and
limit retention. The library is decision-support only — START /
JumpSTART tags are resource-allocation hints, not clinical findings.

This is **not** real casualty detection — production deploys need
person-detection + pose + thermal sensors per casualty. The
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

from triage4_rescue.perception import (  # noqa: E402
    FrameSourceUnavailable,
    SyntheticFrameSource,
    build_opencv_frame_source,
    enumerate_cameras,
    format_camera_table,
    run_camera_preview,
)
from triage4_rescue.sim.synthetic_incident import demo_incident  # noqa: E402
from triage4_rescue.triage_protocol.protocol_engine import StartProtocolEngine  # noqa: E402


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

    print("STRONG PRIVACY NOTE: mass-casualty footage = PHI-equivalent.")
    print("Developer-test only. Production deploys must follow IR data-handling law.")
    _hr()

    source, source_kind = _build_source(args)
    print(f"[config] source={source_kind}  frames={args.frames}  fps={args.fps}")
    _hr()

    motion: list[float] = []
    variances: list[float] = []
    prev: np.ndarray | None = None
    n = 0
    with source:
        while n < args.frames:
            frame = source.read()
            if frame is None:
                break
            n += 1
            variances.append(float(np.std(frame.astype(np.float64))))
            if prev is not None:
                diff = np.abs(prev.astype(np.float64) - frame.astype(np.float64))
                motion.append(float(np.mean(diff) / 255.0))
            prev = frame

    if not variances:
        print("[error] no frames")
        return 1

    mean_motion = float(np.mean(motion)) if motion else 0.0
    mean_variance = float(np.mean(variances))
    activity_proxy = float(min(1.0, mean_motion * 25.0))
    scene_complexity = float(min(1.0, mean_variance / 80.0))

    print(f"[run] frames consumed: {n}")
    print(f"[run] mean motion: {mean_motion:.4f} (scene activity: {activity_proxy:.2f})")
    print(f"[run] mean variance: {mean_variance:.2f} "
          f"(scene complexity: {scene_complexity:.2f})")
    _hr()

    casualties = demo_incident(incident_id="WEBCAM_INCIDENT")
    report = StartProtocolEngine().review(
        incident_id="WEBCAM_INCIDENT", casualties=casualties,
    )
    print(f"incident_id: {report.incident_id}  "
          f"casualties: {report.casualty_count}")
    counts: dict[str, int] = {"immediate": 0, "delayed": 0, "minor": 0, "deceased": 0}
    for a in report.assessments:
        counts[a.tag] = counts.get(a.tag, 0) + 1
    print(f"  counts: {counts}")
    print(f"  cues: {len(report.cues)}")
    _hr()
    print(f"camera-observed scene activity: {activity_proxy:.2f}  "
          f"complexity: {scene_complexity:.2f}")
    print("(real deployment maps frames → CivilianCasualty per-detection samples)")
    _hr()
    print("✓ webcam demo complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
