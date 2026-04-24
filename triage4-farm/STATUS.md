# triage4-farm — status

Honest state-of-the-prototype note. Read before assuming any
capability ships today.

## What is built

- `core/models.py` — 5 dataclasses: `AnimalObservation`,
  `JointPoseSample`, `WelfareScore`, `FarmerAlert`,
  `HerdReport`.
- `core/enums.py` — `Species` (dairy_cow / pig / chicken),
  `WelfareFlag` (well / concern / urgent),
  `AlertKind` (lameness / respiratory / thermal / behaviour).
- `signatures/lameness_gait.py` — quadruped gait-asymmetry
  score from left-right leg y-differential.
- `signatures/respiratory_rate.py` — species-aware resp-rate
  band scoring (cow 15-35 bpm normal, pig 20-40, chicken
  15-40).
- `signatures/thermal_inflammation.py` — hotspot-asymmetry
  score from thermal-delta observations.
- `welfare_check/species_profiles.py` — dairy cow / pig /
  chicken reference bands + thresholds.
- `welfare_check/welfare_engine.py` — review a whole herd,
  return a `HerdReport` with per-animal scores + alerts.
- `sim/synthetic_herd.py` — generate a reproducible herd
  observation set with a configurable lame-animal count.
- `tests/test_*.py` — ~25 tests across core, signatures,
  engine.
- `pyproject.toml`, `Makefile`, `README.md`,
  `docs/PHILOSOPHY.md`.

## What is NOT built

- **No real camera / pose integration.** `JointPoseSample`
  assumes upstream extracted keypoints. A future
  `perception/` module would wire MegaDetector-style
  pretrained models + ear-tag OCR.
- **No ear-tag reader.** Per-animal identification is stubbed
  — each animal has an `id` string; real farms need RFID or
  optical ear-tag OCR.
- **No vet EHR integration.** The `FarmerAlert` is a plain
  dict — pushing it into DairyComp 305, Cargill Boumatic,
  Lely Horizon etc. is a future integration layer.
- **No calibration against real herds.** Lameness thresholds
  are stubs from the DairyCo 1-5 scoring system but not
  validated against real gait video.
- **No antibiotic / dosing recommendations.** By design (see
  `docs/PHILOSOPHY.md`).
- **No milk-yield / feed-intake ingestion.** Integrations
  with barn management systems are future work.
- **No herd-level trend tracking.** Per-animal history /
  weekly trends / lactation-cycle awareness need a storage
  layer.

## Scope boundary — explicit

triage4-farm **is**:
- a welfare-observation library that scores animals for
  signs of lameness, respiratory distress, or localised
  inflammation, and produces farmer-facing alerts.

triage4-farm **is not**:
- a veterinary decision-support tool.
- a replacement for a licensed veterinarian.
- a tool that recommends antibiotic use, dosing, withdrawal
  periods, or any treatment protocol.

These are not marketing caveats — they are product boundaries
enforced at the dataclass level. `FarmerAlert.__post_init__`
raises `ValueError` if alert text contains forbidden
veterinary-practice vocabulary (see `docs/PHILOSOPHY.md`).

## Known limits

- Lameness scoring is 2D from a side-on barn camera. Front-on
  angles under-detect.
- Thermal signature needs a thermal camera — RGB-only
  observations score thermal at 0.5 neutral.
- Species-specific resp-rate bands are population averages.
  Per-animal baseline is future work.
- Respiratory rate from body motion needs the animal
  stationary — grazing / moving animals give noisy signal.
- Behaviour anomalies (head-tilting, hiding, not feeding)
  are not modelled yet.

## Next natural extensions

Roughly ordered by value:

1. Real barn-camera → pose-estimator pipeline.
2. Ear-tag OCR for per-animal identification.
3. Per-animal baseline learner (week-1 calibration per cow).
4. Farmer-facing mobile alerts.
5. Barn-management-system adapters (DairyComp, Lely, etc.).
6. Additional species (beef cow, sheep, goat).
7. Behaviour-pattern detection (not-feeding, hiding).
