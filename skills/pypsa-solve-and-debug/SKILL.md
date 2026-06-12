---
name: pypsa-solve-and-debug
argument-hint: [error message or symptom]
description: Solve PyPSA optimization models + fix failures. Triggers: solver selection/options (HiGHS|Gurobi|CPLEX) | numerical issues | scaling | infeasibility | unboundedness | optimization fails | status infeasible/unbounded | runs too slowly | performance | temporal clustering | rolling horizon | spatial aggregation | interpret solved results | n.statistics | energy balances | shadow prices | suspicious objective | results need interpretation/validation. PyPSA/linopy only; n.pf non-convergence -> pypsa-physical-realism; other tools' power flow out of scope.
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

## Native optimize() levers

! READ references/optimize-levers.md BEFORE hand-rolling any of: rolling horizon (3 traps) | two-stage via fix_optimal_capacities / p_nom_set | stochastic set_scenarios + CVaR | IIS (Gurobi) | transmission_losses | linearized UC (LP prices) | UC gotchas (snapshots-not-hours, up_time_before=1) | MGA near-optimal | N-1 SCLOPF.

## Result interpretation
READ: references/interpreting-results.md = n.statistics | energy balances | duals/shadow prices | curtailment | sanity battery. RUN: sanity battery on EVERY solved model before reporting numbers.

## Reproducibility
- SET: pin solver version + options in result metadata.
- ! barrier deterministic-ish | concurrent methods not -> degenerate optima flip dispatch between runs w/ identical objectives.
- USE: tie-breaking cost noise (1e-3 jitter) -> stabilizes plots.
