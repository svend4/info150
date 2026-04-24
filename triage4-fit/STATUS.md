# triage4-fit — status

Honest state-of-the-prototype note. Read before assuming any
capability ships today.

## What is built

- `core/models.py` — 5 dataclasses: `ExerciseSession`,
  `RepObservation`, `JointPoseSample`, `FormScore`, `CoachCue`.
- `core/enums.py` — `ExerciseKind` (squat / pushup / deadlift),
  `CueSeverity` (ok / minor / severe), `CueKind`
  (asymmetry / depth / tempo / breathing).
- `signatures/pose_symmetry.py` — left-right symmetry score over
  a rep given paired joint samples.
- `signatures/breathing_recovery.py` — post-set HR /
  breathing-rate recovery quality estimate.
- `form_check/exercise_profiles.py` — per-exercise rule sets
  (squat depth threshold, pushup elbow angle, deadlift hip
  hinge angle).
- `form_check/rapid_form_engine.py` — review a whole session,
  return a `CoachBriefing` with per-rep scores + session cues.
- `sim/synthetic_session.py` — generate a reproducible session
  of N reps with a configurable asymmetry-severity dial. Used
  by tests + the `make demo` target.
- `tests/test_*.py` — ~15 tests across symmetry, engine,
  profiles, synthetic data.
- `pyproject.toml`, `Makefile`, `README.md`,
  `docs/PHILOSOPHY.md`.

## What is NOT built

- **No real pose-estimator integration.** `JointPoseSample`
  assumes someone upstream produced (x, y) keypoints — the
  "someone" is a future `perception/` module with MediaPipe /
  MoveNet + webcam. The MVP tests run on purely synthetic
  keypoints.
- **No UI / API.** No FastAPI backend, no dashboard. The
  package is a library; a coach-facing UI is a future
  companion project.
- **No calibration against real athletes.** Thresholds in
  `exercise_profiles.py` are drawn from published squat-depth /
  pushup-form literature but have not been validated against
  actual video.
- **No recovery-time prediction.** `breathing_recovery.py`
  computes a single "recovery quality" score; it does not
  forecast "rest N more seconds". Forecast layer is a future
  add.
- **No persistent history.** Sessions are processed in-memory.
  A trainee-level time series would need a separate storage
  layer.
- **No wearable integration.** HR / breathing rate can come from
  a Polar / Whoop / Apple Watch stream in theory — not wired
  yet.
- **No regulatory documentation.** On purpose (wellness
  framing). If this ever moves clinical, the
  `REGULATORY.md` / `SAFETY_CASE.md` / `RISK_REGISTER.md` trio
  from triage4 is the template.

## Scope boundary — explicit

triage4-fit **is**:
- a library that observes already-extracted keypoints + vitals
  and produces coaching cues.

triage4-fit **is not**:
- a medical device.
- a replacement for a certified personal trainer or physician.
- a tool that should be relied upon for injury prevention
  decisions.

These are not legal-boilerplate caveats — they are product
boundaries that shape the API. `CoachCue.text` never contains
"you are injured" or "stop exercising"; it contains "consider
reducing asymmetry" or "form broke on rep 4 — consider a
rest set".

## Known limits

- Symmetry score assumes bilateral exercises (both sides doing
  similar work). Unilateral exercises (lunges, single-arm
  press) need a different engine.
- Asymmetry thresholds are empirical stubs. Per-trainee
  baseline is a future feature.
- Tempo detection is crude (duration between top + bottom of
  rep); a proper eccentric / concentric split needs phase
  tracking.
- Depth detection is 2D only — side-on camera is assumed.
  Front-on video misses squat depth cues.

## Next natural extensions

Roughly ordered by value:

1. Real webcam → MediaPipe/MoveNet pose pipeline.
2. Per-trainee baseline learner — each person's "normal"
   asymmetry profile.
3. Coach-facing mobile UI (separate project; don't bolt on
   FastAPI here).
4. Wearable HR / breathing ingest.
5. Unilateral exercise engine.
6. Injury-precursor detection (careful — this edges toward
   clinical).
