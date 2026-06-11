# Performance tactics

Ordered by accuracy cost, cheapest distortion first:
1. Solver tuning: barrier + crossover=0 | threads | presolve on. Free.
2. Spatial clustering: pypsa.clustering.spatial (k-means/HAC on network). ! changes congestion -> market-design skill must sign off for price studies.
3. Temporal: segmentation (tsam typical periods + inter-period storage linking) beats every-Nth-hour sampling. ! plain N-hour averaging smooths ramps + flatters storage. ALWAYS keep storage continuity across segments.
4. Rolling horizon (dispatch only): USE native `n.optimize.optimize_with_rolling_horizon(horizon=, overlap=)` — carries SOC + chains ramp/UC history across windows automatically.
   ! 3 verified traps: (a) DISABLE e_cyclic / cyclic_state_of_charge first — per-window cyclicity silently discards the carried SOC; (b) `n.objective` afterwards = LAST window only -> recompute total cost from dispatch; (c) it mutates `*_initial` attributes permanently.
   ! seasonal storage (hydro reservoirs | H2 caverns) + short windows = myopic draining — window sees no value in holding energy for next season. IMPOSE end-of-window SOC targets | water values from a prior full-horizon LP.
   = limited-foresight method asset-economics requires. One implementation, two purposes.
5. Decomposition (Benders | ADMM per period): only for genuinely huge multi-period capacity expansion. ! prototype-grade in most stacks -> budget engineering time.

Too-slow study order: tune solver -> cluster time -> cluster space -> reduce scope. Reducing scope honestly beats torturing full model.
