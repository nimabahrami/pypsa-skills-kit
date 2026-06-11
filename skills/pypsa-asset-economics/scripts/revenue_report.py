#!/usr/bin/env python3
"""revenue_report.py - per-asset revenue decomposition for a SOLVED PyPSA network.

Usage: python revenue_report.py solved_network.nc [--csv out.csv]

Decomposes, per generator / storage unit / store / link:
  energy_revenue  sum_t p_out(t) * price(out_bus, t) * w(t)
  energy_cost     sum_t p_in(t)  * price(in_bus, t)  * w(t)   (links, charging)
  vom_cost        sum_t |p|(t) * marginal_cost * w(t)
  capex           capital_cost * built capacity (annualized EUR)
  net_margin      revenue - costs

Caveat printed on every run: numbers inherit perfect-foresight and system-vs-merchant
biases of the underlying run (see SKILL.md).
"""
import argparse
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("network")
    ap.add_argument("--csv", default=None)
    args = ap.parse_args()

    import pandas as pd
    import pypsa

    n = pypsa.Network(args.network)
    if n.buses_t.marginal_price.empty:
        print("No marginal prices found - is this network solved?")
        return 1

    w = n.snapshot_weightings.objective
    lam = n.buses_t.marginal_price
    rows = []

    def price(bus):
        return lam[bus] if bus in lam.columns else 0.0

    for name, g in n.generators.iterrows():
        p = n.generators_t.p.get(name)
        if p is None:
            continue
        rev = float((p * price(g.bus) * w).sum())
        vom = float((p * w).sum()) * float(g.marginal_cost) if not hasattr(
            g.marginal_cost, "__len__") else float((p * w * g.marginal_cost).sum())
        cap = float(g.get("capital_cost", 0)) * float(
            g.get("p_nom_opt", g.get("p_nom", 0)))
        rows.append(["Generator", name, g.carrier, rev, 0.0, vom, cap,
                     rev - vom - cap])

    for name, l in n.links.iterrows():
        p0 = n.links_t.p0.get(name)
        if p0 is None:
            continue
        cost_in = float((p0.clip(lower=0) * price(l.bus0) * w).sum())
        rev = 0.0
        for i in ["", "2", "3"]:
            bcol, pcol = f"bus{i or '1'}", f"p{i or '1'}"
            if bcol in n.links.columns and isinstance(l.get(bcol), str) and l.get(bcol):
                po = getattr(n.links_t, pcol, None)
                if po is not None and name in po:
                    rev += float((-po[name] * price(l[bcol]) * w).sum())
        vom = float((p0.clip(lower=0) * w).sum()) * float(l.get("marginal_cost", 0))
        cap = float(l.get("capital_cost", 0)) * float(
            l.get("p_nom_opt", l.get("p_nom", 0)))
        rows.append(["Link", name, l.carrier, rev, cost_in, vom, cap,
                     rev - cost_in - vom - cap])

    for name, su in n.storage_units.iterrows():
        p = n.storage_units_t.p.get(name)
        if p is None:
            continue
        rev = float((p.clip(lower=0) * price(su.bus) * w).sum())
        cost = float((-p.clip(upper=0) * price(su.bus) * w).sum())
        vom = float((p.abs() * w).sum()) * float(su.get("marginal_cost", 0))
        cap = float(su.get("capital_cost", 0)) * float(
            su.get("p_nom_opt", su.get("p_nom", 0)))
        rows.append(["StorageUnit", name, su.carrier, rev, cost, vom, cap,
                     rev - cost - vom - cap])

    for name, s in n.stores.iterrows():
        p = n.stores_t.p.get(name)
        if p is None:
            continue
        rev = float((p.clip(lower=0) * price(s.bus) * w).sum())
        cost = float((-p.clip(upper=0) * price(s.bus) * w).sum())
        cap = float(s.get("capital_cost", 0)) * float(
            s.get("e_nom_opt", s.get("e_nom", 0)))
        rows.append(["Store", name, s.carrier, rev, cost, 0.0, cap,
                     rev - cost - cap])

    df = pd.DataFrame(rows, columns=["component", "name", "carrier",
                                     "energy_revenue", "energy_cost", "vom_cost",
                                     "capex_annualized", "net_margin"])
    df = df.sort_values("net_margin", ascending=False)
    pd.set_option("display.float_format", lambda v: f"{v:,.0f}")
    print(df.to_string(index=False))
    print("\nCAVEAT: perfect-foresight, system-optimal dispatch - read "
          "pypsa-asset-economics SKILL.md before treating these as merchant numbers.")
    if args.csv:
        df.to_csv(args.csv, index=False)
        print(f"Written {args.csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
