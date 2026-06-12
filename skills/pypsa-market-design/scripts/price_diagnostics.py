#!/usr/bin/env python3
"""price_diagnostics.py - market-price sanity + congestion economics for a
SOLVED PyPSA network.

Executable form of the checks in SKILL.md "Prices and interpretation" and
references/congestion-analysis.md (rent workflow step 2). Boundary: numeric
battery thresholds owned by pypsa-solve-and-debug/references/
interpreting-results.md; loading screens = pypsa-reporting #10.

Usage:
    python price_diagnostics.py solved_network.nc [--strict] [--floor -500]
                                [--top 10]

Exit code: 0 clean / warnings only, 1 if any ERROR (or any WARN w/ --strict).
"""
from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pypsa

EU_PRICE_FLOOR = -500.0       # EUR/MWh, DA exchange floor; cap is dynamic
ZERO_PRICE_SHARE_WARN = 0.30  # owner: interpreting-results.md battery #4
ZERO_PRICE_EPS = 0.01         # EUR/MWh treated as "zero price"
CONGESTED_LOADING = 0.99      # |flow|/capacity at/above this = congested hour
PRICE_TOL = 1e-3              # numerical slack on bid-stack comparisons


@dataclass
class Finding:
    severity: str   # "ERROR" | "WARN"
    component: str
    name: str
    message: str

    def line(self) -> str:
        return f"[{self.severity}] {self.component:12s} {self.name:35s} {self.message}"


AddFinding = Callable[[Finding], None]


def _check_duals_exist(n: pypsa.Network, add: AddFinding) -> bool:
    """MILP-no-duals trap: committable units silently delete prices."""
    lam = n.buses_t.marginal_price
    committable = bool(n.generators.get("committable", False) is not False
                       and n.generators.committable.any())
    empty = lam.empty or float(lam.abs().to_numpy().max()) < ZERO_PRICE_EPS
    if empty and committable:
        add(Finding("ERROR", "Prices", "-",
                    "committable units + no/zero marginal prices = the MILP"
                    " no-duals trap. Fixes: optimize(linearized_unit_commitment"
                    "=True) | fixed-commitment LP pricing run (SKILL.md)"))
        return False
    if empty:
        add(Finding("ERROR", "Prices", "-",
                    "no meaningful marginal prices - network solved? duals"
                    " assigned (assign_all_duals)?"))
        return False
    return True


def _check_price_levels(n: pypsa.Network, add: AddFinding,
                        floor: float) -> None:
    """Floor/ceiling plausibility + zero-price share, per the EU conventions."""
    lam = n.buses_t.marginal_price
    pmin, pmax = float(lam.min().min()), float(lam.max().max())
    if pmin < floor:
        add(Finding("WARN", "Prices", "-",
                    f"min price {pmin:,.0f} below exchange floor {floor:,.0f}"
                    " EUR/MWh - subsidy/must-run encoding artifact, not a"
                    " market outcome; cap the bid, not the result"))
    zero_share = float((lam <= ZERO_PRICE_EPS).to_numpy().mean())
    if zero_share > ZERO_PRICE_SHARE_WARN:
        add(Finding("WARN", "Prices", "-",
                    f"{zero_share:.0%} of bus-hours at <= 0 price -"
                    " over-supply | non-binding load (battery #4)"))
    # dispatch-only runs: no price can exceed the highest bid in the stack;
    # expansion runs are exempt (capex legitimately enters duals)
    any_ext = any(getattr(n, comp)[col].any()
                  for comp, col in [("generators", "p_nom_extendable"),
                                    ("storage_units", "p_nom_extendable"),
                                    ("links", "p_nom_extendable"),
                                    ("lines", "s_nom_extendable"),
                                    ("stores", "e_nom_extendable")]
                  if col in getattr(n, comp).columns and not getattr(n, comp).empty)
    if not any_ext and not n.generators.empty:
        mc = n.generators.marginal_cost
        mc_t = getattr(n.generators_t, "marginal_cost", None)
        top_bid = float(mc.max())
        if mc_t is not None and not mc_t.empty:
            top_bid = max(top_bid, float(mc_t.max().max()))
        if pmax > top_bid * (1 + PRICE_TOL) + PRICE_TOL:
            add(Finding("WARN", "Prices", "-",
                        f"max price {pmax:,.0f} exceeds the highest bid"
                        f" {top_bid:,.0f} in a DISPATCH-ONLY run - storage"
                        " opportunity cost can do this legitimately; no"
                        " storage -> numerical artifact"))


