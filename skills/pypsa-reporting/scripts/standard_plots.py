#!/usr/bin/env python3
"""standard_plots.py - canonical utility figure set for a SOLVED PyPSA network.

Usage:
    python standard_plots.py solved_network.nc --outdir figures
    python standard_plots.py solved_network.nc --outdir figures --formats png svg

Renders (file number = chart-catalog.md entry number; each skipped gracefully
with a printed reason if inputs are missing):
    00_diagnostic_panel   energy balance | price duration | SOC | shedding  (ALWAYS, catalog #1)
    02_energy_balance     supply vs withdrawal per carrier
    03_dispatch_weeks     stacked dispatch: peak-load | max-residual | min-residual weeks
    04_price_duration     duration curve + month x hour price heatmap
    05_storage_cycling    capacity-weighted SOC per carrier + equivalent full cycles
    06_capacity           existing vs optimized capacity per carrier (shedding excluded)
    07_cost_stack         annualized capex + opex per carrier (incl. line capex)
    08_curtailment        monthly curtailed VRE share
    10_line_loading       loading duration curves for the most loaded lines
    12_constraint_duals   global constraint shadow prices

Doubles as a pattern library: every plot is a standalone `plot_*(n, ax)` function -
lift what you need into your own reporting code. Design rules:
references/design-system.md. Failure-mode reading: references/diagnostics.md.
"""
from __future__ import annotations

import argparse
import sys
import traceback

from plot_style import apply_style, caption, color_for, savefig

ELEC_CARRIERS = ("AC", "electricity", "elec", "DC")

_warned_fallback = False


# ----------------------------------------------------------------- helpers
def elec_buses(n):
    global _warned_fallback
    mask = n.buses.carrier.isin(ELEC_CARRIERS)
    if not mask.any():  # fall back to the most common bus carrier
        top = n.buses.carrier.value_counts().index[0]
        if not _warned_fallback:
            print(f"WARNING: no electricity carrier found; "
                  f"reporting on '{top}' buses")
            _warned_fallback = True
        mask = n.buses.carrier == top
    return n.buses.index[mask]


def energy_weights(n):
    """Snapshot weights for ENERGY sums (MWh = MW * weight)."""
    return n.snapshot_weightings.generators


def cost_weights(n):
    """Snapshot weights for COST sums (objective weighting)."""
    return n.snapshot_weightings.objective


def grouped_generation(n, buses):
    """Generation time series grouped by carrier, MW, on the given buses."""
    gens = n.generators[n.generators.bus.isin(buses)]
    p = n.generators_t.p[gens.index.intersection(n.generators_t.p.columns)]
    return p.T.groupby(gens.carrier.reindex(p.columns)).sum().T


def storage_dispatch(n, buses):
    su = n.storage_units[n.storage_units.bus.isin(buses)]
    if su.empty or n.storage_units_t.p.empty:
        return None
    p = n.storage_units_t.p[su.index.intersection(n.storage_units_t.p.columns)]
    return p.T.groupby(su.carrier.reindex(p.columns)).sum().T


def link_flows(n, buses):
    """Net link injection per carrier at the given buses, MW time series.

    Positive = power injected INTO a bus (e.g. fuel cell), negative =
    withdrawn (e.g. electrolysis, exports). Iterates ALL link ports
    (bus0, bus1, bus2, ...) with their p0/p1/p2/... series.
    """
    import pandas as pd

    if n.links.empty or n.links_t.p0.empty:
        return None
    flows = {}
    bus_cols = [c for c in n.links.columns
                if c.startswith("bus") and c[3:].isdigit()]
    for col in bus_cols:
        pt = getattr(n.links_t, f"p{col[3:]}", None)
        if pt is None or pt.empty:
            continue
        sel = n.links.index[n.links[col].isin(buses)]
        cols = sel.intersection(pt.columns)
        if not len(cols):
            continue
        inj = -pt[cols]  # positive p_i = withdrawal from bus_i
        byc = inj.T.groupby(n.links.carrier.reindex(cols)).sum().T
        for c in byc.columns:
            flows[c] = flows.get(c, 0.0) + byc[c]
    return pd.DataFrame(flows) if flows else None


