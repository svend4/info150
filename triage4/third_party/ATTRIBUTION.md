# Third-party attribution

`triage4` is self-contained. It does **not** depend on `svend4/meta2`,
`svend4/infom` or `svend4/in4n` at runtime. However, several files contain
adapted source from those upstream projects, retrieved directly from their
public GitHub repositories. License status is tracked in `LICENSES/README.md`.

## Real code adaptation

| Upstream path | triage4 path | How it was adapted |
|---|---|---|
| `svend4/meta2` · `puzzle_reconstruction/algorithms/fractal/box_counting.py` | `triage4/signatures/fractal/box_counting.py` | Copied verbatim, wrapped with an OO facade (`BoxCountingFD`), added `mask_to_contour` helper so triage4 callers can feed binary masks. Upstream Russian docstrings preserved for traceability. |
| `svend4/meta2` · `puzzle_reconstruction/algorithms/fractal/divider.py` | `triage4/signatures/fractal/divider.py` | Copied verbatim, wrapped with `RichardsonDivider`, added `signal_to_contour` so 1D triage signals (chest-motion curve etc.) become `(i, v)` polylines that the compass algorithm can walk. |
| `svend4/meta2` · `puzzle_reconstruction/algorithms/fractal/css.py` | `triage4/signatures/fractal/css.py`, `triage4/signatures/fractal/chain_code.py` | Curvature-Scale-Space functions copied verbatim. Freeman chain-code was originally inside `css.py`; split into its own file for triage4. |
| `svend4/meta2` · `puzzle_reconstruction/matching/dtw.py` | `triage4/matching/dtw.py` | Copied verbatim. Upstream compares torn-document edge curves; triage4 uses the same DTW to compare temporal triage signals (chest-motion, perfusion) across frames. Added convenience unwrap so plain 1D signals are auto-reshaped. |
| `svend4/meta2` · `puzzle_reconstruction/matching/score_combiner.py` | `triage4/matching/score_combiner.py` | Copied verbatim: `ScoreVector`, `CombinedScore`, `weighted_combine`, `min_combine`, `max_combine`, `rank_combine`, `normalize_score_vectors`, `batch_combine`. Error messages translated to English; semantics unchanged. |
| `svend4/meta2` · `puzzle_reconstruction/matching/matcher_registry.py` | `triage4/matching/matcher_registry.py` | Registry pattern (`@register` decorator, `register_fn`, `get_matcher`, `list_matchers`, `compute_scores`) ported with the same names. The default meta2 matcher bootstrap was dropped — triage4 registers its own matchers as they appear. |
| `svend4/meta2` · `puzzle_reconstruction/matching/boundary_matcher.py` | `triage4/matching/boundary_matcher.py`, `triage4/matching/shape_match.py` | Copied verbatim: `BoundaryMatch`, `extract_boundary_points`, `hausdorff_distance`, `chamfer_distance`, `frechet_approx`, `score_boundary_pair`, `match_boundary_pair`, `batch_match_boundaries`. Added triage-friendly `shape_match.py` wrapper without the 4-sides bbox concept (for wound boundaries and posture silhouettes). |
| `svend4/infom` · `visualizer/html.py` (pattern only) | `triage4/ui/html_export.py` | Adopted the "serialise-domain-graph-and-embed-in-a-D3-template" pattern. Upstream targets a KnowledgeMap (hex sigs, heptagrams, fractal borders); triage4 writes a one-file SVG dashboard for the `CasualtyGraph` from scratch. No code copied. Exposed via the `GET /export.html` FastAPI route. |
| `svend4/meta2` · `puzzle_reconstruction/matching/candidate_ranker.py` | `triage4/matching/candidate_ranker.py` | Copied verbatim: `CandidatePair`, `score_pair`, `rank_pairs`, `filter_by_score`, `deduplicate_pairs`, `top_k`, `batch_rank`. Used in triage4 to rank casualty↔medic and robot↔casualty assignment candidates. Error strings translated to English. |
| `svend4/meta2` · `puzzle_reconstruction/matching/score_normalizer.py` | `triage4/matching/score_normalizer.py` | Copied verbatim: `ScoreNormResult`, `normalize_minmax`, `normalize_zscore`, `normalize_rank`, `calibrate_scores`, `combine_scores`, `normalize_score_matrix`, `batch_normalize_scores`. Used to bring diverse signature scores onto a comparable scale before weighted fusion. |
| `svend4/in4n` · `2-react/src/App.jsx` (BFS function only) | `triage4/autonomy/route_planner.py` | The ``bfsPath`` textbook BFS function ported to Python as `bfs_path` plus `all_shortest_paths` and `plan_robot_route`. Uses the mission graph to compute shortest-hop routes between robots and casualties. |
| `svend4/in4n` · `2-react/src/components/SemanticZoom.jsx` | `triage4/web_ui/src/components/SemanticZoom.tsx` | Ported to TypeScript. Upstream shows a knowledge-graph node popup; triage4 uses the same fade-by-distance card to show a casualty's priority/confidence when the operator hovers over their marker on the tactical map. |
| `svend4/in4n` · `2-react/src/components/InfoPanel.jsx` | `triage4/web_ui/src/components/InfoPanel.tsx` | Ported to TypeScript. Upstream shows current/target graph node and era slider; triage4 reuses the frame to show current casualty, handoff target, and mission-replay frame. |
| `svend4/meta2` · `puzzle_reconstruction/matching/geometric_match.py` | `triage4/matching/geometric_match.py` | Similarity functions (`aspect_ratio_similarity`, `area_ratio_similarity`, `hu_moments_similarity`, `edge_length_similarity`, `match_geometry`, `batch_geometry_match`) copied verbatim. The upstream `compute_fragment_geometry(mask)` uses OpenCV; triage4 replaces it with a pure-numpy `compute_geometry_from_contour((N,2))` that computes the same properties (area via shoelace, convex hull via monotone chain, Hu moments in pure numpy) so we don't pull in OpenCV. |
| `svend4/infom` · `signatures/heptagram.py` | `triage4/signatures/radar/heptagram.py` | Copied verbatim. 7-axis radar descriptor (strength/direction/temporal/confidence/scale/context/source). Pure stdlib, no external deps. |
| `svend4/infom` · `signatures/octagram.py` | `triage4/signatures/radar/octagram.py` | Copied verbatim. 8-direction 3D compass descriptor with SkeletonType auto-detection and helpers for shell/tower octagrams. Pure stdlib. |
| `svend4/meta2` · `puzzle_reconstruction/scoring/threshold_selector.py` | `triage4/scoring/threshold_selector.py` | Copied verbatim: `ThresholdConfig`, `ThresholdResult`, fixed / percentile / Otsu / F-beta / adaptive strategies + `apply_threshold`, `batch_select_thresholds`. Used in triage4 to auto-calibrate priority cut-offs when the score distribution shifts. Error strings translated to English. |
| `svend4/meta2` · `puzzle_reconstruction/matching/pair_scorer.py` | `triage4/matching/pair_scorer.py` | Copied verbatim: `ScoringWeights` (color/texture/geometry/gradient), `PairScoreResult` with `dominant_channel`/`is_strong_match`, `aggregate_channels`, `score_pair`, `select_top_pairs`, `build_score_matrix`, `batch_score_pairs`. The module's `score_pair` is re-exported as `score_pair_channels` to avoid a name clash with candidate_ranker's `score_pair`. |
| `svend4/meta2` · `puzzle_reconstruction/scoring/rank_fusion.py` | `triage4/scoring/rank_fusion.py` | Copied verbatim: `normalize_scores`, `reciprocal_rank_fusion` (RRF), `borda_count`, `score_fusion`, `fuse_rankings`. Classic ensemble rank-combination — used in triage4 when several independent scorers each rank casualties and a consensus ordering is needed. Error strings translated to English. |
| `svend4/meta2` · `puzzle_reconstruction/scoring/evidence_aggregator.py` | `triage4/scoring/evidence_aggregator.py` | Copied verbatim: `EvidenceConfig`, `EvidenceScore` with `dominant_channel`/`is_confident`, `weight_evidence`, `threshold_evidence`, `compute_confidence`, `aggregate_evidence`, `rank_by_evidence`, `batch_aggregate`. Per-channel thresholding + weighting + confidence in one piece. |
| `svend4/meta2` · `puzzle_reconstruction/matching/curve_descriptor.py` | `triage4/matching/curve_descriptor.py` | Copied verbatim: `CurveDescriptorConfig`, `CurveDescriptor`, `compute_fourier_descriptor`, `compute_curvature_profile`, `describe_curve`, `descriptor_distance`, `descriptor_similarity`, `batch_describe_curves`, `find_best_match`. Used in triage4 to compare wound/posture contours and chest-motion polylines with translation/rotation/scale invariance. Error strings translated to English. |
| `svend4/meta2` · `puzzle_reconstruction/scoring/pair_ranker.py` | `triage4/scoring/pair_ranker.py` | Copied verbatim: `RankConfig`, `RankedPair`, `RankResult` (with `compression_ratio` / `top_pair`), `compute_pair_score`, `rank_pairs`, `build_rank_matrix`, `merge_rank_results`. Re-exported as `rank_pairs_detailed` at the package level to avoid clashing with `candidate_ranker.rank_pairs`. |
| `svend4/infom` · `signatures/hexsig.py` | `triage4/signatures/radar/hexsig.py` | Copied verbatim (pure stdlib): Q6 hypercube operations — bit packing, Hamming distance, BFS shortest paths, Voronoi partition, Delaunay graph, greedy sphere packing, embedding → Q6 projection. `median` is re-exported as `hex_median` to avoid shadowing the builtin. |
| `svend4/meta2` · `puzzle_reconstruction/matching/rotation_dtw.py` | `triage4/matching/rotation_dtw.py` | Copied verbatim: `RotationDTWResult`, `_resample_curve`, `_rotate_curve`, `_mirror_curve`, `rotation_dtw`, `rotation_dtw_similarity`, `batch_rotation_dtw`. Imports triage4's own `dtw_distance` from `.dtw`. Used to compare wound boundaries and posture polylines under any rotation (and optional mirror). |
| `svend4/meta2` · `puzzle_reconstruction/scoring/consistency_checker.py` | `triage4/scoring/consistency_checker.py` | Copied verbatim: `ConsistencyIssue`, `ConsistencyReport`, `check_unique_ids`, `check_all_present`, `check_canvas_bounds`, `check_score_threshold`, `check_gap_uniformity`, `run_consistency_check`, `batch_consistency_check`. Error strings translated to English. A triage-facing wrapper (`state_graph/graph_consistency.py`) uses this machinery for CasualtyGraph / MissionGraph validation (orphan edges, low confidence, double medic handoff, immediate without handoff). |
| `svend4/meta2` · `puzzle_reconstruction/matching/affine_matcher.py` | `triage4/matching/affine_matcher.py` | Geometry-only subset ported. Upstream uses OpenCV's ORB + BFMatcher + `cv2.estimateAffine2D`. triage4 keeps `AffineMatchResult`, `estimate_affine` (pure-numpy RANSAC + `np.linalg.lstsq` refinement instead of cv2), `apply_affine_pts`, `affine_reprojection_error`, `score_affine_match`. The image-level pipeline (`match_fragments_affine`, `batch_affine_match`) is intentionally left out — replaced by `match_points_affine(pts1, pts2)` for cases where callers already have point correspondences. |
| `svend4/meta2` · `puzzle_reconstruction/scoring/pair_filter.py` | `triage4/scoring/pair_filter.py` | Copied verbatim: `FilterConfig`, `CandidatePair` (with n_inliers / rank), `FilterReport`, `filter_by_score`, `filter_by_inlier_count`, `filter_top_k`, `deduplicate_pairs`, `filter_top_k_per_fragment`, `filter_pairs`, `merge_filter_results`, `batch_filter`. The dataclass and two helpers clash by name with `candidate_ranker`, so at the package level they're re-exported as `FilterCandidatePair`, `dedup_filter_pairs`, `filter_by_score_threshold`. Error strings translated. |

