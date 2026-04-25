# portal

Read-only cross-sibling coordination layer for the `triage4-*` family.

## Policy

**Не слияние — совместимость.** *Not merger — compatibility.*

The portal does not extract or share sibling code. It does not modify any
sibling. Each sibling remains the source of truth for its own domain. The
portal's job is narrower:

- Read each participating sibling's `Report` / `Alert` outputs through a
  small per-sibling adapter (~50 lines).
- Translate them into a common `PortalEntry` shape.
- Discover typed `Bridge` relationships across siblings — co-occurrence,
  domain-neighbour, escalation, etc. — that no single sibling can see.

Participation is voluntary: a sibling without an adapter is invisible to
the portal but otherwise unchanged.

## What the portal is NOT

- It is **not** a place to extract shared sibling logic. Mechanical-duplication
  extractions belong in `biocore`. Cross-sibling **relationships** belong here.
- It is **not** a wrapper that calls into siblings. It only consumes their
  outputs (`Report` / `Alert` instances), never their internals.
- It is **not** a forced standardisation effort. Siblings keep their own
  enums, dataclasses, and labels. The adapter does the translation.

## Layout

```
portal/
├── portal/
│   ├── __init__.py
│   ├── protocol.py     # PortalEntry, BridgeKind, Bridge
│   ├── registry.py     # BridgeRegistry (in-memory typed edges)
│   ├── coords.py       # 6-bit domain coordinates + Hamming distance
│   ├── discovery.py    # Deterministic bridge-discovery rules
│   └── cli.py          # `portal demo` smoke command
└── tests/
```

## Pilot siblings

`triage4-fish`, `triage4-bird`, `triage4-wild`. Each ships a
`portal_adapter.py` exporting an `adapt(report) -> Iterable[PortalEntry]`
function. Other siblings can opt in later by providing the same module
shape; nothing forces them to.

## Adding the portal to a new sibling

1. Add `portal_adapter.py` to the sibling package, exporting `adapt()`.
2. Pick a 6-bit domain coordinate (see `portal.coords`) and register it
   in `portal/portal/coords.py` under `SIBLING_COORDS`.
3. (No new dependency on the sibling side — the adapter imports
   `portal.protocol` only.)