def total_load(n, buses):
    loads = n.loads[n.loads.bus.isin(buses)]
    if hasattr(n.loads_t, "p") and not n.loads_t.p.empty:
        cols = loads.index.intersection(n.loads_t.p.columns)
        if len(cols):
            return n.loads_t.p[cols].sum(axis=1)
    import pandas as pd

    sset = n.loads_t.p_set if hasattr(n.loads_t, "p_set") else pd.DataFrame()
    cols = loads.index.intersection(sset.columns) if not sset.empty else []
    ts = sset[cols].sum(axis=1) if len(cols) else pd.Series(0.0, index=n.snapshots)
    static = loads.index.difference(cols)
    if len(static):
        ts = ts + loads.loc[static, "p_set"].sum()
    return ts


def snapshots_per_week(n):
    """Snapshots covering 7 days, from the inferred snapshot frequency."""
    import pandas as pd

    sns = n.snapshots
    if len(sns) < 2:
        return len(sns)
    freq = pd.Series(sns).diff().median()
    return max(1, int(round(pd.Timedelta("7D") / freq)))


# ----------------------------------------------------------------- plots
def plot_energy_balance(n, ax):
    """#2 - per-carrier net energy on the electricity carrier. Must net to ~0."""
    import pandas as pd

    buses = elec_buses(n)
    w = energy_weights(n)
    parts = {}
    gen = grouped_generation(n, buses)
    for c in gen.columns:
        parts[c] = float((gen[c] * w).sum())
    sd = storage_dispatch(n, buses)
    if sd is not None:
        for c in sd.columns:
            parts[c] = parts.get(c, 0.0) + float((sd[c] * w).sum())
    # links: net injection at elec buses across ALL ports (bus0, bus1, bus2, ...)
    lf = link_flows(n, buses)
    if lf is not None:
        for c in lf.columns:
            parts[c] = parts.get(c, 0.0) + float((lf[c] * w).sum())
    parts["load"] = -float((total_load(n, buses) * w).sum())
    s = pd.Series(parts).sort_values()
    s = s[s.abs() > max(1e-6, s.abs().max() * 1e-5)] / 1e6  # TWh
    ax.barh(s.index, s.values, color=[color_for(c) for c in s.index])
    ax.axvline(0, color="#1A1A1A", lw=0.8)
    net = s.sum()
    ax.set_title(f"Energy balance nets to {net:+.3f} TWh"
                 + ("  [CHECK: should be ~0]" if abs(net) > 0.01 * s.abs().max()
                    else ""))
    ax.set_xlabel("TWh (positive = supply)")
    ax.grid(axis="x", alpha=0.25)


