# Native optimize() levers - use before hand-rolling

- `optimize_with_rolling_horizon(horizon=, overlap=)` = native rolling horizon (3 verified traps: references/performance.md item 4).
- `fix_optimal_capacities()` -> two-stage: expansion run -> fixed-fleet operational/UC run. Manual equivalent: `p_nom_set`/`s_nom_set`/`e_nom_set` fix value while KEEPING extendable -> capacity duals survive (feeds pypsa-market-design long-run price decomposition).
- `n.set_scenarios({"low": 0.3, "high": 0.7})` (PyPSA >= 1.0) = native two-stage STOCHASTIC: capacities here-and-now, dispatch per-scenario; weights sum to 1, immutable once set; all frames gain outermost scenario index. + `n.set_risk_preference(alpha=, omega=)` = CVaR (omega=0 risk-neutral; incompatible w/ quadratic marginal cost). ! recourse = dispatch only | tech_capacity_expansion_limit NotImplemented under scenarios (1.0.x).
- `optimize(compute_infeasibilities=True)` -> IIS on infeasible (Gurobi only).
- `optimize(transmission_losses=N)` -> piecewise loss approximation, N tangents (3 = standard). ! requires finite s_nom_max on extendable branches; adds loss component to LMPs.
- `optimize(linearized_unit_commitment=True)` -> UC as pure LP: live duals/prices, fractional status, objective optimistic ~10-20%. Tightened only where start_up_cost == shut_down_cost.
- UC gotchas: `min_up/down_time` counted in SNAPSHOTS not hours (! sampled models shrink them by the sampling factor) | `up_time_before` default = 1 -> unit initially ON -> phantom infeasibility when forced output > load.
- `optimize_mga(slack=0.05, weights=..., sense=...)` = near-optimal alternatives ("within 5% of optimum, min/max tech X") on an already-solved network — robustness studies.
- `optimize_security_constrained(branch_outages=...)` = N-1 SCLOPF. ! cost scales lines x outages x snapshots; bridge-branch outage -> singular BODF.
