#!/usr/bin/env python3
"""test_scripts.py - suite-level smoke test for every bundled script.

Usage:
    python test_scripts.py            # full run (needs pypsa + highs)
    python test_scripts.py --compile  # compile-check only, no deps

Checks:
1. every */scripts/*.py and detect_stack.py compiles (py_compile)
2. detect_stack.py classifies a synthetic pypsa dir and a pandapower dir
3. with pypsa installed: build + solve a small network, then
   - validate_network.py reports 0 ERRORs on it
   - standard_plots.py renders >= 6 figures from it
4. the fenced recipes in generic-patterns.md execute against a toy model

Exit nonzero on any failure. Run before every release/commit.
"""
from __future__ import annotations

import py_compile
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FAILURES: list[str] = []

MIN_FIGURES = 6
EXPECTED_RECIPE_COUNT = 3
EXPECTED_CONSTRAINTS = ("custom-co2-cumulative", "custom-reserve-margin",
                        "custom-h2-ratio")


def check(label: str, ok: bool, detail: str = "") -> None:
    """Print a PASS/FAIL line and record failures for the exit code."""
    print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f"  ({detail})" if detail else ""))
    if not ok:
        FAILURES.append(label)


def run_script(script: Path, *args: str,
               cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run a bundled script in a subprocess, capturing its output."""
    return subprocess.run([sys.executable, str(script), *args],
                          capture_output=True, text=True,
                          cwd=str(cwd) if cwd else None)


def last_stdout_line(r: subprocess.CompletedProcess[str],
                     fallback: str = "") -> str:
    return r.stdout.strip().splitlines()[-1] if r.stdout else fallback


def compile_all() -> None:
    scripts = sorted(ROOT.glob("*/scripts/*.py")) + [ROOT / "detect_stack.py",
                                                     ROOT / "test_scripts.py"]
    with tempfile.TemporaryDirectory() as td:  # keep bytecode out of the repo
        for i, s in enumerate(scripts):
            try:
                py_compile.compile(str(s), cfile=f"{td}/{i}.pyc", doraise=True)
                check(f"compile {s.relative_to(ROOT)}", True)
            except py_compile.PyCompileError as e:
                check(f"compile {s.relative_to(ROOT)}", False, str(e))


def run_detect_stack_on(filename: str,
                        code: str) -> subprocess.CompletedProcess[str]:
    """Run detect_stack.py on a temp dir holding a single source file."""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / filename).write_text(code)
        return run_script(ROOT / "detect_stack.py", str(d))


def test_detect_stack() -> None:
    r = run_detect_stack_on("model.py", "import pypsa\nn = pypsa.Network()\n")
    check("detect_stack: pypsa dir -> exit 0", r.returncode == 0,
          last_stdout_line(r))
    r = run_detect_stack_on("grid.py", "import pandapower as pp\npp.runpp(net)\n")
    check("detect_stack: pandapower dir -> exit 2", r.returncode == 2)


def build_solved_network(path: Path) -> bool:
    """Build and solve a small multi-carrier network; export it to `path`."""
    import numpy as np
    import pandas as pd
    import pypsa

    n = pypsa.Network()
    sns = pd.date_range("2025-01-01", periods=7 * 24, freq="h")
    n.set_snapshots(sns)
    rng = np.random.default_rng(1)
    n.add("Bus", "b1", carrier="AC")
    n.add("Bus", "b2", carrier="AC")
    n.add("Carrier", "gas", co2_emissions=0.2)
    n.add("Carrier", "solar")
    n.add("Carrier", "battery")
    n.add("Carrier", "AC")
    n.add("Bus", "h2", carrier="H2")
    n.add("Carrier", "H2")
    n.add("Carrier", "electrolysis")
    day = np.clip(np.sin((np.arange(len(sns)) % 24 - 6) / 12 * np.pi), 0, 1)
    n.add("Generator", "solar1", bus="b1", carrier="solar", p_nom=500,
          p_max_pu=pd.Series(day * rng.uniform(0.5, 1.0, len(sns)), sns))
    n.add("Generator", "gas1", bus="b2", carrier="gas", p_nom=450,
          efficiency=0.55, marginal_cost=70)
    n.add("Link", "elz", bus0="b1", bus1="h2", carrier="electrolysis",
          p_nom=50, efficiency=0.66, marginal_cost=1)
    n.add("Store", "h2store", bus="h2", carrier="H2", e_nom=5000,
          e_cyclic=True)
    n.add("Load", "dh2", bus="h2", p_set=5.0)
    n.add("StorageUnit", "batt", bus="b1", carrier="battery", p_nom=100,
          max_hours=4, efficiency_store=0.95, efficiency_dispatch=0.95,
          cyclic_state_of_charge=True, marginal_cost=2)
    n.add("Line", "l12", bus0="b1", bus1="b2", x=0.1, r=0.01, s_nom=250,
          carrier="AC")
    n.add("Load", "d1", bus="b1", p_set=pd.Series(150 + 80 * rng.random(len(sns)), sns))
    n.add("Load", "d2", bus="b2", p_set=180.0)
    status, cond = n.optimize(solver_name="highs")
    if status != "ok":
        return False
    n.export_to_netcdf(str(path))
    return True


def test_with_pypsa() -> None:
    try:
        import pypsa
    except ImportError:
        print("SKIP  pypsa not installed - compile checks only")
        return
    major = int(str(pypsa.__version__).split(".")[0])
    # prose facts in the suite are verified against PyPSA 1.x (README
    # Compatibility); a major bump means scripts may pass while prose rots
    check(f"pypsa major version == 1 (found {pypsa.__version__})", major == 1,
          "on mismatch: re-verify version-sensitive claims, NOTATION.md")
    with tempfile.TemporaryDirectory() as td:
        nc = Path(td) / "net.nc"
        try:
            ok = build_solved_network(nc)
        except Exception as e:  # noqa: BLE001
            check("build + solve synthetic network", False, repr(e))
            return
        check("build + solve synthetic network", ok)
        if not ok:
            return
        r = run_script(
            ROOT / "pypsa-physical-realism/scripts/validate_network.py",
            str(nc))
        # exit code is the contract: 0 = clean or warnings only, 1 = any ERROR
        check("validate_network: 0 errors on clean net", r.returncode == 0,
              last_stdout_line(r, r.stderr[-200:]))
        figs = Path(td) / "figs"
        r = run_script(ROOT / "pypsa-reporting/scripts/standard_plots.py",
                       str(nc), "--outdir", str(figs),
                       cwd=ROOT / "pypsa-reporting/scripts")
        n_figs = len(list(figs.glob("*.png"))) if figs.exists() else 0
        check("standard_plots: >= 6 figures", n_figs >= MIN_FIGURES,
              f"{n_figs} rendered")
        r = run_script(
            ROOT / "pypsa-data-pipelines/scripts/audit_inputs.py",
            "audit", str(nc))
        check("audit_inputs: clean series on synthetic net",
              r.returncode == 0, last_stdout_line(r, r.stderr[-200:]))
        r = run_script(
            ROOT / "pypsa-data-pipelines/scripts/audit_inputs.py",
            "convert", "annuity", "--overnight", "400000",
            "--rate", "0.07", "--life", "25")
        check("audit_inputs: annuity conversion",
              "0.08581" in r.stdout, last_stdout_line(r))
        r = run_script(
            ROOT / "pypsa-market-design/scripts/price_diagnostics.py",
            str(nc))
        check("price_diagnostics: clean prices + rent table",
              r.returncode == 0 and "SYSTEM SUM" in r.stdout,
              last_stdout_line(r, r.stderr[-200:]))


def build_recipe_network():
    """Toy model exposing every object the generic-pattern recipes touch."""
    import pandas as pd
    import pypsa

    n = pypsa.Network()
    n.set_snapshots(pd.date_range("2025-01-01", periods=24, freq="h"))
    n.add("Bus", "elec", carrier="AC")
    n.add("Bus", "h2", carrier="H2")
    n.add("Carrier", "gas", co2_emissions=0.2)
    n.add("Carrier", "wind")
    n.add("Generator", "gas1", bus="elec", carrier="gas", p_nom=100,
          efficiency=0.5, marginal_cost=50)
    n.add("Generator", "gas2", bus="elec", carrier="gas", p_nom_extendable=True,
          efficiency=0.5, marginal_cost=60, capital_cost=1e4)
    n.add("Generator", "wind1", bus="elec", carrier="wind", p_nom_extendable=True,
          capital_cost=2e4)
    n.add("Link", "electrolysis", bus0="elec", bus1="h2", carrier="electrolysis",
          p_nom_extendable=True, efficiency=0.66, capital_cost=1e4)
    n.add("Link", "fuel cell", bus0="h2", bus1="elec", carrier="fuel cell",
          p_nom_extendable=True, efficiency=0.5, capital_cost=1e4)
    n.add("Store", "h2store", bus="h2", carrier="H2", e_nom=1000, e_cyclic=True)
    n.add("Load", "d", bus="elec", p_set=80.0)
    return n


def test_reference_snippets() -> None:
    """Extract fenced python recipes from generic-patterns.md and EXECUTE them
    against a toy model — reference code is content too, and untested snippets
    rot (this exact failure shipped once)."""
    try:
        import pypsa  # noqa: F401 - guard: skip cleanly when not installed
    except ImportError:
        print("SKIP  reference snippets - pypsa not installed")
        return
    import re

    src = (ROOT / "pypsa-custom-constraints/references/generic-patterns.md"
           ).read_text()
    blocks = re.findall(r"```python\n(.*?)```", src, re.S)
    check("generic-patterns: found 3 fenced recipes",
          len(blocks) == EXPECTED_RECIPE_COUNT, f"{len(blocks)} blocks")

    n = build_recipe_network()
    n.optimize.create_model()
    ns = {"n": n, "m": n.model, "budget_t": 1e5,
          "firm_carriers": ["gas"], "peak_load": 80.0, "margin": 0.1, "k": 0.5}
    for i, block in enumerate(blocks, 1):
        try:
            exec(block, ns)  # noqa: S102 - executing our own shipped recipes
            check(f"generic-patterns recipe {i} executes", True)
        except Exception as e:  # noqa: BLE001
            check(f"generic-patterns recipe {i} executes", False,
                  f"{type(e).__name__}: {e}")
    for cname in EXPECTED_CONSTRAINTS:
        check(f"constraint '{cname}' landed in model",
              cname in n.model.constraints)
    status, _ = n.optimize.solve_model(solver_name="highs")
    check("model with recipe constraints solves ok", status == "ok")


def main() -> int:
    compile_all()
    test_detect_stack()
    if "--compile" not in sys.argv:
        test_with_pypsa()
        test_reference_snippets()
    print(f"\n{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