def plot_price_duration(n, ax, heatmap_ax=None):
    """#4 - sorted marginal price (mean across elec buses + envelope).

    Pass `heatmap_ax` for the companion month x hour mean-price heatmap
    (used by the standalone figure; the diagnostic panel passes one ax only).
    """
    import numpy as np

    lam = n.buses_t.marginal_price
    if lam.empty:
        raise ValueError("no marginal prices - network not solved?")
    cols = [b for b in elec_buses(n) if b in lam.columns]
    lam = lam[cols]
    srt = lam.apply(lambda s: s.sort_values(ascending=False).values)
    x = np.linspace(0, 100, len(lam))
    ax.fill_between(x, srt.min(axis=1), srt.max(axis=1), alpha=0.18,
                    color="#3D6FB6", lw=0)
    ax.plot(x, srt.mean(axis=1), color="#3D6FB6")
    ax.axhline(0, color="#1A1A1A", lw=0.8)
    shed = n.generators[
        n.generators.carrier.astype(str).str.lower().str.contains("shed")]
    if not shed.empty:  # annotate the VOLL level set by shedding probes
        voll = float(shed.marginal_cost.max())
        ax.axhline(voll, color="#DD1C1A", lw=1.0, ls="--",
                   label=f"VOLL (shedding) = {voll:,.0f}")
        ax.legend(loc="upper right", fontsize=8)
    zero_share = float((lam.mean(axis=1) <= 0.01).mean()) * 100
    ax.set_title(f"Price duration - {zero_share:.0f}% of hours at ~0"
                 + ("  [CHECK]" if zero_share > 30 else ""))
    ax.set_xlabel("share of hours [%]")
    ax.set_ylabel("EUR/MWh")
    if heatmap_ax is not None:
        import numpy as np

        pm = lam.mean(axis=1)
        grid = pm.groupby([pm.index.month, pm.index.hour]).mean().unstack()
        im = heatmap_ax.imshow(grid.values, cmap="viridis", aspect="auto",
                               origin="lower", interpolation="nearest")
        heatmap_ax.figure.colorbar(im, ax=heatmap_ax, label="EUR/MWh")
        heatmap_ax.set_xticks(np.arange(len(grid.columns))[::3],
                              [str(h) for h in grid.columns[::3]])
        heatmap_ax.set_yticks(np.arange(len(grid.index)),
                              [str(m) for m in grid.index])
        heatmap_ax.set_xlabel("hour of day")
        heatmap_ax.set_ylabel("month")
        heatmap_ax.set_title("Mean price by month x hour")
        heatmap_ax.grid(False)


def plot_soc(n, ax, cycles_ax=None):
    """#5 - capacity-weighted normalized SOC per storage carrier.

    Pass `cycles_ax` for the companion equivalent-full-cycles bar
    (standalone figure only; the diagnostic panel shows SOC alone).
    """
    import pandas as pd

    series, cycles = {}, {}
    if not n.stores_t.e.empty:
        e = n.stores_t.e
        cap = n.stores.e_nom_opt.where(n.stores.e_nom_opt > 0,
                                       n.stores.e_nom).reindex(e.columns)
        carriers = n.stores.carrier.reindex(e.columns)
        for carrier in pd.unique(carriers):
            cols = e.columns[carriers == carrier]
            csum = float(cap[cols].sum())
            if csum <= 0:
                continue
            # capacity-weighted mean: sum(e) / sum(cap), not mean of ratios
            series[carrier] = e[cols].sum(axis=1) / csum
            thr = float(e[cols].diff().abs().sum().sum())  # charge+discharge MWh
            cycles[carrier] = cycles.get(carrier, 0.0) + thr / (2 * csum)
    if not n.storage_units_t.state_of_charge.empty:
        soc = n.storage_units_t.state_of_charge
        su = n.storage_units
        cap = (su.p_nom_opt.where(su.p_nom_opt > 0, su.p_nom) * su.max_hours
               ).reindex(soc.columns)
        carriers = su.carrier.reindex(soc.columns)
        w = energy_weights(n)
        for carrier in pd.unique(carriers):
            cols = soc.columns[carriers == carrier]
            csum = float(cap[cols].sum())
            if csum <= 0:
                continue
            series[carrier] = soc[cols].sum(axis=1) / csum
            pcols = cols.intersection(n.storage_units_t.p.columns)
            if len(pcols):
                thr = float(n.storage_units_t.p[pcols].abs()
                            .mul(w, axis=0).sum().sum())
                cycles[carrier] = cycles.get(carrier, 0.0) + thr / (2 * csum)
    if not series:
        raise ValueError("no storage in network")
    df = pd.DataFrame(series)
    for c in df.columns:
        ax.plot(df.index, df[c], label=str(c), color=color_for(c))
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("SOC [-]")
    end_drained = bool((df.iloc[-1] < 0.02).any())
    ax.set_title("Storage state of charge (capacity-weighted)"
                 + ("  [CHECK: drains to 0 at horizon end - e_cyclic?]"
                    if end_drained else ""))
    if len(df.columns) <= 6:
        ax.legend(ncol=min(3, len(df.columns)))
    if cycles_ax is not None and cycles:
        cs = pd.Series(cycles).sort_values()
        cycles_ax.barh(cs.index.astype(str), cs.values,
                       color=[color_for(c) for c in cs.index])
        cycles_ax.set_xlabel("equivalent full cycles "
                             "(throughput / 2 x energy capacity)")
        cycles_ax.set_title("Storage cycling over horizon")
        cycles_ax.grid(axis="x", alpha=0.25)


