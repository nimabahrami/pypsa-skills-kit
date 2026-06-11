---
name: pypsa-network-modeling
argument-hint: [what to build or change]
description: Build/edit PyPSA networks - structural correctness pre-optimization. Triggers: PyPSA model create|modify | components | buses | carriers | snapshots | capacity expansion | dispatch | dispatch optimization | transmission | generators | storage | lines | links | loads | investment periods | unit conventions | network topology | PyPSA-Eur | PyPSA-Earth | config.yaml of a PyPSA workflow | snakemake energy workflow | even without word "network".
---

# PyPSA Network Modeling

Scope: electricity-side PyPSA models, structurally correct before optimization. Heat|hydrogen|transport -> pypsa-sector-coupling. Parameter sanity -> pypsa-physical-realism.
! Project = Snakemake workflow (PyPSA-Eur | PyPSA-Earth)? -> READ references/framework-workflows.md FIRST — config-first discipline, never n.add() into generated networks.

## Units + signs (first)

- Power=MW | energy=MWh | costs=EUR | specific=EUR/MW or EUR/MWh.
- `marginal_cost` = EUR/MWh OUTPUT (primary bus; bus0 for links). Static OR snapshot series (`n.generators_t.marginal_cost`) on Generator|Link|StorageUnit|Store — volatile fuel/CO2 -> series; sourcing -> pypsa-data-pipelines. ! `capital_cost` static only; per-period variation via build_year tranches.
- `capital_cost` = ANNUALIZED EUR/MW (Store: EUR/MWh) per investment period. ! Overnight CAPEX in one-year model -> investment cost overstated ~10-20x.
- Annualize: `capital_cost = overnight_cost * annuity(r, lifetime) + FOM`; `annuity(r, n) = r / (1 - (1 + r) ** -n)`.
- Generator: positive p = injection. Load: positive p_set = consumption.
- Link: `p1 = -efficiency * p0`; p0 = withdrawal at bus0. Losses: SET efficiency < 1, not second component.
- Line/transformer per-unit impedances relative to bus `v_nom`.

## Build workflow

- BUILD carriers first: `n.add("Carrier", ...)`, include `co2_emissions` for fossil fuels -> constraints + statistics group by carrier.
- BUILD buses with explicit `carrier` (AC|DC|heat|H2|...). 1 bus = 1 energy-balance equation. Merge buses only if pypsa-market-design confirms aggregation won't distort measurement.
- SET snapshots -> SET `n.snapshot_weightings` if snapshot > 1h. Three columns = three quantities: `objective` = COSTS (+ marginal_price normalization) | `generators` = accounted ENERGY (CO2/primary-energy GlobalConstraints, e_sum limits) | `stores` = ELAPSED TIME (SOC continuity, standing_loss^w). ! Setting only `objective` -> CO2 cap silently loosened by the sampling factor (constraint counts 1/w of real emissions, CO2 price -> 0, dispatch flips fossil) + storage losses understated w-fold. consistency_check does NOT catch it. SET ALL THREE.
- BUILD components. SET `p_nom_extendable=True` only where investment = decision. SET nonzero `capital_cost` + finite `p_nom_max` (land/resource limits) on every extendable -> else unbounded-free expansion.
- Dispatch-only: SET fixed `p_nom` + `p_nom_extendable=False` everywhere. ! `committable=True` + extendable: invalid through PyPSA 1.0.x (consistency_check rejects) | >=1.1.0 allowed via big-M (`committable_big_m`, auto M = 10x peak load). Discrete unit sizes -> `p_nom_mod > 0` = integer module count -> MILP (pypsa-solve-and-debug).
- RUN `n.consistency_check()` before every solve.

## Component selection

- Generator = un-modeled fuel -> bus energy. USE `p_max_pu` time series for VRE availability | `p_min_pu` for must-run.
- storage: fixed P/E ratio -> StorageUnit | independent P,E sizing -> Store+2Links. ! READ references/storage-representation.md before any storage add (top structural error: BESS|TES|PHS|H2).
- Line = AC + impedance (Kirchhoff voltage constraints) | Link = controllable point-to-point (HVDC|converters|cross-carrier). READ references/grid-transmission.md for impedance, s_max_pu, HVDC patterns.
- GlobalConstraint = system-wide caps, 5 native types: "primary_energy" (CO2) | "operational_limit" (carrier production budget) | "transmission_volume_expansion_limit" (MWkm) | "transmission_expansion_cost_limit" (EUR) | "tech_capacity_expansion_limit" (per carrier|bus|period). Anything fancier -> pypsa-custom-constraints skill.

## Multi-period / investment

- READ references/multi-period.md if >1 investment period (overlapping build years | discounting | `n.investment_periods`).

## Pre-handback checks

- CHECK loads on correct carrier bus (! heat demand on AC bus).
- CHECK `p_max_pu` = per-unit of p_nom, not MW.
- CHECK extendables: capital_cost != 0, p_nom_max present. `p_nom_min` = policy/brownfield build floors | Store: `e_nom_min`/`e_nom_max`.
- VERIFY snapshot weightings sum = period length (year -> 8760 | ! leap year -> 8784; align weather year, load data, annualization).
- CHECK e_cyclic | cyclic_state_of_charge set on annual storage runs -> else optimizer drains storage free by final snapshot.
