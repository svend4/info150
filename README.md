# info150 — monorepo headquarters

A 17-package monorepo organised around the **triage4** decision-support
research stack and a 14-sibling catalogue of domain adaptations, plus
two coordination layers (`biocore`, `portal`) and frozen historical
archives.

```
info150/                                      ← this README
├── README.md                                 ← orientation + map (this file)
├── DOMAIN_ADAPTATIONS.md                     ← 14-sibling catalogue + extraction policy
├── ARCHIVES.md                               ← what the archives are + reuse policy
├── V13_REUSE_MAP.md                          ← per-sibling sketches for v13 borrowings
│
├── triage4/                                  ← FLAGSHIP — DARPA Triage Challenge stack
│
├── biocore/                                  ← shared narrow utility layer (frozen)
├── portal/                                   ← read-only cross-sibling coordination
│
├── triage4-fit/        04 fitness / wellness
├── triage4-clinic/     05 telemedicine pre-screening
├── triage4-home/       06 elderly home care
├── triage4-site/       07 industrial safety
├── triage4-pet/        08 veterinary clinic
├── triage4-rescue/     09 disaster response   ← v13 multiuser pilot lives here
├── triage4-farm/       10 livestock / agtech
├── triage4-aqua/       11 pool / beach safety
├── triage4-sport/      12 sports performance
├── triage4-drive/      13 driver monitoring
├── triage4-crowd/      14 crowd safety
├── triage4-wild/       01 wildlife terrestrial
├── triage4-bird/       02 wildlife avian
├── triage4-fish/       03 wildlife aquatic / aquaculture
│
├── Branch · Branch · Branch · Обзор проекта svend4_meta2.{md,txt,json}
│                                             ← original ChatGPT design log (read-only)
└── triage4_repo_v13.zip                      ← alternative SaaS variant (read-only)
```

## The three layers

The monorepo is structured as three deliberately separated layers, each
answering a different question. **They do not replace each other.**

### 1. The flagship + 14 sibling catalogue (deepening, independent)

`triage4/` is the original DARPA Triage Challenge research stack. The
14 `triage4-*` siblings are domain copy-forks — wildlife, aquaculture,
fitness, industrial safety, etc. — each documented in
`docs/adaptations/01-14`.

The architectural rule (`DOMAIN_ADAPTATIONS.md §7`): **siblings do not
import each other.** Each one is free to grow its own depth — own
plugins, signatures, dashboards, role vocabulary. New "buds and branches"
sprout per sibling, not via a forced shared abstraction.

### 2. `biocore/` — narrow shared utility layer (frozen)

Tier-1 + tier-2 mechanical extractions only — `crc32_seed`,
`DECIMAL_PAIR_RE`, `check_sms_cap`, `normalise_weights`,
`weighted_overall`, `apply_channel_floor`. Each pattern was bytewise
duplicated across ≥ 12 siblings before it was extracted. **Frozen at
its current scope** — no further extraction tiers planned.

biocore answers: *"what byte-level helper does every sibling
re-implement?"* If three siblings share a 4-line clamp-and-validate, it
goes here. Anything more interesting belongs elsewhere.

### 3. `portal/` — cross-sibling coordination (compatibility, not merger)

Inspired by [github.com/svend4/nautilus](https://github.com/svend4/nautilus):
**"Не слияние — совместимость"** — *"Not merger, compatibility."*

The portal does not extract or share sibling code. It does not modify
any sibling. Each sibling stays the source of truth. The portal reads
each participating sibling's `Report` / `Alert` outputs through a small
per-sibling adapter and discovers typed `Bridge` relationships across
them — co-occurrence, domain-neighbour, escalation, geographic, temporal
correlate. Things no single sibling can see on its own.

Adapter participation is voluntary; pilots ship for `triage4-fish`,
`triage4-bird`, `triage4-wild`.

portal answers: *"what relationships exist between siblings that no
single sibling can detect?"*

### Three layers, three rules

| Layer    | Rule                                                              |
|----------|-------------------------------------------------------------------|
| Sibling  | Develop in depth. Copy-fork from triage4. **No imports between siblings.** |
| biocore  | Mechanical duplications across ≥ 12 siblings. **Frozen scope.**   |
| portal   | Read-only. Voluntary participation. **Adapter only, never wraps.** |

## Archives — origin material

Two read-only artefacts live at the repo root for provenance. **Neither
is consumed by any build or test.** See [`ARCHIVES.md`](ARCHIVES.md) for
the full breakdown.

- `Branch · Branch · Branch · Обзор проекта svend4_meta2.{md,txt,json}`
  — original 2026-04-01 ChatGPT design log that seeded the K3 matrix
  and the flagship blueprint.
- `triage4_repo_v13.zip` — an alternative SaaS-flavoured triage4 variant
  that diverged from the flagship's research posture. **Not for
  flagship use** (regulatory / PHI reasons documented in `ARCHIVES.md`).
  Some of its modules (`auth/`, `jobs/`, `audit_repository`) are
  reusable as **reference scaffolding** for several of the operational
  siblings — see [`V13_REUSE_MAP.md`](V13_REUSE_MAP.md) for the
  per-sibling decision matrix.

The first sibling to actually adopt v13 ideas is `triage4-rescue`, via
its new `triage4_rescue.multiuser` subpackage (sessions + RBAC + audit
log + async jobs, with rescue-specific role vocabulary). The pattern
is **copy-fork, not import** — no v13 source flows through; the rescue
package owns its own copy free to diverge.

## Quickstart

Each package is independently installable + testable.

```bash
# flagship
cd triage4 && make install-dev && make qa

# any sibling — same shape
cd triage4-rescue && make install-dev && make qa

# shared utility layer
cd biocore && make install-dev && make qa

# cross-sibling coordination layer
cd portal && make install-dev && make qa
```

CI (`.github/workflows/qa.yml`) runs the full matrix across all
17 packages on every push. See the workflow file for the per-package
matrix definition.

## Where to start reading

For a given goal, jump here:

| If you want to…                                           | Read first                                                     |
|-----------------------------------------------------------|----------------------------------------------------------------|
| Understand the flagship stack                             | [`triage4/README.md`](triage4/README.md) → [`triage4/docs/STATUS.md`](triage4/docs/STATUS.md) |
| Understand the 14-sibling philosophy                      | [`DOMAIN_ADAPTATIONS.md`](DOMAIN_ADAPTATIONS.md)               |
| Understand the biocore extraction policy                  | [`biocore/README.md`](biocore/README.md) + DOMAIN_ADAPTATIONS §7 |
| Understand the portal / nautilus policy                   | [`portal/README.md`](portal/README.md)                         |
| Decide whether to borrow from the v13 archive             | [`V13_REUSE_MAP.md`](V13_REUSE_MAP.md)                         |
| Read what's in the historical archives                    | [`ARCHIVES.md`](ARCHIVES.md)                                   |
| Add a new sibling                                         | `DOMAIN_ADAPTATIONS.md` + study `triage4-fit/` as the template |
| Add a portal adapter to a sibling                         | `portal/README.md` + study `triage4-fish/triage4_fish/portal_adapter.py` |

## Disclaimer

triage4 and its siblings are **research-grade decision-support**       <!-- claims-lint: allow -->
software — not certified medical / industrial / safety devices, and
must not be used as a standalone source of clinical, operational, or
safety decisions. They are framed, tested, and documented as
decision-support for qualified human operators. Each sibling carries
its own `docs/PHILOSOPHY.md` documenting the boundaries it enforces.

License: MIT. See [`triage4/LICENSES/`](triage4/LICENSES/).
