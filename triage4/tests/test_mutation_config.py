"""Sanity checks for the mutmut configuration.

Does NOT run mutmut itself — that takes 5–15 min and is opt-in.
Just verifies that the config in pyproject.toml is well-formed and
points at paths that still exist.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib


_REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_pyproject() -> dict:
    return tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_mutmut_config_exists():
    cfg = _load_pyproject().get("tool", {}).get("mutmut")
    assert cfg is not None, "pyproject.toml missing [tool.mutmut] section"


def test_mutmut_scope_paths_all_exist():
    cfg = _load_pyproject()["tool"]["mutmut"]
    raw = cfg["paths_to_mutate"]
    paths = [p.strip() for p in raw.split(",") if p.strip()]
    assert paths, "paths_to_mutate must declare at least one path"
    for rel in paths:
        assert (_REPO_ROOT / rel).exists(), f"mutmut target missing: {rel}"


def test_mutmut_scope_covers_mortal_sign_override():
    """Score fusion is the mortal-sign override site — MUST be in scope."""
    cfg = _load_pyproject()["tool"]["mutmut"]
    assert "triage_reasoning/score_fusion.py" in cfg["paths_to_mutate"]


def test_mutmut_extra_dep_declared():
    cfg = _load_pyproject()
    extras = cfg["project"]["optional-dependencies"]
    assert "mutation" in extras
    assert any("mutmut" in dep for dep in extras["mutation"])


def test_mutation_runner_script_exists():
    script = _REPO_ROOT / "scripts" / "run_mutation.sh"
    assert script.exists()


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="NTFS has no POSIX executable bit; chmod +x is Unix-only",
)
def test_mutation_runner_script_is_executable_on_posix():
    script = _REPO_ROOT / "scripts" / "run_mutation.sh"
    # Readable by anyone, executable by owner at least.
    assert script.stat().st_mode & 0o100
