# Flow-based market coupling and redispatch

## NTC vs FBMC

- NTC = fixed bilateral exchange limits. ! direction-DEPENDENT (A->B != B->A): one Link w/ p_min_pu = -NTC_reverse/p_nom, p_max_pu = 1 @ p_nom = NTC_forward — symmetric NTC = modeling shortcut, distorts congestion income.
- FBMC = constrains ZONE NET POSITIONS via PTDFs on critical network elements + contingencies (CNECs).
- per CNEC: sum_z PTDF_{cnec,z} * NP_z <= RAM_cnec.
- FBMC couples all borders simultaneously = actual EU Core mechanism.

## Implementation

- BUILD: nodal grid model -> derive PTDFs per sub-network: `n.determine_network_topology()` -> `sub.calculate_PTDF()` / `sub.PTDF` (no Network-level method).
- SET: node-to-zone aggregation via GSK (generation shift key) = flat | pro-rata to capacity | merit-order. ! results GSK-sensitive -> state it.
- BUILD: zonal market network (zone buses).
- SET: net-position variables (zone balance) + CNEC constraints via linopy. READ: pypsa-custom-constraints/references/tech-constraints.md.
- RAM = Fmax - FRM - F0. ! minRAM rules (70% target) materially change results.

## Redispatch workflow

- RUN: zonal market model solve.
- SET: fix market dispatch (n.generators_t.p -> p_set | fixed bounds).
- BUILD: on NODAL network, paired up/down redispatch generators per unit. ! STATE the dispatch-sign convention: down-units dispatch NEGATIVE (p_min_pu<0, p_max_pu=0). Pay-as-bid compensation: up at marginal_cost + spread | down at -(marginal_cost - spread) on the negative-p unit. Cost-based (fuel-savings netting): down at +(marginal_cost - spread). Sign flip inverts the redispatch-cost number regulators see — say which regime.
- outputs regulators care about = redispatch volume + cost.
- shortcut: pypsa.Network spot-vs-redispatch examples in PyPSA documentation ("redispatch" example) -> mirror structure.

## Sanity anchors

- zonal price spreads vanish <=> interconnectors uncongested. CHECK: duals on NTC links.
- FBMC prices between copper-plate + NTC outcomes for most hours -> if not, suspect GSK | RAM units (! MW vs % confusion common).
