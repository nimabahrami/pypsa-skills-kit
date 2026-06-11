---
name: pypsa-solve-and-debug
argument-hint: [error message or symptom]
description: Solve PyPSA optimization models + fix failures. Triggers: solver selection/options | HiGHS | Gurobi | CPLEX | numerical issues | scaling | infeasibility | unboundedness | performance | temporal clustering | rolling horizon | spatial aggregation | interpret solved results | n.statistics | energy balances | shadow prices | optimization fails | status infeasible | status unbounded | runs too slowly | suspicious objective | results need interpretation/validation. PyPSA/linopy only — power-flow convergence of other tools (pandapower|PSS/E) is a different problem.
---

# PyPSA Solve & Debug

## Solver selection
- HiGHS = open-source default. LPs to ~1e7 nonzeros OK | MILP weaker.
- Gurobi/CPLEX/COPT = licensed. USE: barrier (method=2) + crossover=0 for big planning LPs. ! barrier duals w/o crossover valid but less clean -> price analysis: enable crossover.
- MILP (committable units | discrete expansion) -> orders-of-magnitude slowdown. SET: mip gap consciously. ! 1e-3 default gap hides real money in big objectives. ! MILP = no duals/prices -> fixed-commitment LP pricing run: pypsa-market-design.

## Failure triage, in order
0. PyPSA-Eur/Snakemake project -> READ logs/solve_network_* + solver log first; solver config under `solving:`; re-run one rule w/ `snakemake -call <target>` (pypsa-network-modeling/references/framework-workflows.md).
1. RUN: `n.consistency_check()` + pypsa-physical-realism validator FIRST. Most "solver problems" = data problems.
2. infeasible -> references/infeasibility.md + scripts/diagnose_infeasibility.py.
3. unbounded -> free profitable machine: extendable w/ capital_cost<=0 | neg marginal_cost w/o p_nom limit | efficiency>1 loop. RUN: realism validator (catches all 3).
4. numerical trouble (barrier stalls | "numerical difficulties") -> scale model. SET: cost coefficients within ~1e-2..1e6 of each other. ! avoid 1e9 "bigM" capacities -> use 'inf'-free explicit caps. Gurobi: NumericFocus=3, Aggregate=0.
5. slow -> references/performance.md (clustering | rolling horizon | aggregation).

## Native optimize() levers (use before hand-rolling)

- `optimize_with_rolling_horizon(horizon=, overlap=)` = native rolling horizon (traps: performance.md item 4).
- `fix_optimal_capacities()` -> two-stage: expansion run -> fixed-fleet operational/UC run. Manual equivalent: `p_nom_set`/`s_nom_set`/`e_nom_set` fix value while KEEPING extendable -> capacity duals survive (feeds pypsa-market-design long-run price decomposition).
- `n.set_scenarios({"low": 0.3, "high": 0.7})` (PyPSA >= 1.0) = native two-stage STOCHASTIC: capacities here-and-now, dispatch per-scenario; weights sum to 1, immutable once set; all frames gain outermost scenario index. + `n.set_risk_preference(alpha=, omega=)` = CVaR (omega=0 risk-neutral; incompatible w/ quadratic marginal cost). ! recourse = dispatch only | tech_capacity_expansion_limit NotImplemented under scenarios (1.0.x).
- `optimize(compute_infeasibilities=True)` -> IIS on infeasible (Gurobi only).
- `optimize(transmission_losses=N)` -> piecewise loss approximation, N tangents (3 = standard). ! requires finite s_nom_max on extendable branches; adds loss component to LMPs.
- `optimize(linearized_unit_commitment=True)` -> UC as pure LP: live duals/prices, fractional status, objective optimistic ~10-20%. Tightened only where start_up_cost == shut_down_cost.
- UC gotchas: `min_up/down_time` counted in SNAPSHOTS not hours (! sampled models shrink them by the sampling factor) | `up_time_before` default = 1 -> unit initially ON -> phantom infeasibility when forced output > load.
- `optimize_mga(slack=0.05, weights=..., sense=...)` = near-optimal alternatives ("within 5% of optimum, min/max tech X") on an already-solved network — robustness studies.
- `optimize_security_constrained(branch_outages=...)` = N-1 SCLOPF. ! cost scales lines x outages x snapshots; bridge-branch outage -> singular BODF.

## Result interpretation
READ: references/interpreting-results.md = n.statistics | energy balances | duals/shadow prices | curtailment | sanity battery. RUN: sanity battery on EVERY solved model before reporting numbers.

## Reproducibility
- SET: pin solver version + options in result metadata.
- ! barrier deterministic-ish | concurrent methods not -> degenerate optima flip dispatch between runs w/ identical objectives.
- USE: tie-breaking cost noise (1e-3 jitter) -> stabilizes plots.
