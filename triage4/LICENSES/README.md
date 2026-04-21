# Upstream licenses

`triage4` adapts small subsets of three upstream projects:

| Upstream | Declared license | Status |
|---|---|---|
| [`svend4/meta2`](https://github.com/svend4/meta2) | MIT (in `pyproject.toml`) | Adapted — see `meta2.LICENSE` |
| [`svend4/infom`](https://github.com/svend4/infom) | not declared | Inspiration only — no direct code copy |
| [`svend4/in4n`](https://github.com/svend4/in4n) | not declared | Inspiration only — no direct code copy |

At the time of adaptation none of the upstream repositories ship a dedicated
`LICENSE` file. `meta2` declares MIT via its `pyproject.toml`, so the
relevant portions of adapted code in `triage4/signatures/fractal/` are
covered by `meta2.LICENSE` with standard MIT terms.

If and when `infom` or `in4n` adopt an explicit license, any code actually
copied into triage4 should be accompanied by a new LICENSE file in this
directory plus a header in the affected source files.

See `third_party/ATTRIBUTION.md` for the mapping between upstream files
and triage4 modules.
