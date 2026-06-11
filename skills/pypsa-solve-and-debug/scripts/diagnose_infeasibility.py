#!/usr/bin/env python3
"""diagnose_infeasibility.py - localize infeasibility via load-shedding probes.

Usage: python diagnose_infeasibility.py network.nc [--voll 10000] [--solver highs]

Adds a high-cost shedding Generator to every bus that carries a Load, re-solves,
and reports where/when shedding is used. Nonzero shedding pinpoints the bus, carrier
and time window of the binding shortage.
"""
import argparse
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("network")
    ap.add_argument("--voll", type=float, default=10000.0, help="EUR/MWh")
    ap.add_argument("--solver", default="highs")
    args = ap.parse_args()

    import pypsa

    n = pypsa.Network(args.network)
    load_buses = sorted(set(n.loads.bus))
    names = []
    for b in load_buses:
        name = f"shed::{b}"
        n.add("Generator", name, bus=b, carrier="load shedding",
              p_nom=1e6, marginal_cost=args.voll)
        names.append(name)
    print(f"Added {len(names)} shedding generators at VOLL={args.voll} EUR/MWh")

    status, condition = n.optimize(solver_name=args.solver)
    print(f"status={status} condition={condition}")
    if status != "ok":
        print("Still failing WITH shedding -> structural bug, not capacity shortage:"
              " check custom constraints (read the LP), cyclic-SOC conflicts,"
              " impossible e_min_pu profiles, zero-impedance lines.")
        return 1

    shed = n.generators_t.p[names]
    total = shed.sum().sum()
    if total < 1e-3:
        print("No shedding used: original infeasibility was NOT an energy shortage"
              " (or the original model is feasible). Check constraint families by"
              " bisection - see references/infeasibility.md.")
        return 0

    per_bus = shed.sum().sort_values(ascending=False)
    per_bus = per_bus[per_bus > 1e-3]
    print("\nShed energy by bus (MWh-equivalent, weighting-free):")
    for k, v in per_bus.items():
        print(f"  {k:40s} {v:12.1f}")
    active = shed.sum(axis=1)
    active = active[active > 1e-3]
    print(f"\nShedding active in {len(active)} snapshots; first/last:")
    if len(active):
        print(f"  {active.index[0]}  ...  {active.index[-1]}")
    print("\nInterpretation: shortage localized at these buses/windows - inspect"
          " capacity, inflow/availability profiles and storage reach there.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
