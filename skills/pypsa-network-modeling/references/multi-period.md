# Multi-period investment models

USE when optimizing investment across multiple years/periods (`n.investment_periods`, e.g. [2030, 2040, 2050]).

## Mechanics

- ! `n.optimize(multi_investment_periods=True)` REQUIRED. Without the flag: NO error, NO warning — build_year activity windows still apply, but `investment_period_weightings` (years + discounting) are silently DROPPED -> objective understated (verified 5.3x), capex/opex tradeoff distorted, investment decisions can flip.
- Snapshots -> MultiIndex (period, timestep). Components get `build_year` + `lifetime`. Asset active in period p if build_year <= p < build_year + lifetime.
- SET `n.investment_period_weightings`: `years` (period length) + `objective` (discount factors). SET BOTH. ! Default 0% discounting rarely intended. Typical social discount rate 2-7%/a. objective weighting = sum of discount factors over years each period represents.
- capital_cost = annualized; PyPSA charges every active period -> why annualized (not overnight) = convention everywhere.
- Brownfield: BUILD existing fleet with past build_year, p_nom_extendable=False, correct remaining lifetime. Source: powerplantmatching (pypsa-data-pipelines).
- Storage augmentation: new Store tranche per build_year, shared converter Links (degradation economics -> pypsa-asset-economics/references/storage-revenue.md).
- CO2 budgets per period: GlobalConstraint with `investment_period` set | custom constraint for cumulative-over-horizon budgets.
- Build-rate limits: Carrier `max_growth` (MW/period, absolute) + `max_relative_growth` (x previous-period new build) — ADDITIVE, multi-period only, new assets only. Per-period capacity caps: GlobalConstraint `tech_capacity_expansion_limit` w/ `investment_period`.

## Pitfall

- ! Perfect-foresight multi-period results != "bankable" asset story -> pypsa-asset-economics perfect-foresight warning, doubled. Native hedge vs uncertainty: `n.set_scenarios` stochastic (pypsa-solve-and-debug levers) — capacities robust across weighted dispatch scenarios.
