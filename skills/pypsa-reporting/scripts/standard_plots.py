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
from typing import TYPE_CHECKING

from plot_style import (ACCENT_BLUE, ALERT_RED, INK, MUTED_TEXT, SWATCH_DARK,
                        SWATCH_LIGHT, apply_style, caption, color_for, savefig)

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path
    from types import ModuleType

    import pandas as pd
    import pypsa
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

# NOTE: pandas/numpy/matplotlib/pypsa are imported inside functions throughout
# this module so `--help` works without heavy deps and single plot functions
# stay liftable into other codebases.

ELEC_CARRIERS = ("AC", "electricity", "elec", "DC")
VRE_KEYWORDS = ("wind", "solar", "ror")

# unit scalings
MW_PER_GW = 1e3
MWH_PER_TWH = 1e6
EUR_PER_BN_EUR = 1e9

# diagnostic thresholds
ENERGY_IMBALANCE_TOL = 0.01  # |net| above this share of the largest term -> CHECK
ZERO_PRICE_SHARE_WARN = 30  # % of ~0-price hours that earns a [CHECK] flag
SOC_DRAIN_LEVEL = 0.02  # end-of-horizon SOC below this -> e_cyclic check
SOC_LEGEND_MAX = 6  # more carriers than this clutters the SOC legend
MAX_BARS = 15  # carriers shown on capacity / cost bar charts
DEFAULT_TOP_LINES = 10

# figure sizes (inches)
FIGSIZE_PANEL = (12, 8)
FIGSIZE_WIDE = (9, 5)
FIGSIZE_TALL = (9, 6)
FIGSIZE_DUO = (12, 5)
FIGSIZE_WEEK_ROW = (11, 4)  # per stacked dispatch-week row

COST_STACK_CAPTION = ("Annualized costs; run type and foresight caveats "
                      "apply - see pypsa-asset-economics.")

_warned_fallback = False


# ----------------------------------------------------------------- helpers
def elec_buses(n: pypsa.Network) -> pd.Index:
    """Buses on the electricity carrier (with a printed one-time fallback)."""
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


def energy_weights(n: pypsa.Network) -> pd.Series:
    """Snapshot weights for ENERGY sums (MWh = MW * weight)."""
    return n.snapshot_weightings.generators


def cost_weights(n: pypsa.Network) -> pd.Series:
    """Snapshot weights for COST sums (objective weighting)."""
    return n.snapshot_weightings.objective


def group_by_carrier(p: pd.DataFrame, carriers: pd.Series) -> pd.DataFrame:
    """Sum per-component time-series columns into per-carrier columns."""
    return p.T.groupby(carriers.reindex(p.columns)).sum().T


def effective_capacity(opt: pd.Series, nom: pd.Series) -> pd.Series:
    """Optimized capacity where the solver set one, else the input nominal."""
    return opt.where(opt > 0, nom)


def monthly_sum(s: pd.Series) -> pd.Series:
    """Calendar-month sums, tolerant of the pandas 'M' -> 'ME' alias change."""
    try:
        return s.resample("ME").sum()
    except ValueError:  # older pandas alias
        return s.resample("M").sum()


def grouped_generation(n: pypsa.Network, buses: pd.Index) -> pd.DataFrame:
    """Generation time series grouped by carrier, MW, on the given buses."""
    gens = n.generators[n.generators.bus.isin(buses)]
    p = n.generators_t.p[gens.index.intersection(n.generators_t.p.columns)]
    return group_by_carrier(p, gens.carrier)


def storage_dispatch(n: pypsa.Network, buses: pd.Index) -> pd.DataFrame | None:
    """Storage-unit dispatch grouped by carrier, MW, on the given buses."""
    su = n.storage_units[n.storage_units.bus.isin(buses)]
    if su.empty or n.storage_units_t.p.empty:
        return None
    p = n.storage_units_t.p[su.index.intersection(n.storage_units_t.p.columns)]
    return group_by_carrier(p, su.carrier)


