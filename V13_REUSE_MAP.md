# V13 reuse map — per-sibling adoption sketches

The `triage4_repo_v13.zip` archive at the repo root captures an
alternative **SaaS-flavoured** evolution of triage4 that was rejected
for the flagship (see [`ARCHIVES.md`](ARCHIVES.md) for the why). This
file answers a narrower question: **which parts of v13, if any, are
worth borrowing for the 14 catalogue siblings?**

Short answer: a small subset — `auth/`, `jobs/`, `audit_repository`,
`world_replay/`, `analytics/diffing` — is genuinely reusable; the rest
is too clinical/DARPA-coupled. The boundaries below are deliberately
conservative.

This map is for **reference only**. Nothing here must be ported. A
sibling may diverge entirely (a wild ranger does not need RBAC). When
something IS ported, it is **copy-forked** with sibling-specific role
names, action vocabulary, and integration tests — never `pip install`-ed
from the archive.

---

## Domain-neutrality of v13 modules (verified)

I read the actual sources, not just the file names. Verdict per module
group:

| v13 module group | Domain coupling | Verdict |
|---|---|---|
| `auth/session_manager.py`, `permissions.py`, `policy_engine.py` | Role names + action verbs are SaaS-flavoured (`viewer/analyst/operator/admin`, `scenario:mutate`, `workspace:diff`). Engine itself is generic. | **Reusable scaffolding.** Rename roles + actions per sibling. |
| `jobs/async_queue.py`, `worker_loop.py`, `worker_process.py`, `job_manager.py`, `job_control.py` | None. Plain `threading.Queue` + daemon worker. ~80 LOC total. | **Reusable verbatim.** |
| `repositories/audit_repository.py` + `storage/sqlite_store.py` | SQLite-coupled; row shape (`action / actor_user_id / actor_role / target_type / target_id / payload`) is generic. | **Reusable schema.** SQLite introduces persistence — sibling must want that. |
| `repositories/notification_repository.py`, `notification_rules_repository.py` | Generic rule-driven notification dispatch. | **Reusable.** |
| `world_replay/timeline_store.py`, `session_store.py`, `world_state_store.py`, `replay_engine.py` | Event-sourcing of session/world snapshots. Domain-coupled by `world_state` field semantics, but the store mechanics generalise. | **Reusable for siblings that want session replay.** |
| `analytics/diffing.py`, `comparison.py`, `timeline.py` | None. `deep_diff(left, right)` works on any dict/list/scalar tree. | **Reusable verbatim.** |
| `schemas/scenario_schema.py` + `data/scenarios/*.json` | Casualty-flavoured but the JSON envelope is generic. | **Reusable schema, content rewritten per domain.** |
| `signatures/breathing_*`, `perfusion_*`, `bleeding_*`, `thermal_*` | Clinical-only. | **Do not port to any sibling.** |
| `dynamic/dynamic_body_graph.py`, `state_graph/body_state_graph.py` | Clinical body model. | **Do not port.** Per-sibling state graphs are domain-specific. |
| `tactical_scene/casualty_markers.py`, `map_projection.py` | DARPA-flavoured map. | **Do not port.** |
| `mission_coordination/assignment_engine.py` | DARPA mission coordination. | **Do not port.** |
| `triage_temporal/deterioration_model.py`, `priority_engine.py`, `revisit_logic.py` | Clinical triage logic. | **Do not port.** |
| `repositories/casualty_repository.py`, `world_state_repository.py` | Clinical/DARPA. | **Do not port.** |
| `data/triage4.sqlite` (5.5 MB blob) | Pre-computed casualty rows. | **Strictly forbidden — see [`ARCHIVES.md`](ARCHIVES.md) safety caveat.** |

---

## Per-sibling adoption sketches (all 14)

Each sketch lists: **fit summary**, **modules to borrow**, **role
vocabulary**, **action vocabulary** (if RBAC is borrowed), and **what
to skip explicitly**.

### 01 — `triage4-wild` (wildlife terrestrial)

- **Fit:** Limited. Solo ranger, satcom-bandwidth-constrained, single-user.
- **Borrow:** `analytics/diffing.py` only — useful to compare two survey
  runs offline. Maybe `jobs/` for long post-survey video processing if a
  use-case appears (currently none).
- **Skip:** `auth/`, `audit/`, `world_replay/`, all SQLite. Single-user.
- **Roles / actions:** N/A.

### 02 — `triage4-bird` (wildlife avian)

- **Fit:** Same as `triage4-wild`. Solo ornithologist.
- **Borrow:** `analytics/diffing.py` for survey-run comparison. Audio
  pipeline batch processing could justify `jobs/` later.
- **Skip:** `auth/`, RBAC, persistence.
- **Roles / actions:** N/A.

### 03 — `triage4-fish` (aquaculture)

- **Fit:** Partial. Single farm-manager dashboard today, but multi-pen
  sites can have multi-staff in future.
