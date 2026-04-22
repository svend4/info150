# triage4 — Further Reading

Consolidated bibliography for the methods, standards, and
historical baselines referenced across triage4 code and docs. This
is **reference material** — not an endorsement, not a course, not a
substitute for domain expertise.

Entries are grouped by the triage4 area they touch. Each entry
notes the relevant triage4 module or doc in parentheses.

## 1. Triage and battlefield medicine

- **Dominique-Jean Larrey (1797).** Establishment of the first
  military triage system: mortal / serious / light categories,
  treat-urgent-first principle. No single citable paper;
  historical record in Larrey's *Mémoires de chirurgie militaire*
  (1812–1817). Modern reconstruction:
  - Skandalakis PN, Lainas P, Zoras O, *et al.* "Dominique-Jean
    Larrey and the origin of modern triage." *World J Surg*.
    2006;30(8):1392–9.
  - (`triage_reasoning/larrey_baseline.py`,
    `tests/test_larrey_baseline.py`)

- **DARPA Triage Challenge Event 3.** Public programme
  description (2023–). Defines the five gates triage4 targets:
  find & locate, rapid triage, trauma assessment, vitals, HMT.
  - See darpa.mil programme page and `docs/darpa_mapping.md`.

## 2. Remote sensing / stand-off vitals

- **Eulerian video magnification.** Wu HY, Rubinstein M, Shih E,
  Guttag J, Durand F, Freeman W. "Eulerian video magnification
  for revealing subtle changes in the world." *ACM Trans Graph*.
  2012;31(4):65.
  - MIT CSAIL project page.
  - (`signatures/remote_vitals.py`)

- **Remote photoplethysmography (rPPG).** Verkruysse W, Svaasand
  LO, Nelson JS. "Remote plethysmographic imaging using ambient
  light." *Opt Express*. 2008;16(26):21434–45.
  - Foundation for any visible-light HR extraction without
    contact.

## 3. Shape / signature mathematics

- **Box-counting fractal dimension.** Mandelbrot BB. *The Fractal
  Geometry of Nature*. Freeman, 1982.
  - (`signatures/fractal/box_counting.py`)

- **Richardson divider method.** Richardson LF. "The problem of
  contiguity: an appendix to Statistics of Deadly Quarrels."
  *General Systems Yearbook*. 1961;6:139–87.
  - Coastline paradox; divider-step fractal estimation.
  - (`signatures/fractal/divider.py`)

- **Curvature Scale Space (CSS).** Mokhtarian F, Mackworth A.
  "Scale-based description and recognition of planar curves and
  two-dimensional shapes." *IEEE Trans Pattern Anal Mach Intell*.
  1986;8(1):34–43.
  - (`signatures/fractal/css.py`)

- **Freeman chain code.** Freeman H. "On the encoding of
  arbitrary geometric configurations." *IRE Trans Electron Comput*.
  1961;EC-10(2):260–8.
  - (`signatures/fractal/chain_code.py`)

- **Hu moments.** Hu MK. "Visual pattern recognition by moment
  invariants." *IRE Trans Inf Theory*. 1962;8(2):179–87.
  - (`matching/geometric_match.py`)

- **Fourier shape descriptors.** Zahn CT, Roskies RZ. "Fourier
  descriptors for plane closed curves." *IEEE Trans Comput*.
  1972;C-21(3):269–81.
  - (`matching/curve_descriptor.py`)

## 4. Matching and distance metrics

- **Dynamic Time Warping (DTW).** Sakoe H, Chiba S. "Dynamic
  programming algorithm optimization for spoken word recognition."
  *IEEE Trans Acoust Speech Signal Process*. 1978;26(1):43–9.
  - (`matching/dtw.py`, `matching/rotation_dtw.py`)

- **Hausdorff distance.** Huttenlocher DP, Klanderman GA,
  Rucklidge WJ. "Comparing images using the Hausdorff distance."
  *IEEE Trans Pattern Anal Mach Intell*. 1993;15(9):850–63.
  - (`matching/boundary_matcher.py`)

- **Fréchet distance.** Alt H, Godau M. "Computing the Fréchet
  distance between two polygonal curves." *Int J Comput Geom Appl*.
  1995;5(1–2):75–91.
  - (`matching/boundary_matcher.py`)

- **RANSAC.** Fischler MA, Bolles RC. "Random sample consensus: a
  paradigm for model fitting." *Commun ACM*. 1981;24(6):381–95.
  - (`matching/affine_matcher.py`)

## 5. Ranking and fusion

- **Reciprocal Rank Fusion (RRF).** Cormack GV, Clarke CLA,
  Büttcher S. "Reciprocal rank fusion outperforms Condorcet and
  individual rank learning methods." *SIGIR '09*. 2009;758–9.
  - (`scoring/rank_fusion.py`)

- **Borda count.** De Borda J-C (1781). Reprinted in McLean I,
  Urken AB. *Classics of Social Choice*. U Michigan Press, 1995.
  - (`scoring/rank_fusion.py`)

- **Otsu threshold.** Otsu N. "A threshold selection method from
  gray-level histograms." *IEEE Trans Syst Man Cybern*.
  1979;9(1):62–6.
  - (`scoring/threshold_selector.py`)

## 6. Probabilistic reasoning

- **Bayesian particle filter.** Gordon NJ, Salmond DJ, Smith AFM.
  "Novel approach to nonlinear / non-Gaussian Bayesian state
  estimation." *IEE Proc F*. 1993;140(2):107–13.
  - (`triage_reasoning/bayesian_twin.py`)

