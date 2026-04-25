# biocore

Shared utilities extracted from the fourteen `triage4-*` siblings
in this monorepo. Per `DOMAIN_ADAPTATIONS §7`, this package is
the **first slice of `biocore/` extraction** — created only after
fourteen concrete copy-forks proved which patterns are genuinely
shared (and which only LOOK shared but diverge in posture per
sibling).

## What's in scope

biocore contains the small set of utilities that:

1. Appear **literally identically** across multiple siblings
   (same regex, same logic, same intent), AND
2. Are **boundary-mechanism**, not domain-vocabulary
   (the vocabulary itself stays per-sibling — the
   shape of "check this text against a forbidden list" is
   shared).

The MVP slice covers four utility modules:

- **`biocore.seeds`** — `crc32_seed(parts)` for deterministic
  per-process-stable RNG seeding. Used in twelve of fourteen
  siblings' synthetic generators (everything from
  `triage4-home` onward + the three we ported in Phase A).
  triage4-fit uses pure-integer arithmetic and doesn't need
  this; otherwise universal.

- **`biocore.coords`** — `DECIMAL_PAIR_RE` regex +
  `contains_decimal_coords(text)` predicate. Used in
  `triage4-wild`, `triage4-bird`, and `triage4-fish` to
  enforce the field-security boundary against decimal-degree
  coordinate leakage.

- **`biocore.text_guards`** — generic claims-guard helpers:
  `check_forbidden_phrases(text, phrases, list_label)` and
  `check_identifier_prefix(text, prefixes, list_label)`. The
  PER-LIST vocabulary lives in each sibling; the SHAPE of
  the check (lower-case the text, scan substrings, raise
  `ValueError` with a consistent error-message format) is
  shared across all fourteen siblings' claims-guard
  dataclasses.

- **`biocore.sms`** — `check_sms_cap(text, max_chars,
  label)` enforcing the SMS-length constraint introduced
  by `triage4-wild` and reused by `triage4-bird`.

## What's out of scope

Per `DOMAIN_ADAPTATIONS §8` ("anti-patterns to avoid"):

- **Domain enums** (Species, AlertKind, RiskBand, etc.)
  are per-sibling and stay there. The vocabulary IS the
  boundary — extracting it would force premature
  agreement.
- **Engine logic** stays per-sibling. Each engine has its
  own corroborative-alert / mortal-sign-override /
  three-audience-routing / multi-modal-fusion specifics.
- **Per-domain dataclasses** stay per-sibling.
  `CivilianCasualty`, `AnimalObservation`, `PetObservation`,
  `WildlifeObservation`, etc. are not interchangeable.
- **Forbidden-vocabulary lists** stay per-sibling. The
  list of words "the library never says" is exactly the
  product's posture; shared lists would erase domain
  specificity.

## Adoption

Siblings adopt biocore **incrementally and optionally**.
The copy-fork architecture from `DOMAIN_ADAPTATIONS §7`
remains the default; biocore is an OPTIONAL dependency
that consolidates utilities without forcing a
common-base-class pattern.

A sibling that adopts biocore:

1. Adds `biocore` to its `pyproject.toml` dependencies.
2. Replaces inline utility code with a `from biocore.X
   import Y` import.
3. Per-list / per-domain code stays where it lives.

A sibling that does NOT adopt biocore continues to work
unchanged.

## Why now

After fourteen siblings, the shared surface is mapped
empirically. Three patterns hit duplication thresholds:

- The decimal-coord regex appears verbatim in three
  siblings (`triage4-wild`, `triage4-bird`,
  `triage4-fish`).
- The crc32-seed helper appears in twelve siblings.
- The "lowercase + scan + raise" claims-guard shape
  appears in every claims-guard `__post_init__` across
  all fourteen siblings.

Below the duplication threshold (and so kept per-
sibling): the actual vocabulary lists, the engine fusion
logic, the per-domain alert-routing rules. Those genuinely
diverge per posture and shouldn't be unified.

## See also

- `DOMAIN_ADAPTATIONS.md §7` — the monorepo philosophy
  that explicitly waits for ≥3 sibling convergence
  before extracting `biocore/`. Threshold met for the
  utilities above; not yet met for the larger shared
  surfaces.
