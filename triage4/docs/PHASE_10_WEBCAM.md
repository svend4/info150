# Phase 10 — Stage 2: webcam + real YOLO

End-to-end path for testing the **real** perception layer with an
actual RGB camera. Any USB webcam, laptop-integrated camera, or
CCTV with an RTSP stream works. Cost: $0 (you almost certainly
already have one).

Closes RISK_REGISTER **CAL-002** (drift in trained YOLO detector
after deployment) for a single-camera setup, and provides the
substrate for incremental closure of **CAL-001** (thresholds
calibrated on synthetic only).

## 0. What's covered in this stage

- `perception.FrameSource` Protocol — uniform frame-read surface.
- `perception.LoopbackFrameSource` — CI-safe replay of preloaded
  frames.
- `perception.SyntheticFrameSource` — procedurally-generated RGB
  frames (pulse / gradient / moving_square patterns) for tests
  and synthetic-HR demos.
- `perception.build_opencv_frame_source` — lazy factory over
  `cv2.VideoCapture`. Handles USB cameras, video files, RTSP
  streams, gstreamer pipelines.
- `perception.build_ultralytics_detector` — lazy factory for a
  real YOLOv8 detector via `ultralytics`.
- `examples/webcam_triage_demo.py` — end-to-end demo with
  auto-fallback (tries real webcam, falls back to synthetic) and
  FFT-based HR estimate from the luminance time-series.

## 1. Install

The base install stays minimal. Add the perception extras only
when you want real cameras / detection:

```bash
pip install opencv-python       # frame source
pip install ultralytics          # YOLO (~6 MB model downloads on first use)
```

On Linux, a USB webcam is typically at `/dev/video0`. On macOS,
grant the terminal (or whatever process runs Python) camera access
under *System Settings → Privacy & Security → Camera*.

## 2. Smoke-test — synthetic fallback

No hardware needed. The demo gracefully falls back when cv2 /
ultralytics are missing:

```bash
python examples/webcam_triage_demo.py --synthetic --frames 120
```

Expected output (excerpt):

```
[source] forced synthetic
[detector] ultralytics unavailable (...); using loopback
[config] source=synthetic  detector=loopback  frames=120  fps=30.0
[run] frames consumed: 120
[run] detections total: 120
[run] luminance samples: 120
[vitals] estimated HR: 75.0 bpm  (confidence 1.00)
```

The synthetic `pulse` pattern oscillates at 1.2 Hz (= 72 bpm); a
recovered HR within ±3 bpm confirms the Eulerian pipeline is
working end-to-end.

## 3. Real webcam — single-camera HR

With `opencv-python` installed:

```bash
python examples/webcam_triage_demo.py --frames 150 --fps 30
```

The demo auto-detects `cv2.VideoCapture(0)`. Point the camera at
your face under reasonable lighting for ~5 s. The pipeline:

1. grabs 150 frames at 30 fps (≈ 5 s);
2. runs YOLOv8n on each (if installed) or skips to full-frame
   ROI (loopback detector);
3. extracts a scalar luminance per frame from the detected ROI;
4. FFTs the luminance series; returns the dominant frequency in
   the 0.8–3.5 Hz band as heart rate.

Typical real-webcam HR for a resting subject under decent lighting:
55–90 bpm with confidence > 0.4. Ambient lighting flicker can
bleed in above 0.9 confidence on a 100 Hz (Europe) or 120 Hz (US)
peak — that's why confidence is surfaced.

## 4. RTSP / CCTV source

Any OpenCV-accepted source string works:

```bash
# IP camera
python examples/webcam_triage_demo.py --source "rtsp://user:pass@10.0.0.5:554/stream"

# Recorded video file
python examples/webcam_triage_demo.py --source /path/to/video.mp4

# gstreamer pipeline
python examples/webcam_triage_demo.py --source "v4l2src ! videoconvert ! appsink"
```

## 5. Real YOLO — what changes when ultralytics is installed

