---
name: pypsa-custom-constraints
argument-hint: [constraint to express or verify]
description: System-wide caps + custom PyPSA constraints - native GlobalConstraint types FIRST, linopy when they can't express it; always VERIFY it landed. Triggers: linopy | n.model | extra_functionality | custom constraints | GlobalConstraint | add a CO2 budget/cap | emission/production/expansion limits | solver formulations | reserve margins | cyclic storage rules | capacity coupling | CHP back-pressure | electrolyzer minimum load | hydro cascades | EV charging windows | standard component attributes cannot express behavior | was constraint actually applied | is constraint binding | "whether linopy got what it wants".
---

# PyPSA Custom Constraints (linopy)

Three steps, in order: 0. native GlobalConstraint type covers it? -> component, ZERO linopy (list below). 1. else express in linopy. 2. PROVE it landed.
! Never deliver without verification checklist. Silently-ignored constraint -> plausible wrong results.

## Step 0 - native first (zero linopy)

- GlobalConstraint types: `"primary_energy"` (CO2/byproduct cap) | `"operational_limit"` (carrier net production, e.g. gas/biomass budget) | `"transmission_volume_expansion_limit"` (MWkm) | `"transmission_expansion_cost_limit"` (EUR) | `"tech_capacity_expansion_limit"` (cap per carrier, optional per bus + investment_period; replaces deprecated per-bus-carrier nominal constraints). ! Don't hand-roll these — CCL-style caps = tech_capacity_expansion_limit. ! 1.0.x: tech_capacity_expansion_limit NotImplemented on stochastic (set_scenarios) networks
- Carrier growth limits (`max_growth` | `max_relative_growth`) = component attributes, also zero linopy -> pypsa-network-modeling/references/multi-period.md

## Attachment patterns

```python
# Pattern A - callback (works with n.optimize)
def extra_functionality(n, snapshots):
    m = n.model
    p = m.variables["Generator-p"]          # dims: (snapshot, name)
    m.add_constraints(..., name="my-constraint")

n.optimize(extra_functionality=extra_functionality, solver_name="highs")

# Pattern B - explicit (better for debugging)
n.optimize.create_model()
m = n.model
m.add_constraints(..., name="my-constraint")
n.optimize.solve_model(solver_name="highs")
```

## Variable name map (linopy labels)

- `Generator-p` | `Generator-p_nom` | `Link-p` | `Link-p_nom` | `Line-s` | `Line-s_nom` | `Store-e` | `Store-p` | `StorageUnit-state_of_charge` | `StorageUnit-p_dispatch` | `StorageUnit-p_store`
- ! component dimension in linopy vars = `name` (NOT the class): select subsets via `.sel(name=index)`. Capacity vars exist only for `*_nom_extendable=True`
- ! coefficient alignment: pandas Series w/ mismatched indices -> silent all-NaN. Per-component coefficients = `xr.DataArray(..., coords={"name": idx})` | per-snapshot = DataArray on dim `snapshot` (references/generic-patterns.md)
- ! fixed-capacity components = CONSTANTS, not variables -> mixed fleets: ADD constant part to constraint RHS/LHS explicitly

## Building expressions

- USE: linopy pandas/xarray algebra: `(p * weights).sum("snapshot") <= cap`
- time coupling: `p.shift(snapshot=1)` for ramp-like logic. ! mind first snapshot
- keep LINEAR | convex-quadratic if solver supports
- needs binaries (min up/down beyond committable, piecewise costs) -> state explicitly. CHECK: solver supports MILP -> pypsa-solve-and-debug
- common recipes -> `references/generic-patterns.md`
- tech-specific feasibility sets (CHP polygon, cascades, EV windows, charger/discharger exclusivity) -> `references/tech-constraints.md`
- PyPSA-Eur project -> constraints live in scripts/solve_network.py extra_functionality; CCL|EQ|BAU|SAFE exist already — CHECK before hand-rolling (pypsa-network-modeling/references/framework-workflows.md)

## VERIFICATION CHECKLIST (mandatory)

RUN: `scripts/inspect_model.py` | inline. Every step, every time:

1. existence — after model build: `"my-constraint" in n.model.constraints`. CHECK: dimensionality matches intent (one constraint | per snapshot | per component)
2. read LP — 2-bus/3-snapshot toy network: `n.model.to_file("debug.lp")` -> READ rows with constraint name. Catches sign errors + missing terms nothing else catches
3. solved status — solver returned `ok/optimal`. ! infeasible model "satisfies" nothing -> pypsa-solve-and-debug/references/infeasibility.md
4. numerical satisfaction — recompute constraint from `n.*_t` outputs w/ plain pandas. VERIFY: LHS <= RHS + 1e-4 (relative tolerance for big numbers)
5. bindingness + dual — `n.model.constraints["my-constraint"].dual`: nonzero dual = binding, economically active | zero dual on expected-binding constraint = slack -> wrong | genuinely non-binding. CHECK which. Dual over time/periods worth seeing -> pypsa-reporting chart-catalog #12
6. perturbation test — tighten RHS 10% -> re-solve. VERIFY: objective moves in expected direction. Cheapest end-to-end proof constraint steers optimum

## Pitfalls

- ! name collisions w/ PyPSA's own constraints -> silent fail | overwrite. USE: prefix custom names (e.g. `custom-`)
- ! constraints referencing `*_nom` vars of non-extendable components -> KeyError | worse: empty arrays -> vacuous (0 <= 0) constraints. Verification step 1 catches dimensionality giveaway