- **Effective sample size (ESS).** Kish L. *Survey Sampling*.
  Wiley, 1965. Modern usage: Liu JS. *Monte Carlo Strategies in
  Scientific Computing*. Springer, 2001.
  - (`triage_reasoning/bayesian_twin.py`, as a degeneracy flag)

- **Bayesian experimental design / expected information gain.**
  Lindley DV. "On a measure of the information provided by an
  experiment." *Ann Math Stat*. 1956;27(4):986–1005.
  - (`autonomy/active_sensing.py`)

- **Shannon entropy.** Shannon CE. "A mathematical theory of
  communication." *Bell Syst Tech J*. 1948;27(3):379–423.
  - (`triage_temporal/entropy_handoff.py`)

## 7. Distributed systems

- **Conflict-free Replicated Data Types (CRDTs).** Shapiro M,
  Preguiça N, Baquero C, Zawirski M. "Conflict-free replicated
  data types." *SSS '11*. LNCS 6976:386–400. Springer, 2011.
  - Further: Shapiro M *et al.*, INRIA TR-7687 (2011), "A
    comprehensive study of CRDTs."
  - (`state_graph/crdt_graph.py`)

- **OR-Set, LWW-Register, G-Counter** — introduced in the
  Shapiro *et al.* 2011 corpus. `state_graph/crdt_graph.py`
  implements all three.

## 8. Cryptography / data integrity

- **HMAC.** Krawczyk H, Bellare M, Canetti R. "HMAC: Keyed-
  hashing for message authentication." RFC 2104. 1997.
  - (`integrations/marker_codec.py`)

- **SHA-256.** NIST FIPS 180-4. "Secure Hash Standard (SHS)."
  2015.
  - (`integrations/marker_codec.py`)

## 9. Regulatory standards

- **IEC 62304:2006 / AMD 1:2015** — Medical device software.
  Safety-class analysis, lifecycle artefacts.
  - (`docs/REGULATORY.md §4`, `docs/SAFETY_CASE.md`)

- **ISO 14971:2019** — Application of risk management to
  medical devices.
  - (`docs/RISK_REGISTER.md`)

- **ISO 13485:2016** — Medical devices QMS.
  - (`docs/REGULATORY.md §10`)

- **IMDRF N12 (2014)** — Software as a Medical Device:
  framework for risk categorisation.
  - (`docs/REGULATORY.md §3`)

- **IMDRF / FDA / Health Canada / MHRA (2021)** — Good Machine
  Learning Practice for Medical Device Development: ten guiding
  principles.
  - (`docs/REGULATORY.md §7`)

- **FDA (2023)** — Content of Premarket Submissions for Device
  Software Functions.
  - (`docs/REGULATORY.md §5`)

- **FDA (2023)** — Cybersecurity in Medical Devices: Quality
  System Considerations.
  - (`docs/REGULATORY.md §5`, `docs/RISK_REGISTER.md SEC-*`)

- **EU MDR 2017/745** — Medical Devices Regulation.
  - (`docs/REGULATORY.md §6`)

## 10. Clinical data (external, not shipped in this repo)

- **MIMIC-III / MIMIC-IV.** Johnson AEW *et al.* "MIMIC-III, a
  freely accessible critical care database." *Sci Data*.
  2016;3:160035.
  - Reachable via the `PhysioNetRecord` adapter once a real
    archive is ingested.

- **BIDMC PPG and Respiration Dataset.** Pimentel MAF, Johnson
  AEW, Charlton PH *et al.* "Toward a robust estimation of
  respiratory rate from pulse oximeters." *IEEE Trans Biomed Eng*.
  2017;64(8):1914–23.
  - (`integrations/physionet_adapter.py`)

## 11. Software engineering practices

- **Property-based testing / QuickCheck.** Claessen K, Hughes J.
  "QuickCheck: a lightweight tool for random testing of Haskell
  programs." *ICFP '00*. 2000;268–79.
  - hypothesis (the Python port used here): MacIver D *et al.*
    (2019–). https://hypothesis.readthedocs.io
  - (`tests/test_properties.py`)

- **Mutation testing.** DeMillo RA, Lipton RJ, Sayward FG. "Hints
  on test data selection: help for the practicing programmer."
  *Computer*. 1978;11(4):34–41.
  - mutmut (Python): Hovmöller A *et al.* (2017–).
  - (`pyproject.toml [tool.mutmut]`, `docs/MUTATION_TESTING.md`)

- **CycloneDX.** OWASP CycloneDX Software Bill of Materials
  (SBOM) Standard.
  - (`scripts/generate_sbom.py`, `docs/DEPLOYMENT.md §7`)

## 12. Historical / methodological framings (no single citation)

- **C. elegans connectome.** 302 neurons, fully mapped, supports
  survival-relevant behaviour without training. Used here as a
  methodological analogue for small, auditable, hand-wired
  classifiers.
  - (`triage_reasoning/celegans_net.py`)

- **Tangram decomposition.** Ancient Chinese puzzle of stable
  geometric parts. Used here as a metaphor for body-region
  polygon decomposition.
  - (`perception/body_regions.py`)

- **Fractal recursion across scales.** The K3 matrix repeats the
  same `signal → structure → dynamics` triad at body / meaning /
  mission scales. See `docs/ARCHITECTURE.md §4`. General
  background: Barnsley MF. *Fractals Everywhere*. Academic Press,
  1988.
