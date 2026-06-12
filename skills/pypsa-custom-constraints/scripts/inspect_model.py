#!/usr/bin/env python3
"""Inspect a PyPSA/linopy model: list variables & constraints, grep one, dump LP,
and check duals after solve.

Usage:
  python inspect_model.py network.nc                       # list everything
  python inspect_model.py network.nc --grep custom-        # show matching constraints
  python inspect_model.py network.nc --lp out.lp           # export LP (small nets!)
  python inspect_model.py network.nc --solved --duals custom-co2
"""
from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from linopy import Model


def _print_listing(m: Model, grep: str | None) -> None:
    """List all variables, and constraints filtered by an optional substring."""
    print("== variables ==")
    for name, var in m.variables.items():
        print(f"  {name:40s} dims={dict(var.sizes)}")
    print("== constraints ==")
    for name, con in m.constraints.items():
        if grep and grep not in name:
            continue
        print(f"  {name:40s} dims={dict(con.sizes)}")


def _print_duals(m: Model, pattern: str) -> None:
    """Print min/max dual for every constraint whose name contains pattern."""
    for name, con in m.constraints.items():
        if pattern not in name:
            continue
        try:
            d = con.dual
            print(f"-- dual({name}): min={float(d.min())} "
                  f"max={float(d.max())} (nonzero => binding)")
        except Exception as e:  # noqa: BLE001
            print(f"-- dual({name}): unavailable ({e})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("network")
    ap.add_argument("--grep", default=None, help="substring filter on constraint names")
    ap.add_argument("--lp", default=None, help="write LP file to this path")
    ap.add_argument("--solved", action="store_true",
                    help="solve (HiGHS) before inspecting, enables duals")
    ap.add_argument("--duals", default=None,
                    help="substring of constraint names to print duals for")
    args = ap.parse_args()

    import pypsa  # imported late so --help works without pypsa installed

    n = pypsa.Network(args.network)
    n.optimize.create_model()
    m = n.model

    _print_listing(m, args.grep)

    if args.lp:
        m.to_file(args.lp)
        print(f"LP written to {args.lp} - read the rows named after your constraint.")

    if args.solved:
        status, condition = n.optimize.solve_model(solver_name="highs")
        print(f"status={status} condition={condition}")
        if args.duals:
            _print_duals(m, args.duals)
    return 0


if __name__ == "__main__":
    sys.exit(main())
