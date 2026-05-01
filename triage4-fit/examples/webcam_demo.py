"""triage4-fit — webcam demo (Phase 10 stationary-camera support).

Pilot adoption of the flagship's `frame_source` pattern for sibling-
level camera input. Captures frames from a real USB webcam (or a
synthetic fallback), measures left-vs-right luminance imbalance over
the captured frames, and uses the resulting variance as the
``asymmetry_severity`` parameter for ``demo_session("squat", ...)``.

This is **not a real pose detector** — it's a demonstration that the
sibling can take camera input and feed a domain-specific scalar into
its engine. A real deployment would replace the L/R luminance
heuristic with a proper joint-pose extractor (mediapipe, blazepose,
etc.) and feed real pose_frames into ``ExerciseSession``.

Run from the project root:

    python examples/webcam_demo.py                 # auto-fallback (synthetic if no webcam)
    python examples/webcam_demo.py --source 0      # force webcam 0
    python examples/webcam_demo.py --synthetic     # force synthetic
    python examples/webcam_demo.py --frames 90     # number of frames

Optional dep: ``pip install opencv-python``. Without it the script
falls back to the synthetic frame source and still exits 0.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from triage4_fit.form_check.rapid_form_engine import RapidFormEngine  # noqa: E402
from triage4_fit.perception import (  # noqa: E402
    FrameSourceUnavailable,
    SyntheticFrameSource,
    build_opencv_frame_source,
)
from triage4_fit.sim.synthetic_session import demo_session  # noqa: E402


def _hr() -> None:
    print("-" * 70)


def _build_source(args: argparse.Namespace):
    if args.synthetic:
        print("[source] forced synthetic")
        return SyntheticFrameSource(
            pattern="moving_square", n_frames=args.frames,
            fs_hz=args.fps, width=64, height=48, seed=0,
        ), "synthetic"

    if args.source is not None:
        print(f"[source] attempting webcam source {args.source!r}")
        try:
            return build_opencv_frame_source(args.source), "webcam"
        except FrameSourceUnavailable as exc:
            print(f"[source] webcam unavailable ({exc}); falling back to synthetic")

    try:
        return build_opencv_frame_source(0), "webcam"
    except FrameSourceUnavailable as exc:
        print(f"[source] auto-detect failed ({exc}); using synthetic")
    return SyntheticFrameSource(
        pattern="moving_square", n_frames=args.frames, fs_hz=args.fps,
        width=64, height=48, seed=0,
    ), "synthetic"


def _measure_lr_imbalance(frame: np.ndarray) -> float:
    """Mean luminance of the left half minus the right half, abs-normalised.

    Used as a crude proxy for L/R asymmetry — a person leaning left
    or right under a fixed camera produces a non-zero imbalance.
    Returns a value in [0, 1].
    """
    h, w, _ = frame.shape
    half = w // 2
    if half == 0:
        return 0.0
    left = frame[:, :half].astype(np.float64)
    right = frame[:, half:].astype(np.float64)
    lum_l = np.mean(left[..., 0] * 0.299 + left[..., 1] * 0.587 + left[..., 2] * 0.114)
    lum_r = np.mean(right[..., 0] * 0.299 + right[..., 1] * 0.587 + right[..., 2] * 0.114)
    if (lum_l + lum_r) <= 0:
        return 0.0
    return float(abs(lum_l - lum_r) / max(1.0, lum_l + lum_r))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=None, help="OpenCV source (index / URL / file)")
    parser.add_argument("--synthetic", action="store_true", help="force synthetic source")
    parser.add_argument("--frames", type=int, default=60, help="frames to collect")
    parser.add_argument("--fps", type=float, default=30.0, help="expected fps")
    parser.add_argument("--exercise", default="squat",
                        choices=["squat", "pushup", "deadlift"])
    args = parser.parse_args(argv)

    source, source_kind = _build_source(args)
    print(f"[config] source={source_kind}  exercise={args.exercise}  "
          f"frames={args.frames}  fps={args.fps}")
    _hr()

    imbalances: list[float] = []
    frames_consumed = 0
    with source:
        while frames_consumed < args.frames:
            frame = source.read()
            if frame is None:
                break
            frames_consumed += 1
            imbalances.append(_measure_lr_imbalance(frame))

    if not imbalances:
        print("[error] no frames captured")
        return 1

    mean_imbalance = float(np.mean(imbalances))
    var_imbalance = float(np.std(imbalances))
    # Map measured imbalance → asymmetry_severity in [0, 0.7].
    severity = float(min(0.7, mean_imbalance * 5 + var_imbalance * 3))
    rep_count = max(3, frames_consumed // 12)

    print(f"[run] frames consumed: {frames_consumed}")
    print(f"[run] mean L/R imbalance: {mean_imbalance:.4f}")
    print(f"[run] imbalance std-dev: {var_imbalance:.4f}")
    print(f"[run] derived asymmetry_severity: {severity:.3f}")
    print(f"[run] derived rep_count: {rep_count}")
    _hr()

    # Build a synthetic session whose asymmetry parameter is driven by
    # the actual camera observations.
    session = demo_session(
        args.exercise,                   # type: ignore[arg-type]
        rep_count=rep_count,
        asymmetry_severity=severity,
    )
    briefing = RapidFormEngine().review(session)

    print(briefing.as_text())
    _hr()
    print("✓ webcam demo complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