def plot_shedding(n, ax):
    """#11 - load shedding timeline; explicit empty state."""
    shed_gens = n.generators.index[
        n.generators.carrier.astype(str).str.lower().str.contains("shed")]
    cols = [g for g in shed_gens if g in n.generators_t.p.columns]
    if not cols:
        ax.text(0.5, 0.5, "no shedding generators present\n"
                "(run diagnose_infeasibility.py to add probes)",
                ha="center", va="center", color="#666666")
        ax.set_title("Load shedding - not instrumented")
        ax.set_xticks([])
        ax.set_yticks([])
        return
    ts = n.generators_t.p[cols].sum(axis=1)
    total = float((ts * energy_weights(n)).sum())
    ax.fill_between(ts.index, ts.values, color="#DD1C1A", lw=0)
    ax.set_ylabel("MW shed")
    ax.set_title(f"Load shedding - {total:,.0f} MWh total"
                 + ("  [FAILURE: investigate]" if total > 1e-3 else " (none)"))


def plot_dispatch_week(n, ax, start, label):
    """#3 - stacked dispatch for the week starting at snapshot index `start`.

    One positive stack (generation + storage discharge + link injections,
    e.g. fuel cell) and one negative stack (storage charging + link
    withdrawals, e.g. electrolysis / exports), each per carrier, so storage
    never paints over generation and every component is in the legend.
    Multi-port links (bus2, bus3, ...) are included on their elec ports.
    """
    import pandas as pd

    sns_all = n.snapshots
    t0 = sns_all[start]
    sns = sns_all[(sns_all >= t0) & (sns_all < t0 + pd.Timedelta("7D"))]
    buses = elec_buses(n)
    net = grouped_generation(n, buses)
    for extra in (storage_dispatch(n, buses), link_flows(n, buses)):
        if extra is not None:
            net = net.add(extra, fill_value=0.0)
    if net.empty:
        raise ValueError("no dispatchable flows on electricity buses")
    net = net.loc[sns] / 1e3  # GW
    pos = net.clip(lower=0)
    neg = net.clip(upper=0)
    order = pos.sum().sort_values(ascending=False)
    order = list(order[order > 1e-9].index)
    if order:
        ax.stackplot(sns, [pos[c].values for c in order],
                     colors=[color_for(c) for c in order],
                     labels=[str(c) for c in order], lw=0)
    neg_cols = [c for c in neg.columns if (neg[c] < -1e-9).any()]
    if neg_cols:
        ax.stackplot(sns, [neg[c].values for c in neg_cols],
                     colors=[color_for(c) for c in neg_cols],
                     labels=[str(c) if c not in set(order) else "_nolegend_"
                             for c in neg_cols], lw=0)
    load = total_load(n, buses).loc[sns] / 1e3
    ax.plot(sns, load.values, color="#1A1A1A", lw=1.4, label="load")
    ax.set_title(f"Dispatch - {label}")
    ax.set_ylabel("GW")
    ax.legend(loc="upper left", ncol=4, fontsize=7.5)


def pick_weeks(n):
    """Auto-select (start index, label) for the peak-load, max-residual and
    min-residual load weeks. Week length follows the snapshot frequency."""
    buses = elec_buses(n)
    load = total_load(n, buses)
    gen = grouped_generation(n, buses)
    vre_cols = [c for c in gen.columns
                if any(k in str(c).lower() for k in ("wind", "solar", "ror"))]
    residual = load - (gen[vre_cols].sum(axis=1) if vre_cols else 0)
    step = snapshots_per_week(n)
    out = []
    for series, label, pick in [(load, "peak load week", "max"),
                                (residual, "max residual load week", "max"),
                                (residual, "min residual load week", "min")]:
        if len(series) <= step:
            out.append((0, label))
            continue
        roll = series.rolling(step).sum().dropna()
        # rolling(step) at index `end` covers [end - step + 1, end]
        end = series.index.get_loc(roll.idxmax() if pick == "max"
                                   else roll.idxmin())
        out.append((max(0, end - step + 1), label))
    return out


