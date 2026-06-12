#!/usr/bin/env python3
"""detect_stack.py - is this project actually in the PyPSA domain?

Suite-level domain guard. Run BEFORE applying any pypsa-* skill when the
modeling stack is ambiguous (user said "plot my results" / "check my model"
without naming a tool).

Usage:
    python detect_stack.py [project_dir]      # default: cwd

Exit codes:
    0 = PyPSA domain (incl. mixed stacks that contain PyPSA - stdout says which)
    2 = a different stack detected, no PyPSA - pypsa-* skills do NOT apply
    3 = ambiguous (nothing recognized, or weak signals only) - ask the user

A verdict of 0/2 requires at least one STRONG marker; weak signals
(.nc files, linopy/atlite imports) alone always yield 3.
Stdlib only; never imports anything from the target project.
"""
from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path

# Evidence tables map stack name -> list of human-readable evidence strings.
Evidence = dict[str, list[str]]

EXIT_PYPSA = 0
EXIT_OTHER_STACK = 2
EXIT_AMBIGUOUS = 3

# STRONG code markers: searched in source files; one hit decides the stack.
CODE_MARKERS = {
    "pypsa": [r"\bimport pypsa\b", r"\bfrom pypsa\b", r"\bpypsa\.Network\b",
              r"pypsa-eur"],
    "pandapower": [r"\bimport pandapower\b", r"\bfrom pandapower\b",
                   r"\bpp\.runpp\b"],
    "pss/e": [r"\bimport psspy\b", r"\bpsspy\."],
    "powerworld": [r"\bimport esa\b", r"\bSimAuto\b"],
    "opendss": [r"\bimport opendssdirect\b", r"\bdss\.Command\b"],
    "andes": [r"\bimport andes\b"],
    "matpower": [r"\bmpc\.bus\b", r"\bmpc\.gen\b"],   # only meaningful in .m
    "gridlab-d": [r"\bobject\s+(node|load|overhead_line)\b"],  # .glm syntax
}
# STRONG manifest markers: searched ONLY in dependency manifests (line-anchored
# package names would false-positive on prose in source files).
MANIFEST_MARKERS = {
    "pypsa": [r"^\s*pypsa\b", r'"pypsa[">=~]'],
    "pandapower": [r"^\s*pandapower\b", r'"pandapower[">=~]'],
    "andes": [r"^\s*andes\b"],
}
# WEAK signals: suggestive, never sufficient for a verdict on their own.
WEAK_MARKERS = {
    "pypsa": [r"\bimport linopy\b", r"\bimport atlite\b",
              r"\bpowerplantmatching\b"],
}

SOURCE_GLOBS = ["*.py", "*.ipynb", "Snakefile", "*.smk", "*.m", "*.glm"]
MANIFEST_GLOBS = ["requirements*.txt", "pyproject.toml", "environment.y*ml",
                  "setup.py", "setup.cfg", "Pipfile"]
SKIP_PARTS = ("node_modules", "venv", ".venv", "__pycache__")
MAX_FILES = 400
MAX_BYTES = 400_000
MAX_EVIDENCE_SHOWN = 4
MAX_NC_SAMPLED = 5

# matpower/gridlab-d markers only count inside their native file types -
# mentions inside Python text are prose, not usage.
NATIVE_ONLY = {"matpower": {".m"}, "gridlab-d": {".glm"}}

_CODE_PATTERNS = {stack: [re.compile(m, re.MULTILINE) for m in markers]
                  for stack, markers in CODE_MARKERS.items()}
_WEAK_PATTERNS = {stack: [re.compile(m) for m in markers]
                  for stack, markers in WEAK_MARKERS.items()}
_MANIFEST_PATTERNS = {stack: [re.compile(m, re.MULTILINE | re.IGNORECASE)
                              for m in markers]
                      for stack, markers in MANIFEST_MARKERS.items()}


def _skip(p: Path) -> bool:
    return any(part.startswith(".") or part in SKIP_PARTS for part in p.parts)


def _iter_files(root: Path, globs: list[str]) -> Iterator[Path]:
    seen = 0
    for pattern in globs:
        for p in root.rglob(pattern):
            if _skip(p.relative_to(root)):
                continue
            yield p
            seen += 1
            if seen >= MAX_FILES:
                return


def _read(f: Path) -> str:
    try:
        text = f.read_text(errors="ignore")[:MAX_BYTES]
    except OSError:
        return ""
    if f.suffix == ".ipynb":  # cells only, skip outputs noise
        try:
            nb = json.loads(text)
            text = "\n".join("".join(c.get("source", []))
                             for c in nb.get("cells", []))
        except (json.JSONDecodeError, TypeError):
            pass
    return text


