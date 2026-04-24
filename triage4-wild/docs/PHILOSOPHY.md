# Philosophy — three new boundaries, SMS-length constraint

triage4-wild adds three boundaries not present in any prior
sibling and one structural constraint (SMS-length cap) that
reshapes the library's output format. Each is motivated by
a specific empirical failure mode that open-source wildlife
tooling has historically produced.

## Field-security boundary

### Why it's load-bearing

GPS coordinates of endangered animals (elephants, rhinos)
are financial targets. Published cases: leaked collar data
for white rhinos in Kruger National Park (2014-2018) was
correlated with increases in local poaching pressure;
similar patterns in Kenya Ol Pejeta's black-rhino telemetry
show up in security reviews. Any open-source library that
touches wildlife observation and leaves plaintext location
handling unguarded is a candidate vector.

### How it's enforced

- `LocationHandle` is an opaque string token from upstream
  — typically a grid-cell ID ("grid-A7") or reserve-zone
  label ("zone-central"). Plaintext decimal coordinates
  are never accepted.
- `RangerAlert.__post_init__` rejects alert text
  containing vocabulary that suggests coordinate leakage:
  `latitude`, `longitude`, `lat:`, `lng:`, `lon:`, `gps
  coordinates`, `coordinates:`, `located at`.
- `RangerAlert.__post_init__` also rejects obvious
  decimal-degree patterns via a simple heuristic: any
  floating-point pair in `N.NNN, N.NNN` form (3+ decimal
  digits) is refused.

## Poaching-prediction overreach

### Why it's its own boundary

Risk-flag 9.3 in the parent adaptation file is explicit:
"Don't claim to 'predict poaching events' or 'optimise
anti-poaching patrols' — that's a different project with
different ethics." A conservation-health tool that drifts
into patrol optimisation takes on a surveillance-tech
regulatory posture and ethics review that the library is
not set up for.

### How it's enforced

`RangerAlert` rejects:
- `predict poacher`, `predict poaching`
- `likely poacher`, `suspect poacher`, `identify poacher`
- `optimise patrol`, `optimize patrol`
- `schedule patrol route`, `patrol route recommendation`
- `anti-poaching operation`

## Ecosystem-prediction overreach

### Why it's its own boundary

Wildlife-conservation ML products have a history of
over-claiming: "population trajectory predictions",
"extinction risk scoring", "conservation outcome
modeling". Those are legitimate scientific outputs in a
research tool but they're claims this library is
structurally unable to support from the data it processes
(one-pass observations of individual animals). The
boundary keeps the output honest.

### How it's enforced

`RangerAlert` rejects:
- `population trajectory`, `predict extinction`
- `extinction risk`
- `species will` (overreach trope — "species will
  disappear within", etc.)
- `conservation outcome`, `conservation outcome
  prediction`

## SMS-length structural constraint

### Why it's architectural

Ranger handoff runs on Iridium satcom or low-bandwidth
SMS in the field. A 200-char text is a standard frame
budget. Alerts that exceed that are silently truncated
downstream, which is worse than refusing to emit them —
truncation can drop the channel kind or the
secondary-review framing, changing the alert's meaning.

### How it's enforced

`RangerAlert.__post_init__` checks
`len(self.text) <= MAX_RANGER_SMS_CHARS` and raises
`ValueError` if exceeded. The engine is responsible for
producing text short enough; the dataclass refuses
oversized alerts rather than silently accept them.

The library's engine includes a helper that formats
alerts to the budget automatically; consumer apps that
override text generation inherit the obligation to
stay inside the cap.

## What gets reused from triage4

Conceptual, not literal.

- Unit-interval signature scoring.
- Weighted-fusion pattern.
- Dataclass-level claims guard (now with three new
  boundaries + length constraint).
- Deterministic synthetic-fixture pattern with
  `zlib.crc32` seeds.

## What does NOT get reused

- Human medical signatures.
- Anything involving lat/lon plaintext — the boundary is
  architectural.
- The generous multi-paragraph output format of prior
  siblings — bandwidth constraint demands curtness.

## Standard forbidden lists (less novel, still enforced)

Clinical — no definitive diagnosis language:
- `is injured`, `has a wound`, `confirms`
- `diagnosis`, `diagnosis:`
- `is in shock`, `is suffering`

Operational — no patrol command:
- `intercept`, `deploy patrol`, `dispatch rangers`
- `apprehend`, `detain`

No-false-reassurance (light):
- `herd is safe`, `no threats detected`, `all clear`

Panic-prevention (light):
- `tragedy`, `catastrophe`, `fatalities`

## When these lines move

If a future version:

- ingests human-presence data → fork as a separate
  product with its own surveillance-ethics review.
- produces patrol routing → fork `triage4-wild-patrol`
  with explicit conservation-tech-ethics review.
- stores plaintext GPS → that's a different codebase
  with different infra-security requirements.

Don't erode the three boundaries inside one codebase.
The architecture is specifically designed so leaking
location / scope-creeping into patrol optimisation /
over-claiming ecosystem predictions all fail at
construction time.

## In short

Three new boundaries — field-security, poaching-overreach,
ecosystem-overreach. One structural constraint —
SMS-length cap. The ranger is the user; the library is a
200-character hint that never reveals where the animal
is, what the ranger should do operationally, or what the
species' future looks like.
