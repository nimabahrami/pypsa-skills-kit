# Visual diagnostics - symptom -> chart -> root cause -> owner

RENDER diagnostic panel FIRST on every solved network. Then map below.
! Thresholds + root-cause logic OWNED by pypsa-solve-and-debug/references/interpreting-results.md (sanity battery) + pypsa-physical-realism (post-solve smells). This file maps symptom -> chart -> owner; root-cause hints here stay in sync w/ the owner — owner wins on conflict.

- energy balance bar not netting ~0 -> #2 -> sign convention | snapshot weightings -> pypsa-physical-realism, pypsa-network-modeling.
- flat zero price, long periods -> #4 -> non-binding load | free energy loop | over-supply -> pypsa-physical-realism validator.
- no VOLL spikes but shedding exists -> #4 + #11 -> shedder marginal_cost wrong | prices from wrong run -> pypsa-solve-and-debug.
- unexplained negative price blocks -> #4 -> must-run + subsidies, intended? -> pypsa-market-design.
- SOC sawtooth draining to 0 at horizon end -> #5 -> missing e_cyclic | cyclic_state_of_charge -> pypsa-network-modeling (storage-representation.md).
- seasonal store cycling daily -> #5 -> standing_loss | cost orders-of-magnitude off -> pypsa-physical-realism ranges-storage.md.
- BESS SOC micro-cycling noise -> #5 -> missing wear marginal_cost -> pypsa-asset-economics/references/storage-revenue.md.
- charge + discharge same hour in stack -> #3 -> charger/discharger exclusivity -> pypsa-custom-constraints tech-constraints.md.
- one carrier takes entire expansion -> #6 -> missing p_nom_max | cost typo (units!) -> pypsa-physical-realism, pypsa-data-pipelines cost-data.md.
- all expansion exactly at p_nom_max -> #6 -> caps binding everywhere, potentials too tight? -> pypsa-data-pipelines.
- 0% curtailment at high VRE share -> #8 -> free storage | balance bug -> pypsa-physical-realism.
- lines pinned 100% loading all year -> #10 -> no expansion option | clustering artifact -> pypsa-market-design, pypsa-network-modeling.
- shedding clustered one bus/season -> #11 -> localized shortage -> pypsa-solve-and-debug infeasibility.md.
- 5-digit CO2 shadow price -> #12 -> cap near-infeasible -> pypsa-solve-and-debug, pypsa-custom-constraints.
- custom-constraint dual identically 0 -> #12 -> vacuous constraint (empty selection) -> pypsa-custom-constraints verification.

Reporting rule: diagnostic finding goes INTO the report (annotated on relevant figure + 1 caption line), even when inconvenient. Report's job = make problems impossible to miss, not make the model look good.