def link_flows(n: pypsa.Network, buses: pd.Index) -> pd.DataFrame | None:
    """Net link injection per carrier at the given buses, MW time series.

    Positive = power injected INTO a bus (e.g. fuel cell), negative =
    withdrawn (e.g. electrolysis, exports). Iterates ALL link ports
    (bus0, bus1, bus2, ...) with their p0/p1/p2/... series.
    """
    import pandas as pd

    if n.links.empty or n.links_t.p0.empty:
        return None
    flows: dict = {}
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
        byc = group_by_carrier(inj, n.links.carrier)
        for c in byc.columns:
            flows[c] = flows.get(c, 0.0) + byc[c]
    return pd.DataFrame(flows) if flows else None


def net_carrier_flows(n: pypsa.Network, buses: pd.Index) -> pd.DataFrame:
    """Net per-carrier MW injection on `buses`: generation plus storage
    dispatch plus link injections across all ports."""
    net = grouped_generation(n, buses)
    for extra in (storage_dispatch(n, buses), link_flows(n, buses)):
        if extra is not None:
            net = net.add(extra, fill_value=0.0)
    return net


def total_load(n: pypsa.Network, buses: pd.Index) -> pd.Series:
    """Total load on the given buses, MW, from p (solved) or p_set inputs."""
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


def snapshots_per_week(n: pypsa.Network) -> int:
    """Snapshots covering 7 days, from the inferred snapshot frequency."""
    import pandas as pd

    sns = n.snapshots
    if len(sns) < 2:
        return len(sns)
    freq = pd.Series(sns).diff().median()
    return max(1, int(round(pd.Timedelta("7D") / freq)))


# ----------------------------------------------------------------- plots
def plot_energy_balance(n: pypsa.Network, ax: Axes) -> None:
    """#2 - per-carrier net energy on the electricity carrier. Must net to ~0."""
    import pandas as pd

    buses = elec_buses(n)
    w = energy_weights(n)
    # links contribute their net injection at elec buses across ALL ports
    # (bus0, bus1, bus2, ...) - see link_flows
    flows = net_carrier_flows(n, buses)
    parts = {c: float((flows[c] * w).sum()) for c in flows.columns}
    parts["load"] = -float((total_load(n, buses) * w).sum())
    s = pd.Series(parts).sort_values()
    s = s[s.abs() > max(1e-6, s.abs().max() * 1e-5)] / MWH_PER_TWH
    ax.barh(s.index, s.values, color=[color_for(c) for c in s.index])
    ax.axvline(0, color=INK, lw=0.8)
    net = s.sum()
    imbalanced = abs(net) > ENERGY_IMBALANCE_TOL * s.abs().max()
    ax.set_title(f"Energy balance nets to {net:+.3f} TWh"
                 + ("  [CHECK: should be ~0]" if imbalanced else ""))
    ax.set_xlabel("TWh (positive = supply)")
    ax.grid(axis="x", alpha=0.25)


def plot_price_duration(n: pypsa.Network, ax: Axes,
                        heatmap_ax: Axes | None = None) -> None:
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
                    color=ACCENT_BLUE, lw=0)
    ax.plot(x, srt.mean(axis=1), color=ACCENT_BLUE)
    ax.axhline(0, color=INK, lw=0.8)
    shed = n.generators[
        n.generators.carrier.astype(str).str.lower().str.contains("shed")]
    if not shed.empty:  # annotate the VOLL level set by shedding probes
        voll = float(shed.marginal_cost.max())
        ax.axhline(voll, color=ALERT_RED, lw=1.0, ls="--",
                   label=f"VOLL (shedding) = {voll:,.0f}")
        ax.legend(loc="upper right", fontsize=8)
    zero_share = float((lam.mean(axis=1) <= 0.01).mean()) * 100
    ax.set_title(f"Price duration - {zero_share:.0f}% of hours at ~0"
                 + ("  [CHECK]" if zero_share > ZERO_PRICE_SHARE_WARN else ""))
    ax.set_xlabel("share of hours [%]")
    ax.set_ylabel("EUR/MWh")
    if heatmap_ax is not None:
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


