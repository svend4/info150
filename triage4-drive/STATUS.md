# triage4-drive — status

Honest accounting. Marketing language stays out of this file.

## Built

- Package scaffold (`pyproject.toml`, `Makefile`, `.gitignore`).
- `docs/PHILOSOPHY.md` — the triple-boundary posture
  (clinical + operational + privacy) and the
  forbidden-vocabulary lists.
- `triage4_drive.core`:
  - `enums`: `AlertLevel` (ok / caution / critical),
    `AlertKind` (drowsiness / distraction /
    incapacitation / calibration), `GazeRegion` (road /
    mirror / dashboard / off_road).
  - `models`: `EyeStateSample`, `GazeSample`, `PostureSample`,
    `CanBusSample`, `DriverObservation`, `FatigueScore`,
    `DispatcherAlert` (with triple claims guard),
    `DrivingSession`.
- `triage4_drive.signatures`:
  - `eye_closure` — PERCLOS over a rolling window + microsleep
    flag.
  - `gaze_deviation` — fraction of time gaze leaves the road
    region beyond the grace window.
  - `postural_tone` — head-drop / slump detection from paired
    shoulder / nose keypoints.
- `triage4_drive.driver_monitor`:
  - `fatigue_bands` — NHTSA / SAE J2944 PERCLOS cut-offs
    wrapped in a tunable dataclass.
  - `monitoring_engine.DriverMonitoringEngine.review(driver,
    observation)` → `FatigueScore` + `list[DispatcherAlert]`.
- `triage4_drive.sim`:
  - `synthetic_cab` — deterministic synthetic observation
    generator tunable across drowsiness / distraction /
    incapacitation axes.
  - `demo_runner` — entry point for `make demo`.
- `tests/` — tests across models, signatures, and engine.

## Not built

- **Face Mesh + gaze tracker integration.** MediaPipe Face
  Mesh is the production upstream; this library consumes
  already-extracted landmarks. Integration lives in the
  consumer application.
- **CAN-bus correlation.** A `CanBusSample` slot exists on
  `DriverObservation` so consumers can pass speed / steering
  / lane-departure signals; the engine does NOT yet use
  them for cross-correlation. Reserved for a future
  calibration pass once real fleet data lands.
- **Per-driver long-term baseline.** The library learns a
  per-session baseline (~5 observations) only. Fleet-wide
  baselines need a retention-policy-aware store and
  GDPR / BIPA review — out of MVP scope.
- **Dispatcher dashboard.** The library produces
  `DispatcherAlert` records; the UI that surfaces them
  lives in the consumer app.
- **112 / 911 escalation flow.** The engine never triggers
  emergency services directly — doing so requires
  conservative validation and dispatcher-in-the-loop
  confirmation, out of MVP scope and called out as a risk
  in the parent adaptation file.
- **Validation against real fleet data.** Thresholds
  (PERCLOS 0.15 caution / 0.30 critical, distraction
  0.3 / 0.5) are taken from NHTSA / Wierwille 1994 PERCLOS
  literature and DROZY / DMD dataset conventions. Treat
  them as protocol-authentic, not field-calibrated.

## Scope boundary (repeated for emphasis)

- **Clinical:** never diagnoses drowsiness disorders,
  strokes, arrhythmias, intoxication.
- **Operational:** never commands vehicle control. Alert
  surface stops at "inform driver / dispatcher".
- **Privacy:** never stores biometric templates or
  re-identifiable driver data. Claims guard rejects alert
  text that identifies the driver.

If a future version produces vehicle-control commands,
stores facial embeddings for re-identification, or emits
clinical diagnoses, that work belongs in a separate
regulated codebase with UN-ECE / BIPA / IEC-62304 review.
