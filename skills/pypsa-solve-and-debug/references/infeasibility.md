# Infeasibility diagnosis

## Strategy ladder
1. RUN: realism validator. Usual suspects = zero-impedance lines | missing inflow | impossible e_min_pu profiles.
2. Load-shedding probe (workhorse): ADD high-cost shedding generator to every demand bus -> re-solve. RUN: scripts/diagnose_infeasibility.py. WHERE + WHEN shedding appears -> localizes binding shortage (bus | season | carrier). ADD: spill/curtailment dual for must-run surpluses (= negative shedding).
3. Solver IIS (Gurobi: computeIIS) on small/medium models -> minimal conflicting constraint set. READ: component names in it.
4. Bisection by constraint family: disable custom constraints -> global constraints -> unit-commitment, re-solve each. Family whose removal restores feasibility owns the bug.

## Root causes by symptom
- infeasible only winter weeks -> heat/hydro coupling: demand > capacity + storage reach. CHECK: e_cyclic interplay w/ seasonal storage.
- infeasible at first/last snapshot -> initial SOC vs cyclic constraints conflict.
- infeasible after adding custom constraint -> wrong sign/aggregation. GO: pypsa-custom-constraints verification checklist step 2 (read the LP).
- infeasible only w/ MILP -> min up/down times vs snapshot clustering mismatch.

## Load shedding in production runs?
- Industry practice = yes, at VOLL (3k-15k EUR/MWh) -> hard infeasibility becomes priced scarcity -> meaningful prices in shortage hours (pypsa-market-design).
- REPORT: shed energy explicitly.