- **Borrow:** `jobs/` for batch pen-scan processing (immediate); `auth/`
  + `audit/` deferred until multi-staff requirement appears.
- **Skip:** SQLite blob, `world_replay/`. Pen reports are short-lived.
- **Roles / actions:** if/when adopted — `viewer / pen_keeper / farm_manager / admin` with actions `pen:read / pen:scan / pen:configure / users:mutate`.

### 04 — `triage4-fit` (fitness / wellness)

- **Fit:** Minimal. Consumer single-user app.
- **Borrow:** Only `data/digest_presets/*.json` schema as a pattern for
  workout templates. No code modules.
- **Skip:** `auth/`, `audit/`, `jobs/`, all SaaS scaffolding.
- **Roles / actions:** N/A — this sibling is per-device.

### 05 — `triage4-clinic` (telemedicine pre-screening)

- **Fit:** **Do not borrow from v13.** Same regulatory posture as the
  flagship: PHI-adjacent, decision-support-only, no claims discipline
  baked into v13's auth model. The reasons given in `ARCHIVES.md §2`
  ("why importing from v13 is not recommended") apply identically.
- **Borrow:** Nothing.
- **Skip:** Everything.

### 06 — `triage4-home` (elderly home)

- **Fit:** Multi-staff dashboard, but PHI-adjacent (resident behavioural
  data). Cautious borrow.
- **Borrow:** `auth/` (with PHI-aware audit), `jobs/` for nightly digest.
- **Skip:** `world_replay/` (resident-behaviour replay → privacy hazard),
  `triage4.sqlite` blob, `notification_repository` until the privacy
  posture is documented.
- **Roles / actions:** `viewer / care_aide / nurse_in_charge / admin`
  with actions `resident:read / shift:log / alert:acknowledge / users:mutate`.

### 07 — `triage4-site` (industrial safety)

- **Fit:** **Strong.** Multi-user (officer + supervisor), regulatory
  audit trail required, shift-based notifications.
- **Borrow:** `auth/` + `audit_repository` (mandatory for OSHA-style
  accountability), `jobs/` for shift-summary batches, `notification_*`
  for alert dispatch.
- **Skip:** `world_replay/` (shift replay is nice-to-have, not MVP),
  any clinical signature.
- **Roles / actions:** `viewer / safety_officer / shift_supervisor / admin`
  with actions `incident:log / hazard:flag / shift:close / policy:mutate`.

### 08 — `triage4-pet` (veterinary)

- **Fit:** Vet workflow, owner records. PHI-adjacent for owner data.
- **Borrow:** `auth/` (with care — owner PII boundary), `jobs/` for
  appointment-batch reminders.
- **Skip:** `world_replay/` (no replay use-case), SQLite blob.
- **Roles / actions:** `viewer / vet_tech / vet / admin` with actions
  `patient:read / treatment:log / record:edit / users:mutate`.

### 09 — `triage4-rescue` (disaster response) **← pilot**

- **Fit:** **Strongest match.** Multi-dispatcher operations centre,
  incident accountability requires audit, batch incident processing
  fits jobs layer, post-incident replay drives lessons-learned.
- **Borrow:** `auth/` + `audit_repository` + `jobs/` + (optionally
  later) `world_replay/`.
