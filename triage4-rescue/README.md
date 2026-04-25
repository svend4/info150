# triage4-rescue

Civilian mass-casualty triage support — the **third sibling** in
the triage4 monorepo after `triage4-fit` (wellness) and
`triage4-farm` (livestock welfare). Applies the decision-support
pipeline from `triage4` to earthquakes, floods, hurricanes, and
building-collapse incidents.

Domain framing comes from the
[civilian disaster response](../docs/adaptations/09_disaster_response.md)
adaptation study.

## What it is

- A library that produces **START triage tags** (Immediate /
  Delayed / Minor / Deceased) from stand-off observations of
  civilian casualties at a disaster scene.
- Includes **JumpSTART** — the pediatric variant of START —
  because the standard algorithm produces wrong calls on
  children. JumpSTART is a schoolroom-standard US / UK protocol.
- Emits **responder cues** — short texts the first responder
  reads off their tablet. Cue text is guarded at the dataclass
  level: no operational-command vocabulary, no definitive
  clinical pronouncements. See `docs/PHILOSOPHY.md`.
- Ships with a deterministic synthetic-incident generator so
  tests and demos work without real disaster footage (which
  does not exist ethically at scale).

## What it is not

- **Not a diagnostic tool.** Diagnosis is a clinical act; the
  responder's triage tag is a resource-allocation hint, not a
  clinical finding. The system never says "patient has
  internal bleeding", only "breathing absent after airway
  reposition — START tag: deceased. Mark for secondary
  assessment by medical personnel."
- **Not an incident-command replacement.** It never assigns
  responders, allocates vehicles, or routes casualties to
  hospitals. That is an Incident Commander's job and the
  cues never phrase themselves as commands.
- **Not a family-reunification system.** The data flow for
  reuniting casualties with relatives is a downstream feature
  (documented in the adaptation file); out of MVP scope for
  this library.

## Vocabulary translation from triage4

| triage4 (battlefield)           | triage4-rescue (civilian)        |
|---------------------------------|----------------------------------|
| `CasualtyNode`                  | `CivilianCasualty`               |
| `triage_priority` (1-4)         | `start_tag` (immediate / delayed / minor / deceased) |
| `RapidTriageEngine`             | `StartProtocolEngine`            |
| `larrey_baseline` (Napoleonic)  | `start_protocol` (1983 US NDMS)  |
| `MortalThresholds` (combat HR)  | `VitalSignsObservation` bands    |
| `MedicHandoff`                  | `ResponderHandoff`               |
| "medic"                         | "responder"                      |
| "battlefield"                   | "disaster zone" / "incident"     |

## Scope boundary

- Adult (≥ 8 yr) casualties: canonical 1983 START algorithm.
- Pediatric (< 8 yr) casualties: JumpSTART variant.
- Infants (< 1 yr): out of scope; the library raises a
  `StartProtocolError` rather than produce a misleading tag.
  Infant triage needs PTT (Pediatric Triage Tape) and a
  trained paediatric first responder.
- Only tags the four START categories. Does not output
  "likely cause of injury", "needs transport priority", or any
  other downstream decision.

## Copy-fork architecture

Like `triage4-fit` and `triage4-farm`, this sibling **does not
import** from `triage4` or the other siblings. Any conceptually
shared code (e.g. weighted-fusion, claims-lint vocabulary) is
re-implemented here. The DOMAIN_ADAPTATIONS index explains why:
premature extraction of a `biocore/` package before ≥ 3 siblings
converge on identical API surfaces.

This is sibling #3. The first `biocore/` extraction experiment
becomes reasonable *after* this commit — the three concrete
copies now make it safe to ask "what really is shared?"

## Multi-user / multi-shift coordination

`triage4_rescue.multiuser` is the **pilot** adoption of architectural
ideas from the archived `triage4_repo_v13.zip` SaaS variant — see the
top-level [`V13_REUSE_MAP.md`](../V13_REUSE_MAP.md) for the per-sibling
reuse policy. The subpackage adds:

- **`SessionManager`** — in-memory user + session store with
  `viewer / dispatcher / incident_commander / admin` roles.
- **`PolicyEngine`** — role × action permission gate. Action vocabulary
  is rescue-specific (`incident:log`, `responder:assign`, `shift:close`,
  …) and does not reuse v13's SaaS verbs.
- **`AuditLog`** — append-only journal of dispatcher actions. Defaults
  to in-memory; pass `db_path=` for SQLite-backed persistence (the only
  optional persistence in the rescue library).
- **`AsyncJobQueue`** — daemon-thread FIFO worker for batch
  incident-summary processing.

This is **copy-fork**, not import. No code is shared with v13 source;
the package is sized for the rescue domain and free to diverge. Other
siblings borrowing the same architecture write their own copy with
their own role / action vocabulary — see `V13_REUSE_MAP.md` for the
sibling-by-sibling table.

## See also

- `docs/PHILOSOPHY.md` — clinical-adjacent posture, what the
  system does and does not claim.
- `STATUS.md` — honest accounting of what's built and what's
  pending.
- [`docs/adaptations/09_disaster_response.md`](../docs/adaptations/09_disaster_response.md)
  — the parent adaptation study (strategic framing, not a
  product plan).
- [`V13_REUSE_MAP.md`](../V13_REUSE_MAP.md) — monorepo-wide policy on
  borrowing from the archived v13 SaaS variant.