def _soc_by_carrier(e: pd.DataFrame, cap: pd.Series, carriers: pd.Series,
                    throughput_mwh: Callable) -> tuple[dict, dict]:
    """Capacity-weighted SOC series and equivalent-full-cycle counts per carrier.

    `throughput_mwh(cols)` returns the total charge+discharge energy for the
    given component columns, or None when it cannot be computed.
    """
    import pandas as pd

    series: dict = {}
    cycles: dict = {}
    for carrier in pd.unique(carriers):
        cols = e.columns[carriers == carrier]
        csum = float(cap[cols].sum())
        if csum <= 0:
            continue
        # capacity-weighted mean: sum(e) / sum(cap), not mean of ratios
        series[carrier] = e[cols].sum(axis=1) / csum
        thr = throughput_mwh(cols)
        if thr is not None:
            cycles[carrier] = thr / (2 * csum)
    return series, cycles


def plot_soc(n: pypsa.Network, ax: Axes, cycles_ax: Axes | None = None) -> None:
    """#5 - capacity-weighted normalized SOC per storage carrier.

    Pass `cycles_ax` for the companion equivalent-full-cycles bar
    (standalone figure only; the diagnostic panel shows SOC alone).
    """
    import pandas as pd

    series: dict = {}
    cycles: dict = {}
    if not n.stores_t.e.empty:
        e = n.stores_t.e
        cap = effective_capacity(n.stores.e_nom_opt,
                                 n.stores.e_nom).reindex(e.columns)

        def store_throughput(cols):  # charge+discharge MWh
            return float(e[cols].diff().abs().sum().sum())

        s, c = _soc_by_carrier(e, cap, n.stores.carrier.reindex(e.columns),
                               store_throughput)
        series.update(s)
        cycles.update(c)
    if not n.storage_units_t.state_of_charge.empty:
        soc = n.storage_units_t.state_of_charge
        su = n.storage_units
        cap = (effective_capacity(su.p_nom_opt, su.p_nom) * su.max_hours
               ).reindex(soc.columns)
        w = energy_weights(n)

        def unit_throughput(cols):
            pcols = cols.intersection(n.storage_units_t.p.columns)
            if not len(pcols):
                return None
            return float(n.storage_units_t.p[pcols].abs()
                         .mul(w, axis=0).sum().sum())

        s, c = _soc_by_carrier(soc, cap, su.carrier.reindex(soc.columns),
                               unit_throughput)
        series.update(s)
        for carrier, val in c.items():  # a carrier may span stores AND units
            cycles[carrier] = cycles.get(carrier, 0.0) + val
    if not series:
        raise ValueError("no storage in network")
    df = pd.DataFrame(series)
    for c in df.columns:
        ax.plot(df.index, df[c], label=str(c), color=color_for(c))
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("SOC [-]")
    end_drained = bool((df.iloc[-1] < SOC_DRAIN_LEVEL).any())
    ax.set_title("Storage state of charge (capacity-weighted)"
                 + ("  [CHECK: drains to 0 at horizon end - e_cyclic?]"
                    if end_drained else ""))
    if len(df.columns) <= SOC_LEGEND_MAX:
        ax.legend(ncol=min(3, len(df.columns)))
    if cycles_ax is not None and cycles:
        cs = pd.Series(cycles).sort_values()
        cycles_ax.barh(cs.index.astype(str), cs.values,
                       color=[color_for(c) for c in cs.index])
        cycles_ax.set_xlabel("equivalent full cycles "
                             "(throughput / 2 x energy capacity)")
        cycles_ax.set_title("Storage cycling over horizon")
        cycles_ax.grid(axis="x", alpha=0.25)


def plot_shedding(n: pypsa.Network, ax: Axes) -> None:
    """#11 - load shedding timeline; explicit empty state."""
    shed_gens = n.generators.index[
        n.generators.carrier.astype(str).str.lower().str.contains("shed")]
    cols = [g for g in shed_gens if g in n.generators_t.p.columns]
    if not cols:
        ax.text(0.5, 0.5, "no shedding generators present\n"
                "(run diagnose_infeasibility.py to add probes)",
                ha="center", va="center", color=MUTED_TEXT)
        ax.set_title("Load shedding - not instrumented")
        ax.set_xticks([])
        ax.set_yticks([])
        return
    ts = n.generators_t.p[cols].sum(axis=1)
    total = float((ts * energy_weights(n)).sum())
    ax.fill_between(ts.index, ts.values, color=ALERT_RED, lw=0)
    ax.set_ylabel("MW shed")
    ax.set_title(f"Load shedding - {total:,.0f} MWh total"
                 + ("  [FAILURE: investigate]" if total > 1e-3 else " (none)"))


