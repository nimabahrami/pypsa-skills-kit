#!/usr/bin/env python3
"""diagnose_infeasibility.py - localize infeasibility via load-shedding probes.

Usage: python diagnose_infeasibility.py network.nc [--voll 10000] [--solver highs]

Adds a high-cost shedding Generator to every bus that carries a Load, re-solves,
and reports where/when shedding is used. Nonzero shedding pinpoints the bus, carrier
and time window of the binding shortage.
"""
from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd
    import pypsa

SHED_P_NOM = 1e6        # MW - effectively unlimited probe capacity
SHED_TOLERANCE = 1e-3   # MWh below this counts as numerical noise, not shedding


def _add_shedding_generators(n: pypsa.Network, voll: float) -> list[str]:
    """Attach a VOLL-priced shedding generator to every bus that carries a Load."""
    names = []
    for b in sorted(set(n.loads.bus)):
        name = f"shed::{b}"
        n.add("Generator", name, bus=b, carrier="load shedding",
              p_nom=SHED_P_NOM, marginal_cost=voll)
        names.append(name)
    return names


def _report_shedding(shed: pd.DataFrame) -> None:
    """Print which buses and snapshots needed shedding, plus interpretation."""
    per_bus = shed.sum().sort_values(ascending=False)
    per_bus = per_bus[per_bus > SHED_TOLERANCE]
    print("\nShed energy by bus (MWh-equivalent, weighting-free):")
    for k, v in per_bus.items():
        print(f"  {k:40s} {v:12.1f}")
    active = shed.sum(axis=1)
    active = active[active > SHED_TOLERANCE]
    print(f"\nShedding active in {len(active)} snapshots; first/last:")
    if len(active):
        print(f"  {active.index[0]}  ...  {active.index[-1]}")
    print("\nInterpretation: shortage localized at these buses/windows - inspect"
          " capacity, inflow/availability profiles and storage reach there.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("network")
    ap.add_argument("--voll", type=float, default=10000.0, help="EUR/MWh")
    ap.add_argument("--solver", default="highs")
    args = ap.parse_args()

    import pypsa

    n = pypsa.Network(args.network)
    names = _add_shedding_generators(n, args.voll)
    print(f"Added {len(names)} shedding generators at VOLL={args.voll} EUR/MWh")

    status, condition = n.optimize(solver_name=args.solver)
    print(f"status={status} condition={condition}")
    if status != "ok":
        print("Still failing WITH shedding -> structural bug, not capacity shortage:"
              " check custom constraints (read the LP), cyclic-SOC conflicts,"
              " impossible e_min_pu profiles, zero-impedance lines."
              f"\nCaveat: probes sit only at LOAD buses, capped at {SHED_P_NOM:.0e}"
              " MW - a shortage at a load-free intermediate bus or beyond the"
              " probe cap can also land here.")
        return 1

    shed = n.generators_t.p[names]
    if shed.sum().sum() < SHED_TOLERANCE:
        print("No shedding used: original infeasibility was NOT an energy shortage"
              " (or the original model is feasible). Check constraint families by"
              " bisection - see references/infeasibility.md.")
        return 0

    _report_shedding(shed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
