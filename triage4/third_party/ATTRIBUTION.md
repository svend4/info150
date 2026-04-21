# Third-party attribution

`triage4` is self-contained and does not depend on any external
`svend4/meta2`, `svend4/infom` or `svend4/in4n` package at runtime. However,
several modules are adapted from ideas and API shapes described in those
upstream projects. The table below tracks what was adapted, where, and why.

| Upstream | triage4 location | Adaptation |
|---|---|---|
| `meta2.signatures.fractal` (box-counting, divider/Richardson, IFS, CSS, chain-code) | `triage4/signatures/fractal/box_counting.py`, `triage4/signatures/fractal/richardson.py`, `triage4/signatures/fractal_motion.py` | Kept only box-counting and Richardson-divider. Rewritten in pure Python (no NumPy), narrowed to casualty signals (chest-motion curve, wound-boundary mask, thermal-anomaly texture). Renamed classes from `FractalSignature` / `EdgeSignature` vocabulary to motion-/wound-centric names. |
| `infom` knowledge-graph with memory, GraphRAG, snapshots, causal links | `triage4/state_graph/evidence_memory.py`, `triage4/integrations/infom_adapter.py` | Kept only event log + causal edges + named snapshots. Dropped GraphRAG retrieval and agent memory — triage4 needs audit trail, not retrieval. Narrowed events to triage kinds (detection, signature, assessment, handoff, revisit). |
| `in4n` force-graph visualization (`react-force-graph`, `three.js`, BFS-traveler, hyperbolic mode) | `triage4/integrations/in4n_adapter.py` | Kept only the JSON export contract (`{nodes, links}` with group/val/color/strength). Dropped the React renderer, BFS-traveler and hyperbolic layout — those stay on the front-end side. Color palette matches triage priority, not knowledge-community. |

## License posture

When a real upstream release becomes available and a direct code drop is
performed, preserve the upstream LICENSE file and add a `LICENSES/` folder:

```
LICENSES/
  meta2.LICENSE
  infom.LICENSE
  in4n.LICENSE
```

Until then, the adaptations above are **clean-room reimplementations** based
on the architectural descriptions in the project drafts, and are covered by
triage4's own MIT license.

## How to verify independence

```bash
grep -R "^import\s\+\(meta2\|infom\|in4n\)" triage4/    # must be empty
grep -R "^from\s\+\(meta2\|infom\|in4n\)"   triage4/    # must be empty
python -c "import pkgutil, importlib, triage4; \
  [importlib.import_module(n) for _, n, _ in pkgutil.walk_packages(triage4.__path__, 'triage4.')]; \
  import sys; \
  assert not any(m.startswith(('meta2.','infom.','in4n.')) for m in sys.modules)"
pytest -q
```
