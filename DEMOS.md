# DEMOS — running every package's demo + the flagship Web UI

This file is the canonical reference for **what each package's demo
shows**, **how to run it on Linux/macOS and Windows**, and **how to
launch the flagship's Web UI**. It complements:

- [`README.md`](README.md) — monorepo orientation
- [`INSTALL.md`](INSTALL.md) — install + venv + per-package setup
- per-package `README.md` files — domain context

If you are looking for "how do I clone + install", that's in
`INSTALL.md`. This file assumes installation is done.

## Table of contents

- [Overview — who has demos, who has UI](#overview--who-has-demos-who-has-ui)
- [Flagship `triage4` — 11 named demos + benchmark + stress](#flagship-triage4--11-named-demos--benchmark--stress)
- [Sibling demos — 14 packages, uniform shape](#sibling-demos--14-packages-uniform-shape)
- [Portal demo — cross-sibling smoke](#portal-demo--cross-sibling-smoke)
- [Web UI — flagship only](#web-ui--flagship-only)
- [Programmatic API — embed instead of demo](#programmatic-api--embed-instead-of-demo)
- [Benchmark + stress targets](#benchmark--stress-targets)
- [Troubleshooting demos](#troubleshooting-demos)

---

## Overview — who has demos, who has UI

| Package           | Demo command                                      | Web UI               | Special notes |
|-------------------|---------------------------------------------------|----------------------|---|
| **`triage4`** flagship | 11 named demos + benchmark + stress         | **FastAPI + React/Vite** | the only package with a UI |
| `biocore`         | none (utility library — has no domain to demo)    | —                    | use `make qa` to validate |
| `portal`          | `python -m portal.cli demo`                       | —                    | needs pilot siblings installed (fish / bird / wild) |
| `triage4-aqua`    | one-pool lifeguard demo                            | —                    | engine: `PoolWatchEngine` |
| `triage4-bird`    | station-pass avian demo                            | —                    | engine: `AvianHealthEngine` (audio + visual) |
| `triage4-clinic`  | telemedicine pre-screening demo                    | —                    | engine: `ClinicalPreTriageEngine` |
| `triage4-crowd`   | one-venue crowd-safety demo                        | —                    | engine: `VenueMonitorEngine` |
| `triage4-drive`   | one-session driver-monitoring demo                 | —                    | engine: `DriverMonitoringEngine` |
| `triage4-farm`    | one-herd welfare demo                              | —                    | engine: `WelfareCheckEngine` |
| `triage4-fish`    | pen-pass aquaculture demo                          | —                    | engine: `AquacultureHealthEngine` (multi-modal) |
| `triage4-fit`     | one-session coaching demo (inline `python -c`)    | —                    | engine: `RapidFormEngine` |
| `triage4-home`    | one-day in-home monitoring demo                    | —                    | engine: `HomeMonitoringEngine` |
| `triage4-pet`     | pet-video demo (owner + vet output)                | —                    | engine: `PetTriageEngine` |
| `triage4-rescue`  | one-incident mass-casualty demo                    | —                    | engine: `StartProtocolEngine`, plus `multiuser/` package |
| `triage4-site`    | one-shift site-safety demo                         | —                    | engine: `SiteSafetyEngine` |
| `triage4-sport`   | session sport-performance demo                     | —                    | engine: `SportPerformanceEngine` |
| `triage4-wild`    | reserve-pass wildlife demo                         | —                    | engine: `WildlifeHealthEngine` |

### Why only flagship has a Web UI

The 14 siblings are **decision-support libraries**, not services.
Each one's natural surface is:

- a Python API (`<Domain>Engine().review(observation)`)
- a CLI/text demo (the `make demo` target)
- whatever GUI / dashboard the **consuming application** decides to
  build on top — mobile app, web SaaS, embedded device firmware, etc.

Shipping a per-sibling Web UI inside the library would couple the
library to a UI framework choice (React? HTMX? Streamlit?) and would
contradict the per-sibling growth-in-depth policy from
[`DOMAIN_ADAPTATIONS.md`](DOMAIN_ADAPTATIONS.md).

The **flagship** `triage4/` is the exception because it doubles as a
research showcase for DARPA Triage Challenge demos — the FastAPI
dashboard + React UI is part of the demonstration, not part of the
library contract.

### How every demo is invoked (three forms)

**Linux / macOS (with `make`):**
```bash
cd <package>
make demo
```

**Windows PowerShell (no `make`):**
```powershell
cd C:\Users\<you>\info150\<package>
python -m <package_module>.sim.demo_runner
# triage4-fit is the one exception — see its section below.
```

**Cross-platform (works everywhere):**
```bash
cd <package>
python -m <package_module>.sim.demo_runner
```

Throughout this file, `make demo` and the underlying `python -m ...`
form are listed together. Pick whichever matches your shell.

---

## Flagship `triage4` — 11 named demos + benchmark + stress

All flagship demos live in `triage4/examples/`. Each is a self-contained
script — no command-line arguments needed unless noted. Run from inside
`triage4/` after `pip install -e ".[dev]"`.

### `demo-quick` — one-casualty rapid triage

The smallest useful pipeline: take one set of synthetic signatures
(breathing, perfusion, bleeding, thermal), run `RapidTriageEngine`,
print the priority + textual explanation + confidence.

Useful as a **5-second sanity check** that the install is healthy.

| | |
|---|---|
| Script | `triage4/examples/quick_triage.py` |
| Make target | `make demo-quick` |
| Direct command | `python examples/quick_triage.py` |
| Expected runtime | < 1 s |
| External deps | none |

### `demo-twin` — Bayesian patient twin (particle filter)

Shows `PatientTwinFilter` turning **repeated observations** of a single
casualty into a **posterior distribution** over priority bands rather
than a point estimate. Output:

- `P(immediate) / P(delayed) / P(minimal)` per casualty
- effective sample size (ESS) — particle-filter health
- escalation hint when `P(immediate) > 0.8`

Useful for downstream UI (probability bar instead of one label) and
escalation logic.

| | |
|---|---|
| Script | `triage4/examples/bayesian_twin_demo.py` |
| Make target | `make demo-twin` |
| Direct command | `python examples/bayesian_twin_demo.py` |
| Expected runtime | ~ 1 s |
| External deps | none |

### `demo-crdt` — denied-comms CRDT sync (3 medics)

Simulates three medics (A, B, C) working the same incident with **no
working backbone**. Each tablet holds a `CRDTCasualtyGraph` replica;
they sync pairwise whenever two medics are colocated.

The demo prints:
- per-medic graph state at each tick
- pairwise sync events (who synced with whom, what merged)
- final convergence — every replica ends with the same casualty set
  and priorities, regardless of merge order

Useful as a working illustration of conflict-free replicated data
types under battlefield denied-comms conditions.

| | |
|---|---|
| Script | `triage4/examples/crdt_sync_demo.py` |
| Make target | `make demo-crdt` |
| Direct command | `python examples/crdt_sync_demo.py` |
| Expected runtime | ~ 1 s |
| External deps | none |

### `demo-counterfactual` — retrospective counterfactual replay

After a mission, takes the **actual decisions + eventual outcomes** and
asks: *for each casualty, what priority would have maximised the
expected outcome, and how much regret did we accumulate by not choosing
it?*

The demo prints:
- per-casualty actual vs. best-counterfactual priority
- per-casualty regret value
- mean regret across the mission
- count of cases above the regret threshold

Used by medical directors for the morning-after debrief.

| | |
|---|---|
| Script | `triage4/examples/counterfactual_replay.py` |
| Make target | `make demo-counterfactual` |
| Direct command | `python examples/counterfactual_replay.py` |
| Expected runtime | ~ 1 s |
| External deps | none |

### `demo-marker` — steganographic marker handoff

Simulates a **denied-comms battlefield handoff**: medic A assesses a
casualty, encodes the casualty node into an **HMAC-signed steganographic
marker**, "tapes" the QR-safe string to the casualty, and walks away.
Later medic B scans the marker and reconstructs the casualty state
locally — no network needed.

The demo also exercises the **three failure modes** the codec refuses
to accept:
- tampered marker (HMAC mismatch)
- expired marker (TTL exceeded)
- malformed marker (wrong version / corrupted bytes)

| | |
|---|---|
| Script | `triage4/examples/marker_handoff_demo.py` |
| Make target | `make demo-marker` |
| Direct command | `python examples/marker_handoff_demo.py` |
| Expected runtime | < 1 s |
| External deps | none |

### `demo-uav` — UAV waypoint routing

Drives a `LoopbackMAVLinkBridge` to three casualty waypoints in a
deterministic synthetic scenario and prints **step-by-step telemetry**:

- waypoint enter / hover / leave events
- battery + signal estimates per leg
- `BridgeHealth` snapshot at each step

Demonstrates the platform-bridge contract without needing a real UAV.

| | |
|---|---|
| Script | `triage4/examples/uav_waypoint_demo.py` |
| Make target | `make demo-uav` |
| Direct command | `python examples/uav_waypoint_demo.py` |
| Expected runtime | ~ 1 s |
| External deps | none (uses loopback bridge; no real MAVLink stack required) |

### `demo-multi` — multi-platform coordination

Shows `MultiPlatformManager` running **three heterogeneous bridges
behind one surface**: a UAV (MAVLink loopback), a quadruped (Spot
loopback), and a ROS2 companion. The manager:

- broadcasts a new casualty to all three bridges
- targets a mission-graph update at the ROS2 publisher specifically
- aggregates `BridgeHealth` across all three so the operator sees one
  consolidated status

Demonstrates the multi-platform orchestrator without any real
hardware.

| | |
|---|---|
| Script | `triage4/examples/multi_platform_demo.py` |
| Make target | `make demo-multi` |
| Direct command | `python examples/multi_platform_demo.py` |
| Expected runtime | ~ 1 s |
| External deps | none (all three bridges are loopback by default) |

### `demo-calibration` — grid-search calibration walkthrough

End-to-end demonstration of the Phase 9b calibrator:

1. Generate a 70-case realistic dataset (7 scenarios × 10 cases) from
   `sim.realistic_dataset` with sensor degradation applied.
2. Evaluate the **default** engine — establish the baseline score.
3. Run the grid-search calibrator over fusion weights + thresholds.
4. Re-evaluate with the calibrated parameters.
5. Print the before/after macro-F1 and the chosen parameter set.

This is the canonical "how do we tune the engine?" walkthrough — used
when adapting triage4 to a new domain.

| | |
|---|---|
| Script | `triage4/examples/calibration_walkthrough.py` |
| Make target | `make demo-calibration` |
| Direct command | `python examples/calibration_walkthrough.py` |
| Expected runtime | ~ 5–10 s (the grid search does the heavy lifting) |
| External deps | none |

### `demo-replay` — mission timeline replay

Shows the K3-3.3 world-replay path: as a mission unfolds, every scene
transition is appended to a `TimelineStore`; after the mission a
`ReplayEngine` walks the timeline frame-by-frame so an operator (or a
counterfactual scorer) can reconstruct **what was known at each tick**
— not just the final state.

The demo prints:
- timeline tick by tick with priority-revision events
- frame-level diffs between consecutive ticks
- final reconstruction matching the original state

| | |
|---|---|
| Script | `triage4/examples/mission_replay_demo.py` |
| Make target | `make demo-replay` |
| Direct command | `python examples/mission_replay_demo.py` |
| Expected runtime | ~ 1 s |
| External deps | none |

### `demo-webcam` — webcam perception + Eulerian HR

Phase 10 Stage 2 demo. Runs the perception → Eulerian-vitals path
against a real frame source. Tries, in order:

1. A USB webcam via `build_opencv_frame_source(0)` — real camera.
2. A `SyntheticFrameSource` pulsing at a known HR — falls back
   automatically if OpenCV is missing or no webcam is connected.

The Make target uses the synthetic mode by default (so CI runs work):

```
python examples/webcam_triage_demo.py --synthetic --frames 120
```

Drop `--synthetic` to use the real camera.

| | |
|---|---|
| Script | `triage4/examples/webcam_triage_demo.py` |
| Make target | `make demo-webcam` |
| Direct command (synthetic) | `python examples/webcam_triage_demo.py --synthetic --frames 120` |
| Direct command (real) | `python examples/webcam_triage_demo.py --frames 240` |
| Expected runtime | ~ 5 s synthetic; depends on camera in real mode |
| External deps | optional: `opencv-python` for real webcam (`pip install opencv-python`) |

### `demo-tello` — Tello drone 3-waypoint survey

Phase 10 Stage 3 demo. Shows a single Tello-class drone flying a
**three-waypoint search pattern** while triage4 publishes casualty
events and health-gates dispatch. Uses `LoopbackTelloBridge` by
default so the demo runs anywhere (including CI).

With `--real` the demo goes through `build_tello_bridge` to talk to a
real Tello on the local Wi-Fi (drone must be powered on and
discoverable).

| | |
|---|---|
| Script | `triage4/examples/tello_triage_demo.py` |
| Make target | `make demo-tello` |
| Direct command (loopback) | `python examples/tello_triage_demo.py` |
| Direct command (real) | `python examples/tello_triage_demo.py --real` |
| Expected runtime | < 2 s loopback; ~ 30 s on real hardware |
| External deps | optional: `djitellopy` for real drone (`pip install djitellopy`) |

---

## Sibling demos — 14 packages, uniform shape

Every sibling has exactly **one** `make demo` target that runs
`<sibling_module>.sim.demo_runner` (or, for `triage4-fit`, an inline
one-liner). Each demo:

1. Generates **deterministic synthetic input** via the sibling's
   `sim.synthetic_*` module.
2. Feeds the input into the sibling's domain `Engine` class.
3. Prints a **text report** to stdout — alert level + scores + alert
   bodies.

The shape is uniform on purpose; what differs is the **domain** —
what's measured, what bands count as urgent, what the alert text says.

### `triage4-aqua` — pool / beach safety

Lifeguard-team support. Runs `PoolWatchEngine` over a pool of
synthetic swimmers (motion / submersion / distress signatures).

Output sample:

```
Pool DEMO_POOL — running N swimmer observations through PoolWatchEngine.
  swimmer_01  level=watch    overall=0.72  motion=0.85  submersion=0.40 ...
  swimmer_02  level=urgent   overall=0.31  motion=0.10  submersion=0.05 ...
  ...
```

| | |
|---|---|
| Engine | `triage4_aqua.pool_watch.monitoring_engine.PoolWatchEngine` |
| Synthetic input | `triage4_aqua.sim.synthetic_pool.demo_pool()` |
| Make target | `make demo` |
| Direct command | `python -m triage4_aqua.sim.demo_runner` |
| Tests | 119 |

### `triage4-bird` — wildlife avian

Solo-ornithologist station-pass review. Runs `AvianHealthEngine` over
combined **audio + visual** observations of birds at a feeder/station.
Demonstrates the cross-modal corroborative-alert pattern (one combined
"candidate disease pattern" alert when audio + visual both deviate,
instead of two independent alerts).

| | |
|---|---|
| Engine | `triage4_bird.bird_health.monitoring_engine.AvianHealthEngine` |
| Synthetic input | `triage4_bird.sim.synthetic_station.demo_observations()` |
| Make target | `make demo` |
| Direct command | `python -m triage4_bird.sim.demo_runner` |
| Tests | 113 |
| Notes | Depends on `biocore` (tier-1 helpers). |

### `triage4-clinic` — telemedicine pre-screening

Nurse-line / triage-line decision support. Runs
`ClinicalPreTriageEngine` over self-reported submissions (symptom set
+ vitals if present). Output is **strictly framed as decision-support**
— never a diagnosis, never a treatment recommendation. Same regulatory
posture as the flagship.

| | |
|---|---|
| Engine | `triage4_clinic.clinic_triage.triage_engine.ClinicalPreTriageEngine` |
| Synthetic input | `triage4_clinic.sim.synthetic_self_report.demo_submissions()` |
| Make target | `make demo` |
| Direct command | `python -m triage4_clinic.sim.demo_runner` |
| Tests | 105 |

### `triage4-crowd` — crowd / event safety

Event operations centre support. Runs `VenueMonitorEngine` over
zone-by-zone observations of a venue (density / flow / pressure /
chokepoint indicators). Output is per-zone alert level with bridge to
event-coordinator action (NOT to crowd-control commands).

| | |
|---|---|
| Engine | `triage4_crowd.venue_monitor.monitoring_engine.VenueMonitorEngine` |
| Synthetic input | `triage4_crowd.sim.synthetic_venue.demo_venue()` |
| Make target | `make demo` |
| Direct command | `python -m triage4_crowd.sim.demo_runner` |
| Tests | 103 |

### `triage4-drive` — driver monitoring / fleet

Driver-monitoring decision support for fleet operations. Runs
`DriverMonitoringEngine` over observation windows from a synthetic
driving session (drowsiness / distraction / posture indicators).
Output is per-window alert level + suggested rest break — never a
"pull over" command.

| | |
|---|---|
| Engine | `triage4_drive.driver_monitor.monitoring_engine.DriverMonitoringEngine` |
| Synthetic input | `triage4_drive.sim.synthetic_cab.demo_session()` |
| Make target | `make demo` |
| Direct command | `python -m triage4_drive.sim.demo_runner` |
| Tests | 82 |

### `triage4-farm` — livestock / agtech

Farm-manager paddock-scan support. Runs `WelfareCheckEngine` over a
synthetic herd (lameness / body-condition / behavioural signatures).
Output is per-animal welfare score + farm-aggregate, with vet-handoff
framing — never a treatment recommendation.

| | |
|---|---|
| Engine | `triage4_farm.welfare_check.welfare_engine.WelfareCheckEngine` |
| Synthetic input | `triage4_farm.sim.synthetic_herd.demo_herd(n_animals=6, n_lame=2)` |
| Make target | `make demo` |
| Direct command | `python -m triage4_farm.sim.demo_runner` |
| Tests | 64 |

### `triage4-fish` — wildlife aquatic / aquaculture

Aquaculture pen-pass support — the most architecturally interesting
sibling. Runs `AquacultureHealthEngine` over **multi-modal**
observations: visible-light channels (gill rate, school cohesion, sea
lice, mortality floor) **scaled by water-chemistry vision-confidence**
(turbid water → vision channels blend toward neutral).

The demo also exercises the cross-modal corroborative-alert pattern:
when mortality + water-chemistry both fire, you get one combined
"candidate disease pattern" alert instead of two raw alerts.

| | |
|---|---|
| Engine | `triage4_fish.pen_health.monitoring_engine.AquacultureHealthEngine` |
| Synthetic input | `triage4_fish.sim.synthetic_pen.demo_observations()` |
| Make target | `make demo` |
| Direct command | `python -m triage4_fish.sim.demo_runner` |
| Tests | 120 |
| Notes | Depends on `biocore` (tier-1 + tier-2 fusion helpers). |

### `triage4-fit` — fitness / wellness (special: inline demo)

The **only** sibling without a `demo_runner.py` — its `make demo`
target is an inline `python -c "..."` one-liner because the demo is
small enough to fit on one line. Runs `RapidFormEngine` over a
synthetic squat session with controlled asymmetry severity.

```bash
# Make form (Linux/macOS)
make demo

# Direct, cross-platform
python -c "from triage4_fit.sim.synthetic_session import demo_session; from triage4_fit.form_check.rapid_form_engine import RapidFormEngine; sess = demo_session('squat', rep_count=5, asymmetry_severity=0.35); print(RapidFormEngine().review(sess).as_text())"
```

On **Windows PowerShell** the line above works as-is — double quotes
inside the single-quoted Python expression resolve correctly.

| | |
|---|---|
| Engine | `triage4_fit.form_check.rapid_form_engine.RapidFormEngine` |
| Synthetic input | `triage4_fit.sim.synthetic_session.demo_session('squat', rep_count=5, asymmetry_severity=0.35)` |
| Make target | `make demo` |
| Tests | 50 |

### `triage4-home` — elderly home care

Multi-day in-home monitoring support. Runs `HomeMonitoringEngine` over
a **day-series** of windowed observations against a per-resident
**baseline**. The baseline-aware design lets the engine flag
*deviations from this resident's normal*, not just absolute thresholds
— important because elderly-care signals are highly individual.

| | |
|---|---|
| Engine | `triage4_home.home_monitor.monitoring_engine.HomeMonitoringEngine` |
| Synthetic input | `triage4_home.sim.synthetic_day.demo_day_series()` + `demo_baseline()` |
| Make target | `make demo` |
| Direct command | `python -m triage4_home.sim.demo_runner` |
| Tests | 92 |

### `triage4-pet` — veterinary

Owner-submitted pet-video triage. Runs `PetTriageEngine` over
synthetic submissions (pet token + species + age + symptom
observations). Output is **dual-audience**: a friendly recommendation
for the **owner** (stay home / call clinic / see vet) plus a clinical
summary for the **vet**. Demonstrates the audience-routing pattern.

| | |
|---|---|
| Engine | `triage4_pet.pet_triage.triage_engine.PetTriageEngine` |
| Synthetic input | `triage4_pet.sim.synthetic_submission.demo_submissions()` |
| Make target | `make demo` |
| Direct command | `python -m triage4_pet.sim.demo_runner` |
| Tests | 120 |

### `triage4-rescue` — disaster response (+ multiuser pilot)

Civilian mass-casualty triage support — **the v13 multiuser pilot
sibling**. Runs `StartProtocolEngine` over a synthetic incident with
11 casualties (mix of adult / pediatric, ambulatory / non-ambulatory).
The demo prints START / JumpSTART tags + reasoning per casualty.

The sibling **also** ships the `triage4_rescue.multiuser` subpackage
(sessions / RBAC / audit log / async jobs). The demo runner only
exercises the triage path — multiuser is a library API, not a
script. To play with the multiuser API see the
[Programmatic API section below](#programmatic-api--embed-instead-of-demo).

| | |
|---|---|
| Engine | `triage4_rescue.triage_protocol.protocol_engine.StartProtocolEngine` |
| Synthetic input | `triage4_rescue.sim.synthetic_incident.demo_incident()` |
| Make target | `make demo` |
| Direct command | `python -m triage4_rescue.sim.demo_runner` |
| Tests | 134 (62 core + 72 multiuser pilot) |

Sample output:

```
Incident: DEMO_INCIDENT · 11 casualties tagged
  immediate: 3   delayed: 2   minor: 5   deceased: 1
  1 casualty flagged for secondary review
  DEMO_INCIDENT-001  tag=minor      age_group=adult
    reasoning: ambulatory → START minor
  DEMO_INCIDENT-008  tag=immediate  age_group=adult
    reasoning: respiratory rate abnormal (42 /min) → START immediate
  DEMO_INCIDENT-011  tag=deceased   age_group=adult       [flag]
    reasoning: apneic after airway reposition → START deceased
```

### `triage4-site` — industrial safety

Safety-officer one-shift review. Runs `SiteSafetyEngine` over per-worker
observations (PPE compliance / lifting safety / heat-stress markers).
Output is per-worker alert level + per-channel scores; alert text is
operationally framed (officer briefing language) rather than
labour-relations framing.

| | |
|---|---|
| Engine | `triage4_site.site_monitor.monitoring_engine.SiteSafetyEngine` |
| Synthetic input | `triage4_site.sim.synthetic_shift.demo_shift()` |
| Make target | `make demo` |
| Direct command | `python -m triage4_site.sim.demo_runner` |
| Tests | 102 |

### `triage4-sport` — sports performance

Coach-side athlete-session review. Runs `SportPerformanceEngine` over
synthetic athlete sessions **against a per-athlete baseline** (similar
shape to `triage4-home`). Output is per-session performance score with
context — never a "increase load by X%" prescription.

| | |
|---|---|
| Engine | `triage4_sport.sport_engine.monitoring_engine.SportPerformanceEngine` |
| Synthetic input | `triage4_sport.sim.synthetic_session.demo_sessions()` + `demo_baseline()` |
| Make target | `make demo` |
| Direct command | `python -m triage4_sport.sim.demo_runner` |
| Tests | 149 |

### `triage4-wild` — wildlife terrestrial

Solo ranger reserve-pass review. Runs `WildlifeHealthEngine` over a
sequence of observations from a single pass through a reserve.
Aggregates everything into a `ReserveReport`. Designed for
**satcom-bandwidth-constrained** deployments — the SMS-style alert
text is capped at `MAX_RANGER_SMS_CHARS`.

| | |
|---|---|
| Engine | `triage4_wild.wildlife_health.monitoring_engine.WildlifeHealthEngine` |
| Synthetic input | `triage4_wild.sim.synthetic_reserve.demo_observations()` |
| Make target | `make demo` |
| Direct command | `python -m triage4_wild.sim.demo_runner` |
| Tests | 114 |
| Notes | Depends on `biocore` (tier-1 helpers). |

---

## Portal demo — cross-sibling smoke

The `portal/` package's demo is **structurally different** from sibling
demos. It does not run a single engine — it runs several **pilot
siblings** end-to-end, collects their `Report` outputs through
`portal_adapter.py` files, and then prints the **typed bridges** the
portal discovers across them.

### Prerequisites

The portal demo requires the three pilot siblings + biocore to be
installed in the same venv:

```bash
pip install -e biocore/
pip install -e triage4-fish/ triage4-bird/ triage4-wild/
pip install -e portal/
```

### Run

```bash
cd portal
make demo
# or, cross-platform:
python -m portal.cli demo
```

### What it shows

- per-sibling synthetic data → `Report` → `PortalEntry` adapter →
  list of typed entries
- bridge-discovery rules running over the entries:
  - `co_occurrence` — two entries with same urgency in overlapping
    time window
  - `domain_neighbor` — entries whose 6-bit domain coordinates are
    Hamming-1 apart
  - `escalation` — pairs where entry-B reads as a follow-up to entry-A
  - `analogy` — same alert kind firing in two siblings simultaneously
- count of bridges per kind + a printed sample of each

### What it does NOT do

- Does not modify any sibling's state.
- Does not import any sibling's internals — only the published
  `Report` / `Alert` types via the adapter.
- Does not require all siblings — only the three pilots ship adapters
  today. Others join voluntarily by adding their own
  `portal_adapter.py`.

| | |
|---|---|
| Entry point | `portal.cli:main` (subcommand `demo`) |
| Make target | `make demo` |
| Direct command | `python -m portal.cli demo` |
| Tests | 75 |

---

## Web UI — flagship only

The flagship `triage4/` ships **two** Web UI surfaces:

1. **FastAPI dashboard** (`triage4.ui.dashboard_api`) — the data
   plane. JSON over HTTP. Used by the React UI and by any other
   dashboard / mobile-app / CI tool that wants to read state.
2. **React + Vite UI** (`triage4/web_ui/`) — the presentation plane.
   Talks to the FastAPI dashboard.

Each can run independently. You usually run both in parallel — one
terminal each.

### FastAPI dashboard

```bash
cd triage4
uvicorn triage4.ui.dashboard_api:app --reload
```

Then in another terminal (or browser):

```bash
# Linux / macOS
curl http://localhost:8000/health
# Windows PowerShell
Invoke-WebRequest http://localhost:8000/health
```

Endpoints (all GET unless noted):

| Endpoint                          | What it returns                                        |
|-----------------------------------|--------------------------------------------------------|
| `/health`                         | service status + node count in the casualty graph      |
| `/casualties`                     | full list of casualties                                |
| `/casualties/{id}`                | single casualty card                                   |
| `/casualties/{id}/explain`        | triage decision with three-layer explanation (signals → reasoning → priority) |
| `/casualties/{id}/handoff`        | medic handoff payload                                  |
| `/graph`                          | full `CasualtyGraph` as JSON                           |
| `/map`                            | tactical-scene map projection                          |
| `/replay`                         | replay-timeline frames                                 |
| `/tasks`                          | recommended intervention queue                         |
| `/export.html`                    | self-contained HTML snapshot — works fully offline     |
| `/metrics`                        | Prometheus metrics (Phase 13-prep)                     |

### React + Vite UI

```bash
cd triage4/web_ui
npm install     # first time only
npm run dev     # http://localhost:5173
```

Production build:

```bash
npm run build      # output: web_ui/dist/
npm run preview    # serves dist/ on a local port — sanity check
```

The UI talks to the FastAPI dashboard at `http://localhost:8000` by
default. To point at a different backend, set `VITE_API_URL` in the
shell before `npm run dev` (Vite picks it up automatically).

### Both at once — recommended dev flow

Run each in its own terminal:

**Terminal 1** (FastAPI):
```bash
cd info150/triage4
uvicorn triage4.ui.dashboard_api:app --reload
```

**Terminal 2** (React):
```bash
cd info150/triage4/web_ui
npm run dev
```

Then browse `http://localhost:5173`. The UI hot-reloads on any React
change; the API hot-reloads on any Python change.

### Docker alternative

If you don't want Python or Node on the host:

```bash
cd info150/triage4
make docker-compose-up
# Visit http://localhost:8000/export.html for a static HTML snapshot.
make docker-compose-down
```

The Docker image ships **API only** — the React UI is a build-step
away and is meant to be served by whatever production proxy the
deployment uses (the `edge` profile in `docker-compose.yml` has nginx
for that).

---

## Programmatic API — embed instead of demo

Each sibling's demo is just a thin wrapper around the engine. To embed
the engine in your own application, the pattern is uniform:

1. Construct synthetic or real input via the sibling's data classes.
2. Construct the engine with optional weight overrides.
3. Call `engine.review(observation)` (or sibling-specific verb).
4. Inspect `report.scores` / `report.alerts` / `report.as_text()`.

Below — one short snippet per sibling. All snippets assume you are
inside the activated venv with the relevant package installed.

### `triage4-fish` (multi-modal pen review)

```python
from triage4_fish.sim.synthetic_pen import demo_observations
from triage4_fish.pen_health.monitoring_engine import AquacultureHealthEngine

engine = AquacultureHealthEngine()
report = engine.review(demo_observations()[0])
print(report.scores[0])
for alert in report.alerts:
    print(alert.level, alert.kind, alert.text)
```

### `triage4-rescue` (START / JumpSTART triage)

```python
from triage4_rescue.sim.synthetic_incident import demo_incident
from triage4_rescue.triage_protocol.protocol_engine import StartProtocolEngine

engine = StartProtocolEngine()
report = engine.review(demo_incident())
for tag in report.tags:
    print(tag.casualty_id, tag.start_tag, tag.reasoning)
```

### `triage4-rescue` multiuser (sessions / RBAC / audit)

```python
from triage4_rescue.multiuser import (
    SessionManager, PolicyEngine, AuditLog, AsyncJobQueue,
)

sm = SessionManager()
sm.create_user("alice", role="dispatcher")
sess = sm.create_session("alice")

pe = PolicyEngine()
pe.require(sess.role, "incident:log")        # passes
try:
    pe.require(sess.role, "users:mutate")    # raises PermissionError
except PermissionError as e:
    print("denied:", e)

log = AuditLog()                              # in-memory
# log = AuditLog(db_path="./audit.sqlite")    # SQLite-backed (opt-in)
log.append("incident:log", actor_user_id="alice", actor_role="dispatcher",
           target_id="INC-1", payload={"summary": "structure fire"})
print(log.list())
```

### `triage4-bird` (audio + visual avian station)

```python
from triage4_bird.sim.synthetic_station import demo_observations
from triage4_bird.bird_health.monitoring_engine import AvianHealthEngine

for obs in demo_observations():
    print(AvianHealthEngine().review(obs).as_text())
```

### `triage4-home` (baseline-aware day-series)

```python
from triage4_home.sim.synthetic_day import demo_baseline, demo_day_series
from triage4_home.home_monitor.monitoring_engine import HomeMonitoringEngine

engine = HomeMonitoringEngine()
baseline = demo_baseline()
for window in demo_day_series():
    report = engine.review(window, baseline=baseline)
    print(report.as_text())
```

### `triage4-fit` (squat asymmetry)

```python
from triage4_fit.sim.synthetic_session import demo_session
from triage4_fit.form_check.rapid_form_engine import RapidFormEngine

session = demo_session("squat", rep_count=5, asymmetry_severity=0.35)
print(RapidFormEngine().review(session).as_text())
```

### Custom weights for any engine

Every domain engine accepts an optional `weights` dict that is fused
through `biocore.fusion.normalise_weights`. Example for fish:

```python
from triage4_fish.pen_health.monitoring_engine import AquacultureHealthEngine

engine = AquacultureHealthEngine(weights={
    "gill_rate":        0.10,
    "school_cohesion":  0.20,
    "sea_lice":         0.10,
    "mortality_floor":  0.30,   # weight mortality higher
    "water_chemistry":  0.30,
})
```

Pass any partial set; the helper raises on negative totals and
re-scales positive totals to sum to 1.0.

### Flagship `triage4` programmatic entry

The flagship is large — start from `triage4.sim.synthetic_benchmark`:

```python
from triage4.sim.synthetic_benchmark import full_pipeline_run

result = full_pipeline_run(num_casualties=8)
print(result.gate1_score, result.gate2_score, result.hmt_lane)
```

For lower-level access (signatures, perception, graphs) read
`triage4/docs/API.md`.

---

## Benchmark + stress targets

Beyond the 11 demos, the flagship has four heavier targets used for
performance regression tracking.

### `make benchmark` — full DARPA pipeline

8-casualty end-to-end run through perception → signatures → triage →
graph → autonomy → bridge → evaluation through 5 DARPA gates. Same
script as the green-light test in `INSTALL.md`.

```bash
cd triage4
make benchmark
# or
python examples/full_pipeline_benchmark.py
```

Expected runtime: ~ 1 s. Output includes Gate 1–4 metrics, HMT lane,
Bayesian patient twins, counterfactual regret, top-3 grounded
explanations.

### `make benchmark-json` — same, JSON scorecard

```bash
make benchmark-json
# or
python examples/full_pipeline_benchmark.py --json benchmark.json
```

Writes `benchmark.json` next to the script. Useful in CI for tracking
metric drift across commits.

### `make stress` — scaling benchmark (10 / 100 / 500)

```bash
make stress
# or
python examples/stress_benchmark.py
```

Runs the pipeline at three sizes (10, 100, 500 casualties) and prints
wall-clock, peak memory, throughput. Default sizes; ~ 5 s total.

### `make stress-big` — heavier sizes (100 / 1000 / 5000)

```bash
make stress-big
# or
python examples/stress_benchmark.py --sizes 100 1000 5000
```

Same script with bigger sizes — ~ 30 s, useful for regression runs
before a release tag.

---

## Troubleshooting demos

### `ModuleNotFoundError: No module named 'triage4_<sibling>'`

You haven't installed the sibling. Activate venv, then:

```bash
cd info150/<sibling>
pip install -e ".[dev]"
```

### `ModuleNotFoundError: No module named 'biocore'` from a sibling demo

Three siblings (`triage4-wild`, `triage4-bird`, `triage4-fish`) depend
on `biocore`. Install it first:

```bash
pip install -e info150/biocore/
```

### `python -m portal.cli demo` complains a sibling adapter is missing

Only three siblings have adapters today. Install them:

```bash
pip install -e info150/biocore/
pip install -e info150/triage4-fish/ info150/triage4-bird/ info150/triage4-wild/
pip install -e info150/portal/
```

### `uvicorn triage4.ui.dashboard_api:app` — `ModuleNotFoundError: triage4.ui`

You're running `uvicorn` from the wrong directory or you haven't
`pip install -e .` for the flagship. Recover:

```bash
cd info150/triage4
pip install -e ".[dev]"
uvicorn triage4.ui.dashboard_api:app --reload
```

### `npm install` fails in `web_ui/`

You need Node.js 18+. Verify with `node --version`. If older, install
a recent Node — for example via [nvm](https://github.com/nvm-sh/nvm)
on Linux/macOS or `winget install OpenJS.NodeJS.LTS` on Windows.

### Webcam demo can't open the camera

The demo falls back to synthetic mode automatically. If you want the
real-camera path, install OpenCV:

```bash
pip install opencv-python
python examples/webcam_triage_demo.py --frames 240
```

### Tello demo says "no drone found"

You ran the `--real` mode without a drone on the same Wi-Fi. Drop
`--real` to use the loopback bridge:

```bash
python examples/tello_triage_demo.py
```

Or connect to the Tello's Wi-Fi SSID first, then re-run with `--real`.

### Make target works on Linux/macOS but not on Windows

`make` is not installed on Windows by default. Two options:

- Install GNU make: `winget install GnuWin32.Make` or `choco install make`.
- Skip make and run the underlying `python -m ...` command — every
  demo target in this file lists both forms.

See [`INSTALL.md` → Windows / PowerShell section](INSTALL.md#windows--powershell-without-make)
for the full Windows recovery guide.

