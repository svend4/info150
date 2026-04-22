# triage4 — Risk register

Structured hazard tracker for the **triage4** stack, inspired by
ISO 14971 risk-management for medical devices. Pre-clinical; entries
are software- and process-level, not clinical.

Every entry carries:
- **ID** — stable short code for cross-reference
- **Hazard** — what can go wrong
- **Cause** — most plausible source
- **Effect** — what the operator / patient would see
- **Sev (1–5)** — severity if unmitigated
- **Lik (1–5)** — likelihood if unmitigated
- **Risk** — Sev × Lik (pre-mitigation)
- **Mitigation** — what triage4 already does
- **Residual** — Sev × Lik after mitigation
- **Owner** — who tracks it

Severity scale: 1 cosmetic · 2 minor · 3 operator-inconvenience ·
4 wrong-priority for one casualty · 5 systemic wrong-priority or
critical miss.

Likelihood: 1 improbable · 2 remote · 3 occasional · 4 probable ·
5 frequent.

Acceptable residual risk: **≤ 6** for clinical decision-support.

---

## Category: Calibration / accuracy

| ID | Hazard | Sev | Lik | Risk | Mitigation | Residual |
|---|---|---|---|---|---|---|
| CAL-001 | Thresholds calibrated on 70-case synthetic set; real distribution may differ | 5 | 3 | 15 | Mortal-sign override + `LarreyBaselineTriage` cross-check + `PatientTwinFilter` posterior + Phase 11 clinical calibration planned | 5×1=5 |
| CAL-002 | Drift in trained YOLO detector after deployment | 4 | 3 | 12 | `LoopbackYOLODetector` default; any real detector is optional; future PCCP (FDA) declaration | 4×2=8 (gate) |
| CAL-003 | Acoustic channel bandpowers assume quiet background | 3 | 4 | 12 | `acoustic_signature.min_fs_hz` enforced ≥ 8 kHz; operator sees low-confidence flag on noisy input | 3×2=6 |
| CAL-004 | Eulerian bandpass HR mistimes at > 2.5 Hz motion | 3 | 3 | 9 | Confidence flag from `remote_vitals` + contact-HR fallback via `VitalsEstimator` | 3×1=3 |

**Owner:** triage_reasoning maintainer.

## Category: Safety-critical classification

| ID | Hazard | Sev | Lik | Risk | Mitigation | Residual |
|---|---|---|---|---|---|---|
| SAFE-001 | Critical casualty classified as delayed (Larrey-gap regression) | 5 | 2 | 10 | `MortalThresholds` override + `test_larrey_vs_rapid_triage_critical_gap_closed` regression lock + visible "mortal-sign override" reason | 5×1=5 |
| SAFE-002 | C.elegans network disagrees silently with fusion engine | 3 | 3 | 9 | Both classifiers are deterministic; future UI surface can flag disagreement to operator | 3×2=6 |
| SAFE-003 | Mission layer escalates too late | 4 | 2 | 8 | `DEFAULT_MISSION_WEIGHTS` weighted toward immediate_fraction (0.35) and medic_utilisation (0.15); reasons always surfaced | 4×1=4 |
| SAFE-004 | Confidence inflation under sensor degradation | 4 | 3 | 12 | `UncertaintyModel` propagates raw-feature quality; `SensorDegradationSimulator` in CI verifies it | 4×1=4 |

**Owner:** triage_reasoning maintainer.

## Category: Operator-in-the-loop

| ID | Hazard | Sev | Lik | Risk | Mitigation | Residual |
|---|---|---|---|---|---|---|
| HMT-001 | Operator overrides mortal-sign escalation by accident | 4 | 3 | 12 | `hmt_lane` tracks override rate + timeliness; UI should require explicit confirmation (future) | 4×2=8 (gate) |
| HMT-002 | Handoff triggered too early, swamping medic | 3 | 3 | 9 | `entropy_handoff` requires Shannon-entropy plateau, not just a timer | 3×1=3 |
| HMT-003 | Handoff triggered too late, patient deteriorates | 5 | 2 | 10 | Entropy threshold is conservative; mortal-sign override bypasses entropy path | 5×1=5 |
| HMT-004 | Operator cannot read explanation under stress | 3 | 4 | 12 | `ExplainabilityBuilder` produces one-line summary + priority in large font (UI policy) | 3×2=6 |

**Owner:** autonomy + UI maintainer.

## Category: Data integrity

| ID | Hazard | Sev | Lik | Risk | Mitigation | Residual |
|---|---|---|---|---|---|---|
| DATA-001 | Tampered offline marker spoofs priority | 5 | 2 | 10 | `marker_codec` HMAC-SHA256; four rejection tests in `test_phase9e.py` | 5×1=5 |
| DATA-002 | Replay of old marker after patient status changed | 4 | 3 | 12 | Default 24 h max_age in `decode_marker`; configurable | 4×2=8 (gate) |
| DATA-003 | CRDT merge drops observations due to race | 3 | 2 | 6 | OR-set + LWW-register proved commutative + property-tested | 3×1=3 |
| DATA-004 | PhysioNet record loaded with wrong units | 4 | 3 | 12 | `PhysioNetRecord.load_dict` schema validation + unit assertion | 4×1=4 |
| DATA-005 | PHI accidentally committed to repo | 5 | 2 | 10 | No real data in repo; synthetic generators only; CI leak-check | 5×1=5 |

**Owner:** integrations maintainer.

