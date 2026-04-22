"""Tests for scripts/generate_sbom.py.

Exercises the stdlib fallback path (which always works in CI).
The cyclonedx-py CLI path is not exercised because the tool isn't
a hard dep; a successful invocation implies the fallback never
runs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from generate_sbom import _fallback_sbom, generate, main  # noqa: E402


def test_fallback_sbom_has_required_cyclonedx_fields():
    sbom = _fallback_sbom()
    assert sbom["bomFormat"] == "CycloneDX"
    assert sbom["specVersion"].startswith("1.")
    assert "metadata" in sbom
    assert "components" in sbom
    assert isinstance(sbom["components"], list)


def test_fallback_sbom_lists_numpy_and_scipy():
    sbom = _fallback_sbom()
    names = {c["name"].lower() for c in sbom["components"]}
    assert "numpy" in names
    assert "scipy" in names


def test_fallback_sbom_components_have_purl():
    sbom = _fallback_sbom()
    for c in sbom["components"]:
        assert c["purl"].startswith("pkg:pypi/")
        assert "@" in c["purl"]


def test_generate_writes_valid_json(tmp_path):
    out = tmp_path / "sbom.json"
    result = generate(out)
    assert result.exists()
    data = json.loads(result.read_text())
    assert data["bomFormat"] == "CycloneDX"


def test_main_exits_zero_with_default_args(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc = main(["--output", "sbom_test.json"])
    assert rc == 0
    assert (tmp_path / "sbom_test.json").exists()
