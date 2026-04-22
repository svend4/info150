"""SBOM generator for triage4 (CycloneDX JSON).

Addresses the pre-deploy checklist item in ``docs/DEPLOYMENT.md §7``
and RISK_REGISTER **SEC-004** (supply-chain provenance).

The script prefers the ``cyclonedx-py`` CLI when available — that
tool reads the environment's installed distributions and emits a
compliant CycloneDX 1.5+ SBOM. When it isn't available, the script
falls back to a minimal stdlib-only SBOM derived from
``importlib.metadata``. The fallback is *not* a substitute for a
real SBOM in a regulated context but suffices for development-time
sanity checks.

Usage:
    python scripts/generate_sbom.py [--output sbom.json]

Exit codes:
    0 — SBOM written
    1 — I/O or parse error
    2 — bad invocation
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path


_COMPONENT_TYPE = "library"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _try_cyclonedx_cli(output: Path) -> bool:
    """Run the cyclonedx-py CLI if installed; return True on success."""
    if shutil.which("cyclonedx-py") is None:
        return False
    cmd = [
        "cyclonedx-py", "environment",
        "--output-format", "json",
        "--output-file", str(output),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        print(
            f"cyclonedx-py failed ({exc.returncode}): {exc.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    return True


def _fallback_sbom() -> dict:
    """Minimal CycloneDX-shaped SBOM derived from the live environment."""
    components: list[dict] = []
    for dist in sorted(metadata.distributions(), key=lambda d: d.metadata["Name"] or ""):
        name = dist.metadata["Name"]
        version = dist.version
        if not name:
            continue
        component = {
            "type": _COMPONENT_TYPE,
            "bom-ref": f"pkg:pypi/{name.lower()}@{version}",
            "name": name,
            "version": version,
            "purl": f"pkg:pypi/{name.lower()}@{version}",
        }
        license_field = dist.metadata.get("License")
        if license_field:
            component["licenses"] = [{"license": {"name": license_field[:120]}}]
        components.append(component)

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "timestamp": _now_iso(),
            "tools": [
                {
                    "vendor": "triage4",
                    "name": "generate_sbom.py (fallback)",
                    "version": "0.1.0",
                }
            ],
            "component": {
                "type": "application",
                "name": "triage4",
                "version": _triage4_version(),
                "purl": f"pkg:pypi/triage4@{_triage4_version()}",
            },
        },
        "components": components,
    }


def _triage4_version() -> str:
    try:
        return metadata.version("triage4")
    except metadata.PackageNotFoundError:
        return "0.0.0+uninstalled"


def generate(output: Path) -> Path:
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    if _try_cyclonedx_cli(output):
        print(f"SBOM written via cyclonedx-py → {output}")
        return output

    sbom = _fallback_sbom()
    output.write_text(json.dumps(sbom, indent=2) + "\n", encoding="utf-8")
    print(
        f"SBOM written via stdlib fallback → {output}  "
        f"({len(sbom['components'])} components)"
    )
    print(
        "note: for regulated deploys, install 'cyclonedx-bom' and re-run.",
        file=sys.stderr,
    )
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a CycloneDX SBOM.")
    parser.add_argument(
        "--output", "-o",
        default="sbom.json",
        help="output file path (default: sbom.json)",
    )
    args = parser.parse_args(argv)
    try:
        generate(Path(args.output))
    except OSError as exc:
        print(f"I/O error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
