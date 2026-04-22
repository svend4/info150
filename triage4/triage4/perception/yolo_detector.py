"""YOLO-based person detector — real backend for ``PersonDetector``.

Part of Phase 9b. Replaces the stub ``PersonDetector.detect`` (which
raises ``NotImplementedError``) with two concrete implementations:

- ``LoopbackYOLODetector`` — deterministic in-memory fake: returns
  canned bounding boxes registered by the test harness. Lets
  pipelines be integration-tested without downloading a 6 MB weights
  file or loading PyTorch.
- ``build_ultralytics_detector()`` — lazy factory that imports
  ``ultralytics`` and returns a wrapper around ``YOLO(model)``. Raises
  ``DetectorUnavailable`` with install instructions if the package is
  not installed, matching the platform-bridge pattern from Phase 8.
"""

from __future__ import annotations

from typing import Any, Iterable

from triage4.perception.person_detector import PersonDetector


class DetectorUnavailable(RuntimeError):
    """Raised when the real-backend factory can't find its SDK."""


class LoopbackYOLODetector(PersonDetector):
    """In-process fake detector. Preload ``detections`` per frame index."""

    def __init__(
        self,
        canned_detections: Iterable[list[dict]] | None = None,
        confidence_floor: float = 0.0,
    ) -> None:
        if not 0.0 <= confidence_floor <= 1.0:
            raise ValueError(
                f"confidence_floor must be in [0, 1], got {confidence_floor}"
            )
        self._canned: list[list[dict]] = list(canned_detections or [])
        self._confidence_floor = confidence_floor
        self._calls = 0

    @property
    def call_count(self) -> int:
        return self._calls

    def load(self, detections: Iterable[list[dict]]) -> None:
        """Load a new canned sequence of per-frame detections."""
        self._canned = list(detections)
        self._calls = 0

    def detect(self, frame_rgb: Any) -> list[dict]:
        idx = self._calls
        self._calls += 1
        if idx >= len(self._canned):
            return []
        return [
            d
            for d in self._canned[idx]
            if float(d.get("score", 0.0)) >= self._confidence_floor
        ]


class _UltralyticsWrapper(PersonDetector):
    """Thin wrapper over ``ultralytics.YOLO`` that reshapes output to our
    ``{'bbox': [x1, y1, x2, y2], 'score': float}`` contract."""

    def __init__(self, yolo_instance: Any, class_filter: int = 0) -> None:
        self._yolo = yolo_instance
        self._class_filter = int(class_filter)  # COCO class 0 = person

    def detect(self, frame_rgb: Any) -> list[dict]:  # pragma: no cover
        results = self._yolo.predict(frame_rgb, verbose=False)
        if not results:
            return []
        r = results[0]
        out: list[dict] = []
        for box in r.boxes:
            cls = int(box.cls.item()) if hasattr(box.cls, "item") else int(box.cls)
            if cls != self._class_filter:
                continue
            xyxy = box.xyxy[0].tolist() if hasattr(box, "xyxy") else []
            if len(xyxy) != 4:
                continue
            score = float(box.conf.item()) if hasattr(box, "conf") else 0.0
            out.append(
                {
                    "bbox": [float(v) for v in xyxy],
                    "score": score,
                }
            )
        return out


def build_ultralytics_detector(
    model_name: str = "yolov8n.pt",
    class_filter: int = 0,
) -> _UltralyticsWrapper:
    """Lazy-load ultralytics + return a real YOLO-backed detector.

    Raises:
        DetectorUnavailable: if ``ultralytics`` is not installed.
    """
    try:
        from ultralytics import YOLO  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise DetectorUnavailable(
            "ultralytics is not installed. Install with "
            "'pip install ultralytics' or use LoopbackYOLODetector "
            "in tests."
        ) from exc
    model = YOLO(model_name)  # pragma: no cover — downloads weights
    return _UltralyticsWrapper(model, class_filter=class_filter)
