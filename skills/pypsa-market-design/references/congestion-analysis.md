# Congestion analysis - economics, not just loading

Boundary: loading screens (|flow|/s_nom) = pypsa-reporting #10 | constraint mechanics = pypsa-custom-constraints | this file = congestion ECONOMICS on solved networks. "Congestion" here = market concept (price formation + money flows), not the reliability concept (loading near rating).

## Getting the duals at all

- ! default `n.optimize()` leaves `n.lines_t.mu_upper` EMPTY for non-extendable lines. RUN `n.optimize(assign_all_duals=True)` | read `n.model.constraints[...].dual` in-session.
- ! sign convention: PyPSA 1.x/HiGHS stores upper-bound duals <= 0. Textbook mu >= 0 = -(stored mu_upper). Every formula below uses textbook mu.

## Quantities

- nodal price spread dL(t) = lambda_bus1(t) - lambda_bus0(t).
- ! spread != per-line congestion: nonzero spread ANYWHERE -> some constraint binds SOMEWHERE; in a mesh, NON-binding lines also carry spread (KVL). Never infer a line is congested from its own spread — CHECK that line's mu.
- Link (mc=0, eff=1) binding: dL = mu. General Link: eff * lambda_bus1 - lambda_bus0 - mc = mu — marginal_cost and efficiency both enter; "spread = congestion" only after netting them out.
- Line in a mesh: dL != that line's mu in general (cycle constraints redistribute duals).
- congestion rent: per-branch term = sum_t dL(t) * flow(t) * w(t). ! per-line terms can be NEGATIVE (loop flow against the price gradient) — only the SYSTEM sum is a rent: sum_branches = load payments - generator revenues = sum_l mu_l * F_l (verified identity).
- capacity scarcity: extendable s_nom/p_nom duals = EUR/MW per period (year iff weightings sum to a year) of one more MW -> RANK for expansion (pypsa-solve-and-debug/references/interpreting-results.md duals section).
- LMP decomposition: lambda_i = lambda_ref - sum_l PTDF_{l,i} * mu_l (textbook mu >= 0; reference-bus choice shifts the energy/congestion split — REPORT spreads, not absolute components). Loss component = 0 lossless DC | nonzero w/ `optimize(transmission_losses=N)`.
- ! reported `marginal_price` = raw dual / `snapshot_weightings.objective` (post-processing) — comparing raw linopy duals to n.buses_t.marginal_price mismatches by the weighting.
- redispatch volume/cost (zonal) -> two-stage recipe + bid-markup cost formula: references/flow-based.md (single owner — do not restate here).
- congestion income (cross-zone, EU): price spread * scheduled exchange on the interconnector. Screening only.

## Workflow

1. RUN: pypsa-reporting #10 (line loading duration) -> WHERE/WHEN binding.
2. SOLVE w/ assign_all_duals=True -> COMPUTE per-branch terms `(lam[bus1] - lam[bus0]) * n.lines_t.p0 * w` + system sum.
3. RANK capacity duals + rents -> expansion candidates.
4. zonal redispatch quantification -> flow-based.md.

## Pitfalls

- ! zonal/copper-plate run -> intra-zone congestion invisible -> rents structurally underestimated. Aggregation rules: SKILL.md.
- ! spatial clustering concentrates flows on equivalent corridors -> rents on clustered lines = artifact-prone; STATE network resolution w/ every rent number.
- congested hours w/ ~0 spread -> degenerate optimum | parallel free capacity. CHECK duals before calling it a bug.
- continuous expansion: optimally-expanded lines RETAIN rent = annualized capex (sum_t mu_t = capital_cost — cost recovery, not under-investment). Rent EXCEEDING capex recovery | s_nom_max dual > 0 -> potential exhausted. Integer/lumpy expansion -> either sign possible.