def _stack_dispatch(ax: Axes, sns: pd.Index, net: pd.DataFrame) -> None:
    """Positive and negative per-carrier stacks; carriers appearing in both
    keep a single legend entry."""
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


def plot_dispatch_week(n: pypsa.Network, ax: Axes, start: int,
                       label: str) -> None:
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
    net = net_carrier_flows(n, buses)
    if net.empty:
        raise ValueError("no dispatchable flows on electricity buses")
    _stack_dispatch(ax, sns, net.loc[sns] / MW_PER_GW)
    load = total_load(n, buses).loc[sns] / MW_PER_GW
    ax.plot(sns, load.values, color=INK, lw=1.4, label="load")
    ax.set_title(f"Dispatch - {label}")
    ax.set_ylabel("GW")
    ax.legend(loc="upper left", ncol=4, fontsize=7.5)


def pick_weeks(n: pypsa.Network) -> list[tuple[int, str]]:
    """Auto-select (start index, label) for the peak-load, max-residual and
    min-residual load weeks. Week length follows the snapshot frequency."""
    buses = elec_buses(n)
    load = total_load(n, buses)
    gen = grouped_generation(n, buses)
    vre_cols = [c for c in gen.columns
                if any(k in str(c).lower() for k in VRE_KEYWORDS)]
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


def plot_capacity(n: pypsa.Network, ax: Axes) -> None:
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
    cap = pd.concat(rows).groupby(level=0).sum() / MW_PER_GW
    shed_mask = cap.index.astype(str).str.lower().str.contains("shed")
    excluded = bool(shed_mask.any())
    cap = cap[~shed_mask]
    if cap.empty:
        raise ValueError("no capacity data besides shedding slack")
    cap["added"] = (cap["p_nom_opt"] - cap["p_nom"]).clip(lower=0)
    cap = cap.sort_values("p_nom_opt", ascending=True).tail(MAX_BARS)
    colors = [color_for(c) for c in cap.index]
    ax.barh(cap.index, cap["p_nom"], color=colors, alpha=0.45)
    ax.barh(cap.index, cap["added"], left=cap["p_nom"], color=colors)
    ax.set_xlabel("GW")
    ax.set_title("Capacity - existing (faded) vs optimized addition")
    ax.legend(handles=[Patch(facecolor=SWATCH_LIGHT, label="existing"),
                       Patch(facecolor=SWATCH_DARK, label="added")])
    if excluded:
        ax.text(0.99, 0.02, "shedding capacity excluded (diagnostic slack)",
                transform=ax.transAxes, ha="right", va="bottom",
                fontsize=8, color=MUTED_TEXT)


def _carrier_costs(n: pypsa.Network) -> tuple[dict, dict]:
    """Annualized capex and opex per carrier, EUR/a, as two dicts."""
    w = cost_weights(n)
    capex: dict = {}
    opex: dict = {}
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
    return capex, opex


def _cost_headline(total_bn: float) -> str:
    """Human-scale system-cost string from a bn EUR/a total."""
    if total_bn >= 10:
        return f"{total_bn:.0f} bn EUR/a"
    if total_bn >= 1:
        return f"{total_bn:.2f} bn EUR/a"
    return f"{total_bn * 1e3:.0f} M EUR/a"