## Category: Platform bridges / deployment

| ID | Hazard | Sev | Lik | Risk | Mitigation | Residual |
|---|---|---|---|---|---|---|
| BRIDGE-001 | Real ROS2 / MAVLink SDK imported at load time by accident | 3 | 3 | 9 | `build_*_bridge` factories are lazy; end-to-end test asserts no external SDK in sys.modules after import | 3×1=3 |
| BRIDGE-002 | Loopback bridge masks real-backend wiring bug | 4 | 3 | 12 | Contract tests (future Phase 10) will run `Loopback == real` bridge equivalence | 4×2=8 (gate) |
| BRIDGE-003 | MAVLink coordinate frame confusion | 4 | 3 | 12 | `GeoPose.frame` field always carries frame string; bridge implementations must document conversions | 4×2=8 (gate) |
| BRIDGE-004 | Connection loss causes telemetry backlog | 3 | 4 | 12 | `LoopbackROS2Bridge` bounds deque size; real bridges should mirror | 3×2=6 |

**Owner:** integrations maintainer.

## Category: Cybersecurity

| ID | Hazard | Sev | Lik | Risk | Mitigation | Residual |
|---|---|---|---|---|---|---|
| SEC-001 | Weak secret used with `marker_codec` | 5 | 3 | 15 | `encode_marker` rejects secrets < 8 bytes; deployment guide (Phase 13) will mandate ≥ 32-byte keys | 5×2=10 (gate) |
| SEC-002 | WebSocket bridge exposed without auth | 4 | 4 | 16 | Loopback is in-memory; real `build_fastapi_websocket_bridge` is a skeleton — deployment guide will mandate TLS + token auth | 4×2=8 (gate) |
| SEC-003 | Dashboard API leaks PHI to unauthenticated clients | 5 | 3 | 15 | No PHI in repo; auth required in any real deployment (Phase 13) | 5×2=10 (gate) |
| SEC-004 | Supply-chain compromise via optional ML dep | 4 | 2 | 8 | Core install uses pure stdlib + numpy + scipy; ML deps are optional `[ml]` extra; SBOM in CI artefact | 4×1=4 |

**Owner:** deployment / security maintainer.

## Category: Build / CI / tooling

| ID | Hazard | Sev | Lik | Risk | Mitigation | Residual |
|---|---|---|---|---|---|---|
| CI-001 | Silent type regression slips through (mypy disabled) | 3 | 3 | 9 | mypy is gated in `.github/workflows/ci.yml`; Python 3.11 + 3.12 matrix | 3×1=3 |
| CI-002 | Test coverage breadth-first; no mutation testing | 3 | 4 | 12 | Known gap; `mutmut` deferred to Phase 13 | 3×3=9 (gate) |
| CI-003 | Dependency pin rot (numpy API change) | 3 | 3 | 9 | `pyproject.toml` bounds; Dependabot on GitHub (policy, not enforced) | 3×2=6 |
| CI-004 | Flaky test masks regression | 3 | 3 | 9 | Every test uses fixed seeds; no time-based assertions except explicit timeout tests | 3×1=3 |

**Owner:** infra maintainer.

## Category: Claims / regulatory

| ID | Hazard | Sev | Lik | Risk | Mitigation | Residual |
|---|---|---|---|---|---|---|
| CLAIM-001 | Docs accidentally use "diagnose" / "treat" wording | 4 | 3 | 12 | Claims discipline in `REGULATORY.md §9`; future claims-lint CI check | 4×2=8 (gate) |
| CLAIM-002 | UI copy implies FDA clearance | 5 | 2 | 10 | No UI copy shipped yet; claims review on dashboard rollout | 5×1=5 |
| CLAIM-003 | Publication implies clinical efficacy without clinical trial | 5 | 3 | 15 | Pre-clinical framing enforced; publication templates include "decision-support research" qualifier | 5×2=10 (gate) |

**Owner:** project lead.

## Category: UI (out-of-scope but tracked)

| ID | Hazard | Sev | Lik | Risk | Mitigation | Residual |
|---|---|---|---|---|---|---|
| UI-001 | Web dashboard mis-renders priority badge colour | 4 | 3 | 12 | `web_ui/` has prop types; explicit colour-contrast tests pending | 4×2=8 (gate) |
| UI-002 | Dashboard times out on large casualty graph | 2 | 3 | 6 | `SemanticZoom` component pattern from in4n; load test deferred to Phase 13 | 2×2=4 |

**Owner:** web_ui maintainer.

---

## Risk acceptance

Entries marked **(gate)** in the residual column have residual risk ≥ 6
and are explicitly gated — they must be re-evaluated before the
corresponding phase (10 / 11 / 13) ships. They are acceptable in the
current pre-clinical research context.

Entries without **(gate)** are deemed acceptable with the current
mitigations for the research context.

## Traceability

Each entry's mitigation points to a specific module / test / doc. When
a mitigation changes, the relevant `CHANGELOG.md` entry must
reference the RISK ID. Example: `CHANGELOG.md:Phase 9b` references
**SAFE-001** via the Larrey-gap closure.

## Review cadence

- Every phase commit updates this register if new modules change the
  hazard landscape.
- Before any clinical pilot (Phase 11), the full register is reviewed
  with a regulatory consultant and re-scored.
- Before any real-hardware deployment (Phase 10), the BRIDGE-* and
  SEC-* categories are re-scored against the actual platform.
