"""Claims-lint for triage4 (RISK_REGISTER CLAIM-001).

Scans user-facing text for words that carry regulatory weight
("diagnose", "treat", "medical device", "FDA-cleared", ...). A hit
in user-facing copy is a compliance bug; a hit inside the regulatory
discussion (REGULATORY.md, RISK_REGISTER.md, SAFETY_CASE.md) is
expected and explicitly allow-listed.

Exit codes:
    0 — no violations
    1 — one or more violations (details printed to stderr)
    2 — bad invocation

Run from the project root:

    python scripts/claims_lint.py
"""

from __future__ import annotations

import ast
import re
import sys
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path


# Forbidden patterns. Each targets a *framing claim* — something a
# user-facing page would say about triage4 or its peers that would
# carry regulatory weight. Bare English verbs ("we treat X as Y")
# are NOT matched; only product-claim phrasing is.
_FORBIDDEN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # Broad — "diagnose" is almost always a clinical claim.
    ("diagnose",         re.compile(r"\bdiagnos(e|es|is|tic|ing|ed)\b", re.IGNORECASE)),
    ("cure",             re.compile(r"\bcures?\s+(patients?|casualt(y|ies)|wounds?|injur(y|ies))\b", re.IGNORECASE)),
    # Product-as-medical-device claims.
    ("medical device",   re.compile(r"\b(is|are|as)\s+(a\s+|an\s+)?medical[\s\-]+devices?\b", re.IGNORECASE)),
    ("FDA-cleared",      re.compile(r"\bFDA[\s\-]+(clear|approv)(ed|al)\b", re.IGNORECASE)),
    ("CE-marked",        re.compile(r"\bCE[\s\-]+mark(ed|ing)\b", re.IGNORECASE)),
    ("clinically proven", re.compile(r"\bclinical(ly)?[\s\-]+(proven|validated)\b", re.IGNORECASE)),
    # Product action claims: "triage4 can treat", "the system diagnoses", ...
    (
        "product claim",
        re.compile(
            r"\b(triage4?|the\s+(system|stack|tool|product|software))\s+"
            r"(can|will|does|is\s+able\s+to|is\s+designed\s+to)\s+"
            r"(treat|cure|heal|prescribe|administer)\b",
            re.IGNORECASE,
        ),
    ),
]


# Files that explicitly *discuss* the forbidden words (regulatory
# context). They are expected to contain them and are skipped.
_ALLOWLIST_FILES = {
    "docs/REGULATORY.md",
    "docs/RISK_REGISTER.md",
    "docs/SAFETY_CASE.md",
    "docs/STATUS.md",                        # meta-discusses the lint
    "docs/FURTHER_READING.md",               # cites the standards by name
    "scripts/claims_lint.py",                # the script itself
    "tests/test_claims_lint.py",             # the test for the script
}


# Docstrings that legitimately explain what is being forbidden (the
# ``decision-support`` framing comment in a module, for example).
# Matched by a leading "[claims-lint: allow]" marker on the same
# docstring, kept minimal to avoid abuse.
_INLINE_ALLOW_MARKER = "[claims-lint: allow]"


@dataclass
class Finding:
    path: str
    line: int
    term: str
    excerpt: str

    def format(self) -> str:
        return f"{self.path}:{self.line}: forbidden term {self.term!r} — {self.excerpt.strip()!r}"


def _iter_markdown_files(root: Path) -> Iterator[Path]:
    for p in root.rglob("*.md"):
        rel = p.relative_to(root).as_posix()
        if rel in _ALLOWLIST_FILES:
            continue
        if any(part in {".git", "node_modules", "build", "dist"} for part in p.parts):
            continue
        yield p


def _iter_python_docstrings(
    root: Path,
) -> Iterator[tuple[Path, int, str]]:
    for p in root.rglob("*.py"):
        rel = p.relative_to(root).as_posix()
        if rel in _ALLOWLIST_FILES:
            continue
        if any(part in {".git", "build", "dist", ".venv", "venv"} for part in p.parts):
            continue
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue

        # Module-level docstring.
        module_doc = ast.get_docstring(tree)
        if module_doc:
            yield p, 1, module_doc

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                doc = ast.get_docstring(node)
                if doc:
                    yield p, node.lineno, doc


def _scan_text(text: str, path: Path, start_line: int = 1) -> Iterator[Finding]:
    for lineno_offset, line in enumerate(text.splitlines()):
        # Skip lines that opt out.
        if _INLINE_ALLOW_MARKER in line:
            continue
        for term, pattern in _FORBIDDEN_PATTERNS:
            if pattern.search(line):
                yield Finding(
                    path=str(path),
                    line=start_line + lineno_offset,
                    term=term,
                    excerpt=line,
                )


def scan(root: Path | None = None) -> list[Finding]:
    root = root or Path(__file__).resolve().parent.parent
    findings: list[Finding] = []

    for md in _iter_markdown_files(root):
        text = md.read_text(encoding="utf-8")
        rel = md.relative_to(root)
        findings.extend(_scan_text(text, rel))

    for py, lineno, doc in _iter_python_docstrings(root):
        rel = py.relative_to(root)
        findings.extend(_scan_text(doc, rel, start_line=lineno))

    return findings


def main(argv: Iterable[str] | None = None) -> int:
    argv = list(argv) if argv is not None else sys.argv[1:]
    if argv:
        print("usage: claims_lint.py", file=sys.stderr)
        return 2

    findings = scan()
    if not findings:
        print("claims-lint: OK — no forbidden terms found in user-facing copy.")
        return 0

    print(f"claims-lint: {len(findings)} violation(s):", file=sys.stderr)
    for f in findings:
        print(f"  {f.format()}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
