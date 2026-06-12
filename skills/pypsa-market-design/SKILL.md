---
name: pypsa-market-design
argument-hint: [market question]
description: Model electricity market structures in PyPSA. Triggers: market design | price formation | zonal vs nodal pricing | copper-plate | flow-based market coupling vs NTC | redispatch | redispatch cost | bidding zones | bidding-zone aggregation | reserve markets | ancillary markets | reading prices from duals | congestion pricing/rent/income/cost | LMP decomposition | price spread between buses/zones | can buses be merged | single bus modeling | why model prices differ from exchange prices.
---

# PyPSA Market Design

- PyPSA native = NODAL, perfectly competitive, marginal-cost market.
- RUN `python scripts/price_diagnostics.py solved.nc` FIRST on any solved run = MILP no-duals trap detection | floor/bid-stack plausibility | zero-price share | per-branch congestion rents + system sum.
- Scope: EU market architecture (FBMC | redispatch | EUR). US two-settlement / ORDC scarcity adders not covered — the nodal core + duals logic transfers, the adders don't.
- Bus marginal prices = duals of energy balance.
- Real markets = deliberate distortions of baseline -> choose + encode distortion matching study question.

## Aggregation decision (single bus / merged buses)

- Safe iff intra-zone congestion non-binding for question asked.
- CHECK: what study measures (prices? RES integration? transmission need?).
- prices | congestion | redispatch as outputs -> keep nodes | calibrated zonal layout. ! copper-plate invalidates them.
- only system energy/CO2 totals -> single bus per zone OK. STATE: assumption explicitly in deliverable.
- 2 components, 1 bus, identical price exposure (battery co-located w/ PV behind one connection) -> pricing unchanged, feasibility changed (shared grid connection limit). BUILD: shared link.

## Market layouts

- nodal -> full network, Lines w/ impedances, s_max_pu = security proxy.
- zonal NTC -> 1 bus/zone, Links w/ NTC capacities between zones. Crude | standard EU screening.
- zonal flow-based (FBMC) -> zone buses + PTDF constraints on critical network elements limiting net positions. READ: linopy formulation references/flow-based.md. Constraint mechanics -> pypsa-custom-constraints.
- two-stage market + redispatch -> solve zonal dispatch -> fix -> resolve nodal feasibility w/ up/down redispatch units. READ: references/flow-based.md (redispatch section).

## Prices and interpretation

- n.buses_t.marginal_price = EUR/MWh dual of nodal balance.
- scarcity hours price at VOLL only if load shedding w/ VOLL cost modeled -> else infeasible instead of pricing scarcity.
- ! EU exchange bid floor = -500 EUR/MWh (DA; cap dynamic ~4-5k). Model prices below the floor = subsidy/must-run ENCODING artifact — cap the bid, never report sub-floor prices as market outcomes.
- capacity-expansion runs -> long-run-equilibrium prices (capex enters duals via binding capacity constraints) | dispatch-only runs -> short-run prices. ! never compare either 1:1 w/ day-ahead outturns w/o stating which built.
- ! committable units = MILP = NO duals -> marginal_price empty/meaningless. Two fixes: (a) native middle path `optimize(linearized_unit_commitment=True)` = pure LP, live prices, fractional commitment, objective optimistic ~10-20% | (b) industry pricing run: solve MILP -> FIX commitment (committable=False + p_min_pu/p_max_pu scaled by solved status) -> re-solve LP -> duals from THAT. Non-convex costs unrecovered by LP prices = why real markets pay uplift — model prices never show it; STATE when comparing.
- storage/hydro opportunity costs -> automatic via SOC constraint duals.
- congestion ECONOMICS (rents | redispatch cost | LMP decomposition | expansion ranking) -> READ references/congestion-analysis.md. Loading screens = pypsa-reporting #10.

## Reserves / ancillary

- READ: references/reserves-ancillary.md -> reserve products, co-optimization vs sequential, when reserve revenues -> pypsa-asset-economics.
- deliverable claims reserve revenue/feasibility -> STATE reserve representation level (1-4 of reserves-ancillary.md).

## Sequential energy markets

- sequential energy markets for ASSET valuation (DA/ID/imbalance) -> pypsa-asset-economics/references/multi-market-dispatch.md | system-side sequential clearing (zonal + redispatch) stays here (references/flow-based.md).
