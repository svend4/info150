# 04 — Fitness / wellness

Gym / home-workout form check, recovery tracking, post-exercise
breathing + HR monitoring. **Strictly wellness, not clinical.**

## 1. Use case

Webcam or phone camera watches a user doing squats / push-ups /
deadlifts. The system scores form quality (symmetry, joint
angles, depth), estimates HR via Eulerian remote vitals,
measures recovery from post-set breathing recovery, and
suggests "continue", "reduce intensity", "rest", or "form
correction" as coach-facing prompts. **Not** a substitute for
a trainer or a physician.

## 2. Who pays

- Gym chains (Planet Fitness, Equinox, Virgin Active).
- Home fitness platforms (Peloton, Tonal, Mirror).
- Corporate wellness programmes (Gympass, ClassPass B2B).
- Fitness app consumers directly (B2C subscription).

Revenue model: B2B SaaS licence per location, or B2C
subscription $10-20/mo.

## 3. What transfers from triage4

**~65 % reuse — highest among practical sub-projects.**

- `FrameSource` — webcam / phone (via WebRTC or local browser
  access).
- `signatures/posture_signature.py` — instability, asymmetry
  during exercise. Core of form-check.
- `signatures/breathing_signature.py` — post-set recovery rate,
  strong fatigue proxy.
- `signatures/remote_vitals.py` — resting HR + recovery HR
  via Eulerian.
- `state_graph/skeletal_graph.py` — 13-joint humanoid
  (unchanged topology), now focused on motion symmetry.
- `triage_reasoning/uncertainty.py` — per-channel quality.
- `triage_reasoning/celegans_net.py` — pattern reused: a
  small hand-wired "form-quality" classifier with 6 sensory
  inputs and 3 motor outputs (continue / reduce / rest).
- `triage_reasoning/llm_grounding.py` — grounded coach prompt
  builder. Rebrands from "medic-facing" to "coach-facing".
- `world_replay/*` — replay a workout.
- Dev infrastructure.

## 4. What has to be built

- **Real-time pose estimation** — `build_ultralytics_detector`
  is per-frame; fitness needs ≥ 25 fps with tight latency
  (MediaPipe or MoveNet, on-device).
- **Exercise classifier** — which rep of which lift is happening
  (CNN or rule-based from keypoint sequence).
- **Rep counter + form-score-per-rep** aggregation.
- **Coach-facing UI** — completely different from operator
  dashboard; has to be mobile-first.
- **Wellness-framing language pass** — every forbidden-word
  rule in `claims-lint.py` must be re-authored: replace
  "casualty" / "priority" / "medic" / "handoff" with
  "trainee" / "intensity" / "coach" / "cue". No medical
  claims at all.

## 5. Regulatory complexity

**Low.** General wellness is regulated by FTC (US) and
consumer-protection bodies (EU), not FDA / CE / MDR. Explicit
disclaimer required: "not medical, consult a doctor before
starting exercise". No PHI handling per se, but camera-in-bedroom
raises standard privacy concerns — GDPR applies for EU
consumers.

## 6. Data availability

**High.** Public exercise video datasets (UCF-101, NTU RGB+D,
InfantMovement, Fit3D). Gym partnerships easy because
volunteers are plentiful and anonymisable. Self-recorded
founders-using-it flywheel gets a calibration set in weeks.

## 7. Commercial viability

**High.** Fitness app market is $15 B/y and growing. Three
large competitors use pose AI (Mirror, Tonal, Freeletics Coach),
but their decision surface is opaque — triage4-style grounded
explanations are a genuine differentiator ("your left hip
dropped 4 cm during the second rep — this is why the cue
fired").

## 8. Engineer-weeks estimate

**6-10 weeks to MVP** — shortest among candidates:

- Weeks 1-2: copy-fork triage4, strip medical framing, wire
  MediaPipe for real-time pose.
- Weeks 3-5: exercise classifier + rep counter for 5 core
  lifts (squat, bench, deadlift, overhead press, row).
- Weeks 6-8: coach-facing mobile UI with cue feed, post-
  workout summary.
- Weeks 9-10: one gym pilot + calibration against instructor
  labels.

## 9. Risk flags

- **Injury liability.** If the "cue engine" tells a user to
  continue and they tear something, liability follows.
  Disclaimers + user-consent flow are not optional.
- **Claims slippage.** Nothing the system says can be
  "diagnosing" a problem — only cuing. Language audit in CI
  is mandatory.
- **Sensor contamination.** Home cameras pick up roommates,
  kids, pets. On-device processing + no-upload default is
  important for adoption.
- **Pose-estimator dependency.** MediaPipe / MoveNet accuracy
  degrades in low light or unusual angles. The uncertainty
  model must surface "low pose confidence — skipping cue"
  rather than over-cuing.