IFS (iterated-function-system) fractals from upstream were deliberately left
out — triage4 does not need fractal code-book reconstruction and skipping
them keeps the dependency surface smaller.

## Idea-level inspiration (no direct code)

- **`svend4/infom`** — event log with causal edges and named snapshots, as
  used in `triage4/state_graph/evidence_memory.py`. The upstream indexer
  (`indexer.py`, `graphrag_query.py`) operates on text via an LLM adapter,
  which is out of scope for triage. Only the *shape* of the memory model
  (events + causal links + snapshots) was ported, written from scratch.
- **`svend4/in4n`** — the force-graph export contract in
  `triage4/integrations/in4n_adapter.py` is compatible with what the
  upstream React app expects (`react-force-graph`, `three.js`). The
  renderer, BFS-traveler and Voronoi terrain overlay stay on the frontend
  side and are not ported.

## Dependencies pulled in by the adaptation

Porting the real fractal code introduced two mainstream scientific-Python
dependencies, declared in `pyproject.toml`:

- `numpy` — used by box-counting and divider;
- `scipy` — used by CSS for `scipy.ndimage.gaussian_filter1d`.

These are **public PyPI packages**, not the three upstream repositories, so
triage4 remains a single installable project.

## How to verify independence

```bash
grep -R "^import\s\+\(meta2\|infom\|in4n\)" triage4/   # must be empty
grep -R "^from\s\+\(meta2\|infom\|in4n\)"   triage4/   # must be empty
python -c "import pkgutil, importlib, triage4, sys; \
  [importlib.import_module(n) for _, n, _ in pkgutil.walk_packages(triage4.__path__, 'triage4.')]; \
  assert not any(m.startswith(('meta2.','infom.','in4n.')) for m in sys.modules)"
pytest -q
```
