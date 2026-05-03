"""Frame sources — uniform access to RGB frames from any origin.

Part of Phase 10 Stage 2. Gives the rest of the perception layer a
single surface it can iterate over without caring whether frames come
from a webcam, an RTSP stream, a recorded video file, or an in-memory
synthetic generator.

Three sources ship in this module:

- ``LoopbackFrameSource`` — deterministic, in-memory, yields from a
  preloaded list of frames. Always available (numpy is a base dep).
  Used in every test and as the CI-safe fallback for the webcam demo.
- ``SyntheticFrameSource`` — generates programmatic RGB frames on
  demand (gradient / moving square / ambient-lit face proxy). Useful
  for the Eulerian vitals demo without needing a real camera.
- ``build_opencv_frame_source`` — lazy factory over ``cv2.VideoCapture``.
  Raises ``FrameSourceUnavailable`` if OpenCV is missing. Accepts any
  source OpenCV accepts (int index for USB cameras, RTSP URL, file
  path, gstreamer pipeline).

All three implement the ``FrameSource`` Protocol: ``read() ->
np.ndarray | None``, ``close() -> None``, plus context-manager
support.
"""

from __future__ import annotations

import math
import time
from typing import Iterable, Iterator, Protocol, runtime_checkable

import numpy as np


class FrameSourceUnavailable(RuntimeError):
    """Raised when a real-backend factory cannot locate its dep (cv2)."""


@runtime_checkable
class FrameSource(Protocol):
    """Minimal frame-source contract.

    ``read()`` returns the next frame as a ``(H, W, 3)`` uint8 RGB
    ndarray, or ``None`` when the source is exhausted / unavailable.
    The bridge does not block forever — implementations should return
    ``None`` on timeout rather than hang.
    """

    def read(self) -> np.ndarray | None: ...
    def close(self) -> None: ...


# ---------------------------------------------------------------------------
# Loopback — preloaded frames
# ---------------------------------------------------------------------------


class LoopbackFrameSource:
    """Yields from a preloaded list of frames. Test / CI workhorse."""

    def __init__(self, frames: Iterable[np.ndarray]) -> None:
        self._frames: list[np.ndarray] = [
            self._validate(i, f) for i, f in enumerate(frames)
        ]
        self._idx = 0
        self._closed = False

    @staticmethod
    def _validate(index: int, frame: np.ndarray) -> np.ndarray:
        if not isinstance(frame, np.ndarray):
            raise TypeError(f"frame {index} is not a numpy array")
        if frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError(
                f"frame {index} must be (H, W, 3), got shape {frame.shape}"
            )
        return frame

    def read(self) -> np.ndarray | None:
        if self._closed or self._idx >= len(self._frames):
            return None
        frame = self._frames[self._idx]
        self._idx += 1
        return frame

    def close(self) -> None:
        self._closed = True

    @property
    def frame_count(self) -> int:
        return len(self._frames)

    @property
    def position(self) -> int:
        return self._idx

    def __enter__(self) -> "LoopbackFrameSource":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def __iter__(self) -> Iterator[np.ndarray]:
        while True:
            frame = self.read()
            if frame is None:
                return
            yield frame


# ---------------------------------------------------------------------------
# Synthetic — procedurally generated
# ---------------------------------------------------------------------------