def plot_capacity(n, ax):
    """#6 - existing vs added capacity per carrier (MW components only).

    Shedding probes are excluded - their slack capacity dwarfs real assets.
    """
    import pandas as pd
    from matplotlib.patches import Patch

    rows = []
    for comp, nom, opt in [("generators", "p_nom", "p_nom_opt"),
                           ("links", "p_nom", "p_nom_opt"),
                           ("storage_units", "p_nom", "p_nom_opt"),
                           ("lines", "s_nom", "s_nom_opt")]:  # MVA ~ MW
        df = getattr(n, comp)
        if df.empty or opt not in df.columns:
            continue
        g = df.groupby("carrier")[[nom, opt]].sum()
        g.columns = ["p_nom", "p_nom_opt"]  # normalize s_nom -> p_nom (MVA ~ MW)
        rows.append(g)
    if not rows:
        raise ValueError("no capacity data")
    cap = pd.concat(rows).groupby(level=0).sum() / 1e3  # GW
    shed_mask = cap.index.astype(str).str.lower().str.contains("shed")
    excluded = bool(shed_mask.any())
    cap = cap[~shed_mask]
    if cap.empty:
        raise ValueError("no capacity data besides shedding slack")
    cap["added"] = (cap["p_nom_opt"] - cap["p_nom"]).clip(lower=0)
    cap = cap.sort_values("p_nom_opt", ascending=True).tail(15)
    colors = [color_for(c) for c in cap.index]
    ax.barh(cap.index, cap["p_nom"], color=colors, alpha=0.45)
    ax.barh(cap.index, cap["added"], left=cap["p_nom"], color=colors)
    ax.set_xlabel("GW")
    ax.set_title("Capacity - existing (faded) vs optimized addition")
    ax.legend(handles=[Patch(facecolor="#C9C9C9", label="existing"),
                       Patch(facecolor="#4A4A4A", label="added")])
    if excluded:
        ax.text(0.99, 0.02, "shedding capacity excluded (diagnostic slack)",
                transform=ax.transAxes, ha="right", va="bottom",
                fontsize=8, color="#666666")


def plot_cost_stack(n, ax):
    """#7 - annualized capex + opex per carrier (lines: capex only)."""
    import pandas as pd

    w = cost_weights(n)
    capex, opex = {}, {}
    specs = [("generators", "p_nom_opt", "p"), ("links", "p_nom_opt", "p0"),
             ("storage_units", "p_nom_opt", "p"), ("stores", "e_nom_opt", "p"),
             ("lines", "s_nom_opt", None)]  # lines carry no marginal cost
    for comp, optcol, pcol in specs:
        df = getattr(n, comp)
        ts = getattr(getattr(n, comp + "_t"), pcol, None) if pcol else None
        if df.empty:
            continue
        for name, row in df.iterrows():
            car = str(row.get("carrier", "")) or comp
            cc = float(row.get("capital_cost", 0)) * float(
                row.get(optcol, row.get(optcol.replace("_opt", ""), 0)) or 0)
            capex[car] = capex.get(car, 0.0) + cc
            mc = float(row.get("marginal_cost", 0) or 0)
            if mc and ts is not None and name in ts.columns:
                opex[car] = opex.get(car, 0.0) + float(
                    (ts[name].clip(lower=0) * w).sum()) * mc
    df = pd.DataFrame({"capex": pd.Series(capex, dtype=float),
                       "opex": pd.Series(opex, dtype=float)}
                      ).fillna(0) / 1e9  # bnEUR/a
    df = df[df.sum(axis=1) > 0].sort_values("capex", ascending=True).tail(15)
    if df.empty:
        raise ValueError("no cost data")
    from matplotlib.patches import Patch

    colors = [color_for(c) for c in df.index]
    ax.barh(df.index, df["capex"], color=colors)
    ax.barh(df.index, df["opex"], left=df["capex"], color=colors, alpha=0.5)
    ax.legend(handles=[Patch(facecolor="#4A4A4A", label="capex (annualized)"),
                       Patch(facecolor="#4A4A4A", alpha=0.5, label="opex")])
    ax.set_xlabel("bn EUR / a")
    total = float(df.sum().sum())  # bn EUR/a
    if total >= 10:
        head = f"{total:.0f} bn EUR/a"
    elif total >= 1:
        head = f"{total:.2f} bn EUR/a"
    else:
        head = f"{total * 1e3:.0f} M EUR/a"
    ax.set_title(f"System cost {head} by carrier")


