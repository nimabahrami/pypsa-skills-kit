# Interpreting solved models

## n.statistics - first stop
- RUN: `n.statistics()` = capex/opex/supply/withdrawal/curtailment/market value per component-carrier.
- VERIFY: `n.statistics.energy_balance(bus_carrier="AC")` nets to ~0. Nonzero -> sign convention | weighting bug upstream.

## Sanity battery (RUN on EVERY solved model)
Visual form (pypsa-reporting `standard_plots.py`): checks 2/4/5 = figure 00 panel | check 3 = figure 08 | check 6 = figure 12 | check 1 = printed objective, no chart. Render first, then check thresholds here.
1. CHECK: objective magnitude = EUR order plausible for system size. Off-by-1e3 -> unit bug.
2. VERIFY: energy balance per carrier nets to zero.
3. CHECK: VRE curtailment share plausible (high single digits to ~20-30% in high-RES). 0% w/ lots of VRE -> free storage | balance bug.
4. CHECK: n.buses_t.marginal_price distribution. all-zero hours -> over-supply | non-binding load bug | VOLL-priced hours -> shedding active | negative hours -> must-run + subsidies, intended?
5. CHECK: storage SOC seasonal pattern sensible (caverns peak autumn) | round-trip energy conserved.
6. CHECK: GlobalConstraints duals. CO2 shadow price within believable EUR/t range for cap tightness. ! 5-digit CO2 price -> cap near-infeasible.

## Duals beyond prices
! default optimize() drops bound duals for non-extendable components -> RUN `n.optimize(assign_all_duals=True)`. PyPSA 1.x stores upper-bound duals <= 0.
- line/link s_nom duals = scarcity value per MW -> ranks transmission expansion. Congestion rents + LMP decomposition -> pypsa-market-design/references/congestion-analysis.md.
- p_nom_max duals = scarcity value of potential (land | cavern) -> which limits bite.
- custom constraint duals -> pypsa-custom-constraints verification step 5.

## Reporting discipline
- ATTACH: run type to every number = dispatch vs expansion | foresight | weather year | network resolution. Interpretation changes w/ each.
- Caveats owned by pypsa-market-design + pypsa-asset-economics.