class SyntheticFrameSource:
    """Programmatic RGB frames for demos and Eulerian HR tests.

    Patterns:
      - ``pulse`` — a centred disc whose luminance oscillates at
        ``hr_hz``. Feeds the Eulerian vitals extractor.
      - ``gradient`` — diagonal colour ramp; useful as a
        non-degenerate bitmap for YOLO smoke tests.
      - ``moving_square`` — a white rectangle travelling left-to-
        right; useful for testing motion / tracking paths.

    Deterministic: a fixed ``seed`` gives byte-for-byte reproducible
    frames across runs and across Python versions.
    """

    VALID_PATTERNS = ("pulse", "gradient", "moving_square")

    def __init__(
        self,
        pattern: str = "pulse",
        *,
        n_frames: int = 300,
        width: int = 64,
        height: int = 48,
        fs_hz: float = 30.0,
        hr_hz: float = 1.2,
        seed: int = 0,
    ) -> None:
        if pattern not in self.VALID_PATTERNS:
            raise ValueError(
                f"pattern must be one of {self.VALID_PATTERNS}, got {pattern!r}"
            )
        if n_frames <= 0 or width <= 0 or height <= 0:
            raise ValueError("n_frames / width / height must be positive")
        if fs_hz <= 0 or hr_hz <= 0:
            raise ValueError("fs_hz / hr_hz must be positive")
        self._pattern = pattern
        self._n = int(n_frames)
        self._w = int(width)
        self._h = int(height)
        self._fs = float(fs_hz)
        self._hr = float(hr_hz)
        self._rng = np.random.default_rng(seed)
        self._idx = 0
        self._closed = False

    @property
    def n_frames(self) -> int:
        return self._n

    def read(self) -> np.ndarray | None:
        if self._closed or self._idx >= self._n:
            return None
        t = self._idx / self._fs
        frame = self._render(t)
        self._idx += 1
        return frame

    def close(self) -> None:
        self._closed = True

    def __enter__(self) -> "SyntheticFrameSource":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    # -- patterns ------------------------------------------------------

    def _render(self, t: float) -> np.ndarray:
        if self._pattern == "pulse":
            return self._render_pulse(t)
        if self._pattern == "gradient":
            return self._render_gradient()
        return self._render_moving_square(t)

    def _render_pulse(self, t: float) -> np.ndarray:
        base = 128.0 + 10.0 * math.sin(2 * math.pi * self._hr * t)
        frame = np.full((self._h, self._w, 3), base, dtype=np.float64)
        frame += self._rng.normal(0.0, 1.0, frame.shape)
        return np.clip(frame, 0.0, 255.0).astype(np.uint8)

    def _render_gradient(self) -> np.ndarray:
        xs = np.linspace(0, 255, self._w, dtype=np.float64)
        ys = np.linspace(0, 255, self._h, dtype=np.float64)
        X, Y = np.meshgrid(xs, ys)
        frame = np.stack([X, Y, (X + Y) / 2.0], axis=-1)
        return np.clip(frame, 0.0, 255.0).astype(np.uint8)

    def _render_moving_square(self, t: float) -> np.ndarray:
        frame = np.zeros((self._h, self._w, 3), dtype=np.uint8)
        # Travel one full width per second.
        period = max(1.0, self._w / self._fs)
        x0 = int((t * self._w / period)) % self._w
        x1 = min(self._w, x0 + max(2, self._w // 8))
        y0 = self._h // 4
        y1 = min(self._h, y0 + max(2, self._h // 2))
        frame[y0:y1, x0:x1] = 255
        return frame


# ---------------------------------------------------------------------------
# Real-backend factory (OpenCV)
# ---------------------------------------------------------------------------


def build_opencv_frame_source(  # pragma: no cover
    source: int | str = 0,
    *,
    width: int | None = None,
    height: int | None = None,
    fps: float | None = None,
    read_timeout_s: float = 2.0,
):
    """Open a real frame source via ``cv2.VideoCapture``.

    ``source`` follows OpenCV conventions:

    - integer index (``0`` by default) — USB / built-in webcam;
    - path — local video file;
    - URL — ``rtsp://...``, ``http://...``, gstreamer pipeline.

    Raises ``FrameSourceUnavailable`` if:

    - ``cv2`` is not installed;
    - the source cannot be opened;
    - the source doesn't deliver a first frame within
      ``read_timeout_s``.

    Returns a ``_OpenCVFrameSource`` that satisfies ``FrameSource``.
    """
    try:
        import cv2
    except ImportError as exc:
        raise FrameSourceUnavailable(
            "cv2 (opencv-python) is not installed. Install with "
            "'pip install opencv-python' or use LoopbackFrameSource / "
            "SyntheticFrameSource in tests."
        ) from exc

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise FrameSourceUnavailable(
            f"cv2.VideoCapture could not open source {source!r}. "
            "Check device index / URL / codec availability."
        )

    if width is not None:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(width))
    if height is not None:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(height))
    if fps is not None:
        cap.set(cv2.CAP_PROP_FPS, float(fps))

    # Smoke-test: read one frame. Some cameras need a few hundred ms
    # to warm up — we budget ``read_timeout_s``.
    deadline = time.time() + float(read_timeout_s)
    while time.time() < deadline:
        ok, _frame = cap.read()
        if ok:
            break
    else:
        cap.release()
        raise FrameSourceUnavailable(
            f"no frame from {source!r} within {read_timeout_s}s"
        )

    return _OpenCVFrameSource(cap, cv2_module=cv2)


class _OpenCVFrameSource:  # pragma: no cover
    """Thin wrapper over ``cv2.VideoCapture`` that returns RGB ndarrays.

    OpenCV natively delivers BGR; we convert to RGB so the rest of
    triage4 (Eulerian vitals, YOLO, signature extractors) sees a
    consistent channel order.
    """

    def __init__(self, capture, cv2_module) -> None:
        self._cap = capture
        self._cv2 = cv2_module
        self._closed = False

    def read(self) -> np.ndarray | None:
        if self._closed:
            return None
        ok, bgr = self._cap.read()
        if not ok or bgr is None:
            return None
        return self._cv2.cvtColor(bgr, self._cv2.COLOR_BGR2RGB)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._cap.release()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()


# ---------------------------------------------------------------------------
# UX helpers — discovery + preview
# ---------------------------------------------------------------------------


def enumerate_cameras(  # pragma: no cover
    max_index: int = 10,
) -> list[dict[str, object]]:
    """Probe local camera indices ``0..max_index-1`` and report which open.

    For each probed index returns one dict::

        {"index": 0, "opened": True, "width": 640, "height": 480, "fps": 30.0}
        {"index": 5, "opened": False, "error": "cannot open"}

    Used by the ``--list-cameras`` flag in webcam demos so users can
    pick a working ``--source`` value before running the full demo.
    Raises :class:`FrameSourceUnavailable` if ``cv2`` is not installed.
    """
    try:
        import cv2
    except ImportError as exc:
        raise FrameSourceUnavailable(
            "cv2 (opencv-python) is not installed. Install with "
            "'pip install opencv-python'."
        ) from exc

    results: list[dict[str, object]] = []
    for idx in range(int(max_index)):
        cap = cv2.VideoCapture(idx)
        try:
            if not cap.isOpened():
                results.append({"index": idx, "opened": False, "error": "cannot open"})
                continue
            ok, _frame = cap.read()
            if not ok:
                results.append({"index": idx, "opened": False, "error": "no frame"})
                continue
            results.append({
                "index": idx,
                "opened": True,
                "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                "fps": float(cap.get(cv2.CAP_PROP_FPS)),
            })
        finally:
            cap.release()
    return results


def format_camera_table(rows: list[dict[str, object]]) -> str:
    """Render :func:`enumerate_cameras` output as a human-readable table."""
    lines = ["index  status     resolution    fps    note"]
    lines.append("-" * 50)
    for r in rows:
        idx = r.get("index")
        if r.get("opened"):
            w, h, fps = r.get("width"), r.get("height"), r.get("fps")
            lines.append(f"  {idx:<4} available  {w}x{h:<6}  {fps:<5.1f}  use --source {idx}")
        else:
            err = r.get("error", "")
            lines.append(f"  {idx:<4} -          -             -      {err}")
    return "\n".join(lines)


def run_camera_preview(  # pragma: no cover
    source: int | str = 0,
    *,
    window_title: str = "preview - SPACE: continue   Q/ESC: quit",
    max_wait_s: float = 60.0,
) -> str:
    """Show a live-preview window before the demo collects frames.

    Opens its own ``cv2.VideoCapture`` (separate from the demo's source)
    for the duration of the preview, displays each frame in a window
    with on-screen instructions, and waits for the user to press
    ``SPACE`` (returns ``"continue"``) or ``Q`` / ``ESC`` (returns
    ``"quit"``). Auto-quits after ``max_wait_s``.

    Raises :class:`FrameSourceUnavailable` if ``cv2`` is missing or the
    source cannot be opened. Display-unavailable failures (headless
    build, no DISPLAY) bubble up as the underlying ``cv2.error``.
    """
    try:
        import cv2
    except ImportError as exc:
        raise FrameSourceUnavailable(
            "cv2 (opencv-python) is not installed."
        ) from exc

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise FrameSourceUnavailable(
            f"cv2.VideoCapture could not open source {source!r}."
        )

    deadline = time.time() + float(max_wait_s)
    decision = "quit"
    try:
        while time.time() < deadline:
            ok, bgr = cap.read()
            if not ok:
                continue
            cv2.putText(
                bgr, "SPACE: continue   Q/ESC: quit", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2,
            )
            cv2.imshow(window_title, bgr)
            key = cv2.waitKey(1) & 0xFF
            if key == ord(" "):
                decision = "continue"
                break
            if key in (ord("q"), 27):  # 27 = ESC
                decision = "quit"
                break
    finally:
        cap.release()
        try:
            cv2.destroyWindow(window_title)
        except Exception:
            pass
    return decision