def _branch_rent_rows(n: pypsa.Network) -> list[tuple[str, str, float, float]]:
    """(component, name, rent EUR, congested-hour share) per branch."""
    lam = n.buses_t.marginal_price
    w = n.snapshot_weightings.objective
    rows: list[tuple[str, str, float, float]] = []
    for comp, flows, cap_cols in [
            ("Line", "lines", ("s_nom_opt", "s_nom")),
            ("Link", "links", ("p_nom_opt", "p_nom"))]:
        df = getattr(n, comp.lower() + "s")
        p0 = getattr(n, flows + "_t").p0
        if df.empty or p0.empty:
            continue
        for name, row in df.iterrows():
            if name not in p0.columns or row.bus0 not in lam.columns \
                    or str(row.get("bus1", "")) not in lam.columns:
                continue
            flow = p0[name]
            spread = lam[row.bus1] - lam[row.bus0]
            rent = float((spread * flow * w).sum())
            cap = 0.0
            for c in cap_cols:
                cap = float(row.get(c, 0) or 0)
                if cap > 0:
                    break
            share = float((flow.abs() >= CONGESTED_LOADING * cap).mean()) \
                if cap > 0 else 0.0
            rows.append((comp, str(name), rent, share))
    return rows


def _report_congestion(n: pypsa.Network, top: int) -> None:
    """Congestion-rent table per branch + system sum (congestion-analysis.md).

    Per-branch terms can be NEGATIVE (loop flow against the price gradient);
    only the SYSTEM sum is a rent.
    """
    rows = sorted(_branch_rent_rows(n), key=lambda r: -abs(r[2]))
    if not rows:
        print("\nno branches with prices on both ends - no congestion table")
        return
    total = sum(r[2] for r in rows)
    print(f"\nCongestion rents (top {min(top, len(rows))} by |rent|;"
          " negative = loop flow against gradient):")
    print(f"{'comp':6s} {'name':30s} {'rent EUR':>14s} {'congested h':>12s}")
    for comp, name, rent, share in rows[:top]:
        print(f"{comp:6s} {name:30s} {rent:14,.0f} {share:11.1%}")
    print(f"{'SYSTEM SUM':37s} {total:14,.0f}"
          "   (= load payments - generator revenues, lossless)")


def diagnose(n: pypsa.Network, floor: float) -> list[Finding]:
    findings: list[Finding] = []
    if _check_duals_exist(n, findings.append):
        _check_price_levels(n, findings.append, floor)
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("network")
    ap.add_argument("--strict", action="store_true", help="warnings also fail")
    ap.add_argument("--floor", type=float, default=EU_PRICE_FLOOR,
                    help="exchange price floor screen, EUR/MWh")
    ap.add_argument("--top", type=int, default=10,
                    help="branches in the congestion table")
    args = ap.parse_args()

    import pypsa  # late import so --help works without pypsa

    n = pypsa.Network(args.network)
    findings = diagnose(n, args.floor)
    errors = [f for f in findings if f.severity == "ERROR"]
    warns = [f for f in findings if f.severity == "WARN"]
    for f in errors + warns:
        print(f.line())
    if not errors:
        _report_congestion(n, args.top)
    print(f"\n{len(errors)} error(s), {len(warns)} warning(s).")
    if errors or (args.strict and warns):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
