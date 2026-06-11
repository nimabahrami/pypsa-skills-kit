# Chart catalog - what to draw, how, and the bug each chart catches

Entry format: PURPOSE | BUILD (PyPSA accessors) | CATCHES (failure exposed). Functions exist in scripts/standard_plots.py (output file number = entry number here) — copy or run. EXCEPTIONS: #1 = file 00 | #9 = manual | #11 = panel quadrant. ! Catalog and standard_plots.py MUST stay in sync — SKILL.md Extending rule.

## 1. Diagnostic panel (always first)
- 2x2: energy balance bar | price duration | normalized SOC | shedding timeline.
- CATCHES: 4 most common silent failures in one glance. Ships w/ every report.

## 2. Energy balance per carrier
- PURPOSE: supply vs withdrawal by technology, nets to ~0 per bus carrier.
- BUILD: `n.statistics.energy_balance(bus_carrier=...)` | fallback: group component time series by carrier w/ ENERGY weightings (`snapshot_weightings.generators`; objective weightings = costs only).
- CATCHES: sign-convention + snapshot-weighting bugs | phantom sources/sinks.

## 3. Dispatch stack (selected weeks)
- PURPOSE: stacked area, generation + storage discharge above 0 | charging + exports below | load line. 2-3 AUTO-SELECTED weeks: peak load | max residual load (load - VRE) | min residual — not a random January week.
- BUILD: `n.generators_t.p` grouped by carrier | storage from storage_units/stores | load from `n.loads_t.p`.
- CATCHES: simultaneous charge+discharge (exclusivity bug) | must-run violations | implausible merit order.

## 4. Price duration curve + monthly-hourly heatmap
- PURPOSE: sorted `n.buses_t.marginal_price` (mean across buses + min-max envelope) | heatmap month x hour of mean price.
- CATCHES: all-zero price hours (non-binding load | free energy) | missing VOLL spikes | unexplained negative blocks. ANNOTATE VOLL level + zero line.

## 5. Storage cycling
- PURPOSE: capacity-weighted normalized SOC per storage carrier, one axis (separate panels manually when daily cycling obscures seasonal traces) | equivalent-full-cycles bar per carrier.
- BUILD: `n.stores_t.e` | `n.storage_units_t.state_of_charge` | cycles = throughput / (2 * energy capacity).
- CATCHES: missing e_cyclic (drain-to-zero sawtooth at horizon end) | micro-cycling (missing wear cost) | seasonal store behaving daily (standing_loss typo).

## 6. Capacity: existing vs optimized
- PURPOSE: per-carrier bars split pre-existing (p_nom) vs added (p_nom_opt - p_nom). MW components only — Stores (MWh) excluded (energy capacity context = #5); never mix MW + MWh bars. Shedding carriers excluded (diagnostic slack), noted on axes.
- CATCHES: runaway single-technology expansion (missing p_nom_max | cost typo) | expansion exactly at p_nom_max everywhere (caps doing all the work).

## 7. Cost stack + economics
- PURPOSE: annualized CAPEX + OPEX stacked per carrier | system total in title. Companion: per-asset net margin from pypsa-asset-economics/scripts/revenue_report.py, diverging bar.
- CATCHES: carrier cost share >> energy share | negative margins on built technologies (annualization bug).

## 8. Curtailment
- PURPOSE: monthly curtailed energy share per VRE carrier (available = p_max_pu * p_nom_opt - dispatched).
- CATCHES: 0% curtailment w/ high VRE (free storage | balance bug) | extreme curtailment (missing transmission | storage options).

## 9. Network map (multi-node only — MANUAL, not in standard_plots.py)
- PURPOSE: `n.plot()` w/ line widths = loading | bus sizes = peak demand or capacity.
- CATCHES: islanded subnetworks | congestion on one corridor (clustering artifact -> pypsa-market-design before trusting prices).

## 10. Line loading duration curves
- PURPOSE: sorted |flow|/s_nom per line (or top-N congested).
- CATCHES: lines pinned 100% all year (missing expansion option) | never >30% (over-built input data).

## 11. Shedding / slack panel (diagnostic)
- PURPOSE: when shedding generators exist (diagnose_infeasibility.py probes | production VOLL shedders): shed power timeline (per-bus breakdown = manual). ! empty state must SAY "no shedding present" — absent panel != evidence.
- CATCHES: localized infeasibility | scarcity concentration.

## 12. Constraint duals
- PURPOSE: shadow prices of GlobalConstraints (CO2 caps etc.) | per investment period = one bar per period.
- BUILD: script covers `n.global_constraints.mu` only. Custom linopy duals = in-session from `n.model.constraints[name].dual` (model must be live — duals not persisted to netCDF).
- CATCHES: near-infeasible caps (5-digit CO2 price) | slack constraints user believed binding (cross-check: pypsa-custom-constraints verification step 5).