def plot_curtailment(n, ax):
    """#8 - monthly curtailed share per VRE carrier."""
    import pandas as pd

    pmax = n.generators_t.p_max_pu
    if pmax.empty:
        raise ValueError("no VRE availability series")
    gens = n.generators.loc[n.generators.index.intersection(pmax.columns)]
    cap = gens.p_nom_opt.where(gens.p_nom_opt > 0, gens.p_nom)
    avail = pmax[gens.index] * cap
    disp = n.generators_t.p[gens.index]
    cur = (avail - disp).clip(lower=0)

    def monthly(s):
        try:
            return s.resample("ME").sum()
        except ValueError:  # older pandas alias
            return s.resample("M").sum()

    plotted = False
    for carrier in pd.unique(gens.carrier):
        idx = gens.index[gens.carrier == carrier]
        a_m = monthly(avail[idx].sum(axis=1))
        c_m = monthly(cur[idx].sum(axis=1))
        if float(a_m.sum()) == 0:
            continue
        ax.plot(c_m.index, (c_m / a_m.replace(0, float("nan"))) * 100,
                label=str(carrier), color=color_for(carrier), marker="o", ms=3)
        plotted = True
    if not plotted:
        raise ValueError("curtailment series could not be built")
    ax.set_ylabel("curtailed share [%]")
    ax.set_title("VRE curtailment by month")
    ax.legend()


def plot_line_loading(n, ax, top=10):
    """#10 - |flow|/s_nom duration curves for the most loaded lines."""
    import numpy as np

    if n.lines.empty or n.lines_t.p0.empty:
        raise ValueError("no lines (or no line flow results) in network")
    cols = n.lines.index.intersection(n.lines_t.p0.columns)
    cap = n.lines.s_nom_opt.where(n.lines.s_nom_opt > 0, n.lines.s_nom)
    cap = cap.reindex(cols).replace(0, float("nan"))
    loading = (n.lines_t.p0[cols].abs() / cap).dropna(axis=1, how="all")
    if loading.empty:
        raise ValueError("no lines with nonzero capacity")
    sel = loading.mean().sort_values(ascending=False).head(top).index
    x = np.linspace(0, 100, len(loading))
    for name in sel:
        ax.plot(x, loading[name].sort_values(ascending=False).values * 100,
                label=str(name), lw=1.2)
    ax.axhline(100, color="#DD1C1A", lw=0.8, ls="--")
    ax.set_xlabel("share of hours [%]")
    ax.set_ylabel("loading [% of s_nom]")
    ax.set_title(f"Line loading - {len(sel)} most loaded "
                 f"line{'s' if len(sel) != 1 else ''}")
    ax.legend(fontsize=7.5, ncol=2)