Without `ultralytics`, the demo uses `LoopbackYOLODetector` with a
single canned bounding box covering most of the frame. That's fine
for confirming the vitals path works — the ROI just covers more
than a face.

With `ultralytics`:

```bash
pip install ultralytics
python examples/webcam_triage_demo.py
```

The first run downloads `yolov8n.pt` (~6 MB) to your current
directory. Subsequent runs reuse it. The demo then uses the real
YOLO boxes — the ROI shrinks to the actual person, and the HR
estimate sharpens because flicker from walls / lamps outside the
person is no longer averaged in.

## 6. Collecting a small calibration set

One of the original "Alpha → Beta" blockers was CAL-001: thresholds
tuned on 70 synthetic casualties. With a webcam you can collect a
tiny real-data supplement:

```python
from triage4.perception import build_opencv_frame_source

frames = []
with build_opencv_frame_source(0) as src:
    for _ in range(150):
        frame = src.read()
        if frame is None:
            break
        frames.append(frame.copy())

# Persist to disk for later replay in CI.
import numpy as np
np.savez("calibration_run_001.npz", frames=np.stack(frames))
```

Replay from the saved archive:

```python
from triage4.perception import LoopbackFrameSource
import numpy as np

arr = np.load("calibration_run_001.npz")["frames"]
src = LoopbackFrameSource([arr[i] for i in range(arr.shape[0])])
# … feed to the pipeline exactly as the webcam would …
```

Ten short recordings of healthy volunteers (5 s each) already
doubles the effective calibration substrate. Do NOT commit the
recordings to a public repo — they're PHI-adjacent even when the
volunteers are the team. See `docs/REGULATORY.md §8` (HIPAA /
GDPR overlay).

## 7. Acceptance criteria

Stage 2 is considered **done** when:

- [ ] `pip install opencv-python ultralytics` succeeds on the dev
      machine.
- [ ] `python examples/webcam_triage_demo.py` exits 0 and reports
      a plausible HR (55–90 bpm for a resting subject).
- [ ] `python examples/webcam_triage_demo.py --synthetic` exits 0
      and reports HR within ±3 bpm of 72.
- [ ] `tests/test_frame_source.py` passes (21 tests,
      already on main).
- [ ] At least one short (≥ 5 s) real-webcam recording is
      archived locally (not in the repo).

## 8. What is NOT covered by Stage 2

- Platform mobility — the camera is stationary (on a tripod or a
  hand). Use Stage 3 (Tello) for a moving camera.
- Real multi-person detection accuracy evaluation — no ground
  truth, no dataset partnership yet.
- Thermal / IR imaging — current perception is visible-light only.
- Motion blur / low-light / adversarial conditions — all testable
  but not baselined.

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `FrameSourceUnavailable: cv2 ... not installed` | Extra missing | `pip install opencv-python` |
| `FrameSourceUnavailable: could not open source 0` | No camera / no permission / device busy | Check OS camera permission; close other apps using the camera; try source `1` or `2` |
| `FrameSourceUnavailable: no frame within 2s` | Camera warming up too slowly | Pass `--source` explicitly; increase `read_timeout_s` in a custom call |
| HR estimate is exactly 100 bpm or 120 bpm | AC-line flicker from fluorescent lighting (50 Hz × 2 = 100 bpm; 60 Hz × 2 = 120 bpm) | Record outdoors or under DC-driven LED |
| HR confidence < 0.2 | Too few frames, heavy motion, poor lighting | Hold still, face the camera, 150+ frames, good lighting |
| `ultralytics` downloads 120 MB on first use | Non-nano model selected | Default is `yolov8n.pt` (~6 MB); avoid `yolov8l.pt` / `yolov8x.pt` on edge |
| YOLO detects a person on an empty chair | COCO class confusion / background | Raise `confidence_floor` when you construct the detector |

## 10. Next

Once Stage 2 passes locally, proceed to
[`PHASE_10_TELLO.md`](PHASE_10_TELLO.md) — Stage 3.