- **Skip:** `tactical_scene/casualty_markers.py` (DARPA-flavoured;
  rescue uses civilian START/JumpSTART markers already), `triage4.sqlite`
  blob, the entire `repositories/casualty_repository.py` (incompatible
  schema — rescue's `IncidentReport` is the source of truth).
- **Roles / actions:** `viewer / dispatcher / incident_commander / admin`
  with actions `incident:read / incident:log / responder:assign /
  resource:dispatch / shift:close / users:mutate / policy:mutate`.
- **Persistence:** SQLite acceptable for incident audit log (rescue
  already has multi-shift continuity needs); explicitly opt-in.

### 10 — `triage4-farm` (livestock / agtech)

- **Fit:** Partial. Farm manager + farmhand staff possible.
- **Borrow:** `jobs/` for nightly herd-health batches (immediate);
  `auth/` + `audit/` if multi-staff arrives.
- **Skip:** `world_replay/` (no replay use-case for paddock scans),
  clinical signatures.
- **Roles / actions:** if/when adopted — `viewer / farmhand / farm_manager / admin`.

### 11 — `triage4-aqua` (pool / beach safety)

- **Fit:** Strong. Lifeguard team with shift rotations, audit useful
  post-incident.
- **Borrow:** `auth/` + `audit_repository` + `jobs/` (lighter persistence
  than rescue — shift logs only, not full incident archive).
- **Skip:** `world_replay/` (real-time only), SQLite blob.
- **Roles / actions:** `viewer / lifeguard / chief_lifeguard / admin`
  with actions `pool:read / drown:flag / shift:close / users:mutate`.

### 12 — `triage4-sport` (sports performance)

- **Fit:** Coaching dashboard, athlete biometric data is PHI-adjacent.
- **Borrow:** `auth/` (with athlete-consent boundary), `jobs/` for
  session post-processing, `world_replay/` for workout replay.
- **Skip:** `audit_repository` if it logs biometric values (privacy);
  scope it to system actions only.
- **Roles / actions:** `viewer / athlete / coach / admin` with actions
  `session:read / session:log / plan:edit / athlete:invite`.

### 13 — `triage4-drive` (driver monitoring / fleet)

- **Fit:** Strong. Multi-driver + multi-dispatcher fleet, session replay
  central to incident review.
- **Borrow:** `auth/` + `audit/` + `jobs/` + `world_replay/`. Closest
  to v13's original SaaS shape.
- **Skip:** Clinical signatures (none used here), `tactical_scene/`,
  `triage4.sqlite` blob.
- **Roles / actions:** `viewer / driver / dispatcher / fleet_admin`
  with actions `trip:read / trip:start / driver:assign / vehicle:configure / users:mutate`.

### 14 — `triage4-crowd` (crowd safety)

- **Fit:** Strong. Event operations centre, multi-coordinator,
  post-event analytics matter.
- **Borrow:** `auth/` + `audit/` + `jobs/` + `world_replay/timeline_store`
  (the timeline shape fits event-density curves).
- **Skip:** SQLite blob, clinical signatures, `tactical_scene/`.
- **Roles / actions:** `viewer / coordinator / event_lead / admin` with
  actions `zone:read / zone:flag / responder:dispatch / event:close / users:mutate`.

---

## Summary table — who borrows what

| Sibling | `auth/` | `jobs/` | `audit/` | `world_replay/` | `notification_*` | `analytics/diffing` |
|---|---|---|---|---|---|---|
| 01 wild       | — | maybe | — | — | — | ✓ |
| 02 bird       | — | maybe | — | — | — | ✓ |
| 03 fish       | later | ✓ | later | — | — | maybe |
| 04 fit        | — | — | — | — | — | — |
| 05 clinic     | — | — | — | — | — | — |
| 06 home       | ✓ (PHI-careful) | ✓ | ✓ (PHI-careful) | — | later | — |
| 07 site       | ✓ | ✓ | ✓ | later | ✓ | maybe |
| 08 pet        | ✓ (PII-careful) | ✓ | ✓ | — | later | — |
| 09 rescue     | **✓ pilot** | **✓ pilot** | **✓ pilot** | later | later | maybe |
| 10 farm       | later | ✓ | later | — | — | maybe |
| 11 aqua       | ✓ | ✓ | ✓ (light) | — | ✓ | — |
| 12 sport      | ✓ | ✓ | scoped | ✓ | — | — |
| 13 drive      | ✓ | ✓ | ✓ | ✓ | ✓ | maybe |
| 14 crowd      | ✓ | ✓ | ✓ | ✓ | ✓ | maybe |

**Pilot:** `triage4-rescue` — see `triage4-rescue/triage4_rescue/multiuser/`
once that pilot lands.

---

## Cross-cutting safety rules

1. **Never extract `triage4_repo_v13/data/triage4.sqlite`** to any
   working tree. Synthetic casualty rows resemble PHI; this is
   forbidden by `ARCHIVES.md §2` and applies to every sibling.
2. **Never `pip install` the archive.** Its `triage4` namespace would
   shadow the flagship and break imports.
3. **Strip `__pycache__`** from any extraction (the archive ships ~30
   `.pyc` files inline).
4. **Rename roles and actions per sibling.** `viewer/analyst/operator/admin`
   is a SaaS template; sibling-specific vocabulary is mandatory.
5. **PHI / PII boundary.** Any sibling that would log identifiable
   resident / patient / owner data through `audit_repository` MUST
   document the data-protection posture in its own `STATUS.md` before
   adoption.
6. **Persistence is opt-in.** Today every sibling is stateless
   in-memory. Introducing SQLite is a real architectural shift; treat
   it as a phase change, not a refactor.
7. **Tests do not transfer.** v13's `test_v{N}_features.py` files are
   feature-version-locked; siblings rewrite tests around their own
   invariants.

---

## Relationship to `biocore` and `portal/`

Three layers, three roles — none replaces the other:

- **`biocore/`** — frozen narrow utility layer. Bytewise duplications
  across ≥ 12 siblings, extracted once. **Not the place for v13
  borrowings.** Keep biocore narrow; let each sibling copy-fork.
- **`portal/`** — read-only cross-sibling coordination
  (nautilus-style "compatibility, not merger"). **Not the place for
  v13 borrowings either.** The portal reads sibling outputs; it does
  not import sibling internals.
- **v13 borrowings** — copy-forked into individual siblings under a
  per-sibling subpackage (e.g. `triage4_rescue/multiuser/`). Each
  sibling owns its own copy, adapts the role/action vocabulary, and
  diverges freely.

This three-layer separation is deliberate. Mixing them re-introduces
the merger pressure that `portal/`'s nautilus policy explicitly
rejects.