def _hit(table: Evidence, stack: str, evidence: str) -> None:
    table.setdefault(stack, []).append(evidence)


def _scan_manifests(root: Path, strong: Evidence) -> None:
    for f in _iter_files(root, MANIFEST_GLOBS):
        text = _read(f)
        for stack, patterns in _MANIFEST_PATTERNS.items():
            if any(p.search(text) for p in patterns):
                _hit(strong, stack, f"{f.relative_to(root)} (manifest)")


def _scan_sources(root: Path, strong: Evidence, weak: Evidence) -> None:
    for f in _iter_files(root, SOURCE_GLOBS):
        text = _read(f)
        for stack, patterns in _CODE_PATTERNS.items():
            native = NATIVE_ONLY.get(stack)
            if native and f.suffix not in native:
                continue
            for p in patterns:
                if p.search(text):
                    _hit(strong, stack, f"{f.relative_to(root)}: {p.pattern}")
                    break
        for stack, patterns in _WEAK_PATTERNS.items():
            for p in patterns:
                if p.search(text):
                    _hit(weak, stack,
                         f"{f.relative_to(root)}: {p.pattern} (weak)")
                    break


def _note_nc_files(root: Path, weak: Evidence) -> None:
    nc = [p for p in root.rglob("*.nc")
          if not _skip(p.relative_to(root))][:MAX_NC_SAMPLED]
    if nc:
        _hit(weak, "pypsa", f"{len(nc)} .nc file(s), e.g. {nc[0].name} (weak)")


def detect(root: Path) -> tuple[Evidence, Evidence]:
    """Collect strong and weak stack evidence found under `root`."""
    strong: Evidence = {}
    weak: Evidence = {}
    # manifests FIRST - highest-precision signal, must survive MAX_FILES cap
    _scan_manifests(root, strong)
    _scan_sources(root, strong, weak)
    _note_nc_files(root, weak)
    return strong, weak


def _print_evidence(strong: Evidence, weak: Evidence) -> None:
    for label, table in [("strong", strong), ("weak", weak)]:
        for stack, evidence in sorted(table.items()):
            print(f"[{stack}] {len(evidence)} {label} marker(s)")
            for e in evidence[:MAX_EVIDENCE_SHOWN]:
                print(f"    {e}")


def _has_snakemake_workflow(root: Path) -> bool:
    return ((root / "Snakefile").exists() or (root / "rules").is_dir()
            or any(not _skip(p.relative_to(root)) for p in root.rglob("*.smk")))


def _verdict(root: Path, strong: Evidence, weak: Evidence) -> int:
    """Print the verdict line(s) and return the exit code (0 / 2 / 3)."""
    others = {s for s in strong if s != "pypsa"}
    if "pypsa" in strong and _has_snakemake_workflow(root):
        print("\nNOTE: Snakemake workflow detected (PyPSA-Eur/Earth-style) -> "
              "config-first discipline; never hand-edit generated networks. "
              "READ pypsa-network-modeling/references/framework-workflows.md.")
    if "pypsa" in strong and not others:
        print("\nVERDICT: PyPSA domain - this suite applies.")
        return EXIT_PYPSA
    if "pypsa" in strong:
        print(f"\nVERDICT: mixed stacks (pypsa + {', '.join(sorted(others))}) "
              "- apply pypsa-* skills to the PyPSA parts only; do not apply "
              "PyPSA conventions to the other tool's files.")
        return EXIT_PYPSA
    if others:
        print(f"\nVERDICT: different stack detected ({', '.join(sorted(others))})"
              " - the pypsa-* skills do NOT apply. Route to that tool's own "
              "skills/docs (e.g. PowerSkills covers pandapower/PSS-E/"
              "PowerWorld/OpenDSS/ANDES).")
        return EXIT_OTHER_STACK
    if weak:
        print("\nVERDICT: weak signals only "
              f"({', '.join(sorted(weak))}) - not sufficient. "
              "ASK the user which tool they use before applying any skill.")
        return EXIT_AMBIGUOUS
    print("\nVERDICT: ambiguous - no recognized power-systems stack found. "
          "ASK the user which tool they use before applying any skill.")
    return EXIT_AMBIGUOUS


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not root.is_dir():
        print(f"not a directory: {root}")
        return EXIT_AMBIGUOUS
    strong, weak = detect(root)
    _print_evidence(strong, weak)
    return _verdict(root, strong, weak)


if __name__ == "__main__":
    sys.exit(main())