def plot_cost_stack(n: pypsa.Network, ax: Axes) -> None:
    """#7 - annualized capex + opex per carrier (lines: capex only)."""
    import pandas as pd
    from matplotlib.patches import Patch

    capex, opex = _carrier_costs(n)
    df = pd.DataFrame({"capex": pd.Series(capex, dtype=float),
                       "opex": pd.Series(opex, dtype=float)}
                      ).fillna(0) / EUR_PER_BN_EUR
    df = df[df.sum(axis=1) > 0].sort_values("capex", ascending=True).tail(MAX_BARS)
    if df.empty:
        raise ValueError("no cost data")
    colors = [color_for(c) for c in df.index]
    ax.barh(df.index, df["capex"], color=colors)
    ax.barh(df.index, df["opex"], left=df["capex"], color=colors, alpha=0.5)
    ax.legend(handles=[Patch(facecolor=SWATCH_DARK, label="capex (annualized)"),
                       Patch(facecolor=SWATCH_DARK, alpha=0.5, label="opex")])
    ax.set_xlabel("bn EUR / a")
    ax.set_title(f"System cost {_cost_headline(float(df.sum().sum()))} by carrier")


def plot_curtailment(n: pypsa.Network, ax: Axes) -> None:
    """#8 - monthly curtailed share per VRE carrier."""
    import pandas as pd

    pmax = n.generators_t.p_max_pu
    if pmax.empty:
        raise ValueError("no VRE availability series")
    gens = n.generators.loc[n.generators.index.intersection(pmax.columns)]
    cap = effective_capacity(gens.p_nom_opt, gens.p_nom)
    avail = pmax[gens.index] * cap
    cur = (avail - n.generators_t.p[gens.index]).clip(lower=0)

    plotted = False
    for carrier in pd.unique(gens.carrier):
        idx = gens.index[gens.carrier == carrier]
        a_m = monthly_sum(avail[idx].sum(axis=1))
        c_m = monthly_sum(cur[idx].sum(axis=1))
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


def plot_line_loading(n: pypsa.Network, ax: Axes,
                      top: int = DEFAULT_TOP_LINES) -> None:
    """#10 - |flow|/s_nom duration curves for the most loaded lines."""
    import numpy as np

    if n.lines.empty or n.lines_t.p0.empty:
        raise ValueError("no lines (or no line flow results) in network")
    cols = n.lines.index.intersection(n.lines_t.p0.columns)
    cap = effective_capacity(n.lines.s_nom_opt, n.lines.s_nom)
    cap = cap.reindex(cols).replace(0, float("nan"))
    loading = (n.lines_t.p0[cols].abs() / cap).dropna(axis=1, how="all")
    if loading.empty:
        raise ValueError("no lines with nonzero capacity")
    sel = loading.mean().sort_values(ascending=False).head(top).index
    x = np.linspace(0, 100, len(loading))
    for name in sel:
        ax.plot(x, loading[name].sort_values(ascending=False).values * 100,
                label=str(name), lw=1.2)
    ax.axhline(100, color=ALERT_RED, lw=0.8, ls="--")
    ax.set_xlabel("share of hours [%]")
    ax.set_ylabel("loading [% of s_nom]")
    ax.set_title(f"Line loading - {len(sel)} most loaded "
                 f"line{'s' if len(sel) != 1 else ''}")
    ax.legend(fontsize=7.5, ncol=2)


def plot_constraint_duals(n: pypsa.Network, ax: Axes) -> None:
    """#12 - shadow prices (mu) of global constraints."""
    gc = n.global_constraints
    if gc.empty:
        raise ValueError("no global constraints in network")
    if "mu" not in gc.columns or gc.mu.isna().all() or (
            n.buses_t.marginal_price.empty):  # mu defaults to 0 pre-solve
        raise ValueError("global constraints carry no duals (mu) - "
                         "network not solved?")
    mu = gc.mu.dropna()
    ax.barh(mu.index.astype(str), mu.values, color=ACCENT_BLUE)
    ax.axvline(0, color=INK, lw=0.8)
    ax.set_xlabel("shadow price mu [EUR per constraint unit]")
    ax.set_title("Global constraint duals")
    ax.text(0.99, 0.02, "sign: objective change per unit of constraint "
            "relaxation (e.g. EUR/tCO2 for a CO2 cap)",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=8, color=MUTED_TEXT)
    ax.grid(axis="x", alpha=0.25)