def plot_constraint_duals(n, ax):
    """#12 - shadow prices (mu) of global constraints."""
    gc = n.global_constraints
    if gc.empty:
        raise ValueError("no global constraints in network")
    if "mu" not in gc.columns or gc.mu.isna().all() or (
            n.buses_t.marginal_price.empty):  # mu defaults to 0 pre-solve
        raise ValueError("global constraints carry no duals (mu) - "
                         "network not solved?")
    mu = gc.mu.dropna()
    ax.barh(mu.index.astype(str), mu.values, color="#3D6FB6")
    ax.axvline(0, color="#1A1A1A", lw=0.8)
    ax.set_xlabel("shadow price mu [EUR per constraint unit]")
    ax.set_title("Global constraint duals")
    ax.text(0.99, 0.02, "sign: objective change per unit of constraint "
            "relaxation (e.g. EUR/tCO2 for a CO2 cap)",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=8, color="#666666")
    ax.grid(axis="x", alpha=0.25)


# ----------------------------------------------------------------- driver
def render(n, outdir, formats, debug=False):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    apply_style()
    made, skipped = [], []

    if n.buses_t.marginal_price.empty:
        print("=" * 72)
        print("WARNING: network appears unsolved - diagnostic figures only, "
              "results figures will be skipped/meaningless")
        print("=" * 72)

    def attempt(name, fn):
        try:
            fig = fn()
            savefig(fig, outdir, name, formats)
            plt.close(fig)
            made.append(name)
        except Exception as e:  # noqa: BLE001
            skipped.append((name, str(e) or repr(e)))
            if debug:
                traceback.print_exc()

    # 00 diagnostic panel - ALWAYS first (references/diagnostics.md)
    def panel():
        fig, axs = plt.subplots(2, 2, figsize=(12, 8))
        for ax, f in zip(axs.flat, [plot_energy_balance, plot_price_duration,
                                    plot_soc, plot_shedding]):
            try:
                f(n, ax)
            except Exception as e:  # noqa: BLE001
                ax.text(0.5, 0.5, f"unavailable:\n{str(e) or repr(e)}",
                        ha="center",
                        va="center", color="#666666", fontsize=8)
        fig.suptitle("Diagnostic panel - read before any presentation figure",
                     fontweight="bold")
        return fig

    attempt("00_diagnostic_panel", panel)

    singles = [("02_energy_balance", plot_energy_balance, (9, 5)),
               ("06_capacity", plot_capacity, (9, 6)),
               ("07_cost_stack", plot_cost_stack, (9, 6)),
               ("08_curtailment", plot_curtailment, (9, 5)),
               ("10_line_loading", plot_line_loading, (9, 5)),
               ("12_constraint_duals", plot_constraint_duals, (9, 5))]
    for name, f, size in singles:
        def make(name=name, f=f, size=size):
            fig, ax = plt.subplots(figsize=size)
            f(n, ax)
            if name == "07_cost_stack":
                caption(fig, "Annualized costs; run type and foresight caveats "
                             "apply - see pypsa-asset-economics.")
            return fig
        attempt(name, make)

    def weeks():
        sel = pick_weeks(n)
        fig, axs = plt.subplots(len(sel), 1, figsize=(11, 4 * len(sel)))
        axs = [axs] if len(sel) == 1 else list(axs)
        for ax, (start, label) in zip(axs, sel):
            plot_dispatch_week(n, ax, start, label)
        return fig

    attempt("03_dispatch_weeks", weeks)

    def price():
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        plot_price_duration(n, ax1, heatmap_ax=ax2)
        return fig

    attempt("04_price_duration", price)

    def storage():
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        plot_soc(n, ax1, cycles_ax=ax2)
        return fig

    attempt("05_storage_cycling", storage)

    print(f"created {len(made)} figure(s) in {outdir}: " + ", ".join(made))
    for name, why in skipped:
        print(f"skipped {name}: {why}")
    return made


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("network")
    ap.add_argument("--outdir", default="figures")
    ap.add_argument("--formats", nargs="+", default=["png"])
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    import pypsa  # late import so --help works without pypsa

    n = pypsa.Network(args.network)
    render(n, args.outdir, tuple(args.formats), debug=args.debug)
    return 0


if __name__ == "__main__":
    sys.exit(main())
