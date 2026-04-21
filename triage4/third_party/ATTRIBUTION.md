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
| `svend4/in4n` · `2-react/src/components/SemanticZoom.jsx` | `triage4/web_ui/src/components/SemanticZoom.tsx` | Ported to TypeScript. Upstream shows a knowledge-graph node popup; triage4 uses the same fade-by-distance card to show a casualty's priority/confidence when the operator hovers over their marker on the tactical map. |
| `svend4/in4n` · `2-react/src/components/InfoPanel.jsx` | `triage4/web_ui/src/components/InfoPanel.tsx` | Ported to TypeScript. Upstream shows current/target graph node and era slider; triage4 reuses the frame to show current casualty, handoff target, and mission-replay frame. |

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
