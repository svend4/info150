"""Perception layer for camera/video input — opt-in.

Three frame sources following a common ``FrameSource`` Protocol:

- ``LoopbackFrameSource`` — preloaded list of frames (CI-safe, no deps).
- ``SyntheticFrameSource`` — programmatic frame generator (no hardware).
- ``build_opencv_frame_source`` — lazy factory wrapping
  ``cv2.VideoCapture``. Requires ``opencv-python`` (in the ``[camera]``
  extra).

Copy-fork of the flagship's ``triage4.perception.frame_source`` —
each sibling owns its own copy under nautilus "compatibility, not
merger" policy.
"""

from __future__ import annotations

from .frame_source import (
    FrameSource,
    FrameSourceUnavailable,
    LoopbackFrameSource,
    RobustFrameSource,
    SyntheticFrameSource,
    build_opencv_frame_source,
    enumerate_cameras,
    format_camera_table,
    run_camera_preview,
    slice_panorama,
)

__all__ = [
    "FrameSource",
    "FrameSourceUnavailable",
    "LoopbackFrameSource",
    "RobustFrameSource",
    "SyntheticFrameSource",
    "build_opencv_frame_source",
    "enumerate_cameras",
    "format_camera_table",
    "run_camera_preview",
    "slice_panorama",
]