# ----------------------------------------------------------------- driver
# name -> (plot function, figsize, optional caption); the file number matches
# the chart-catalog.md entry number - keep in sync (SKILL.md Extending rule).
SINGLE_FIGURES = (
    ("02_energy_balance", plot_energy_balance, FIGSIZE_WIDE, None),
    ("06_capacity", plot_capacity, FIGSIZE_TALL, None),
    ("07_cost_stack", plot_cost_stack, FIGSIZE_TALL, COST_STACK_CAPTION),
    ("08_curtailment", plot_curtailment, FIGSIZE_WIDE, None),
    ("10_line_loading", plot_line_loading, FIGSIZE_WIDE, None),
    ("12_constraint_duals", plot_constraint_duals, FIGSIZE_WIDE, None),
)


def _panel_figure(n: pypsa.Network, plt: ModuleType) -> Figure:
    """00 - four-quadrant diagnostic panel; failed quadrants self-annotate."""
    fig, axs = plt.subplots(2, 2, figsize=FIGSIZE_PANEL)
    for ax, plot in zip(axs.flat, [plot_energy_balance, plot_price_duration,
                                   plot_soc, plot_shedding]):
        try:
            plot(n, ax)
        except Exception as e:  # noqa: BLE001
            ax.text(0.5, 0.5, f"unavailable:\n{str(e) or repr(e)}",
                    ha="center", va="center", color=MUTED_TEXT, fontsize=8)
    fig.suptitle("Diagnostic panel - read before any presentation figure",
                 fontweight="bold")
    return fig


def _weeks_figure(n: pypsa.Network, plt: ModuleType) -> Figure:
    """03 - one stacked dispatch row per auto-picked week."""
    sel = pick_weeks(n)
    width, row_height = FIGSIZE_WEEK_ROW
    fig, axs = plt.subplots(len(sel), 1, figsize=(width, row_height * len(sel)))
    axs = [axs] if len(sel) == 1 else list(axs)
    for ax, (start, label) in zip(axs, sel):
        plot_dispatch_week(n, ax, start, label)
    return fig


def _price_figure(n: pypsa.Network, plt: ModuleType) -> Figure:
    """04 - price duration curve plus month x hour heatmap."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=FIGSIZE_DUO)
    plot_price_duration(n, ax1, heatmap_ax=ax2)
    return fig


def _storage_figure(n: pypsa.Network, plt: ModuleType) -> Figure:
    """05 - SOC time series plus equivalent-full-cycles bar."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=FIGSIZE_DUO)
    plot_soc(n, ax1, cycles_ax=ax2)
    return fig


def render(n: pypsa.Network, outdir: str | Path, formats: Sequence[str],
           debug: bool = False) -> list[str]:
    """Render the full figure set into `outdir`; returns the names created."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    apply_style()
    made: list[str] = []
    skipped: list[tuple[str, str]] = []

    if n.buses_t.marginal_price.empty:
        print("=" * 72)
        print("WARNING: network appears unsolved - diagnostic figures only, "
              "results figures will be skipped/meaningless")
        print("=" * 72)

    def attempt(name: str, build: Callable[[], Figure]) -> None:
        try:
            fig = build()
            savefig(fig, outdir, name, formats)
            plt.close(fig)
            made.append(name)
        except Exception as e:  # noqa: BLE001
            skipped.append((name, str(e) or repr(e)))
            if debug:
                traceback.print_exc()

    # 00 diagnostic panel - ALWAYS first (references/diagnostics.md)
    attempt("00_diagnostic_panel", lambda: _panel_figure(n, plt))
    for name, plot, size, note in SINGLE_FIGURES:
        def single(plot=plot, size=size, note=note):
            fig, ax = plt.subplots(figsize=size)
            plot(n, ax)
            if note:
                caption(fig, note)
            return fig
        attempt(name, single)
    attempt("03_dispatch_weeks", lambda: _weeks_figure(n, plt))
    attempt("04_price_duration", lambda: _price_figure(n, plt))
    attempt("05_storage_cycling", lambda: _storage_figure(n, plt))

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
