---
name: pypsa-physical-realism
argument-hint: [network.nc or model dir]
description: Validate PyPSA models against physical/engineering reality - parameter ranges | topology | free energy | cost sanity (zero-marginal-cost electrolyzer = canonical bug). Triggers: check/review/lint/sanity-check a PyPSA network | pre-delivery checklist | is this plausible / does this look right | before solving for real decisions | suspicious results | zero or negative prices everywhere | one technology built without limit | storage cycling that beats thermodynamics | AC-feasibility of optimized dispatch (n.pf | n.lpf, explicit PyPSA context only). PyPSA only; stack ambiguous? VERIFY pypsa deps first.
---

# PyPSA Physical Realism

Model solves != model right. Skill = linter: deterministic checks -> judgment on rest.

## Script first

```
python scripts/validate_network.py path/to/network.nc   # or CSV folder
python scripts/validate_network.py network.nc --strict   # warnings fail too
```

- CHECK: structural invariants + parameter ranges. Exits nonzero on ERROR.
- REPORT: findings grouped by severity + fix each.
- input TIME-SERIES forensics (timezone | leap | placeholder profiles) = pypsa-data-pipelines scripts/audit_inputs.py — run both before real decisions.

## Script invariants = review checklist

- no free energy: Link efficiency > 1 only ambient-heat carriers (heat pumps) | Generator efficiency in (0, 1] | no negative standing losses.
- no free machines: extendable -> capital_cost > 0. ! Overnight-CAPEX-sized capital_cost -> flagged probably-not-annualized (generators + links). committable+extendable -> ERROR on PyPSA 1.0.x | WARN >=1.1.0 (big-M).
- real inputs cost money: conversion tech (electrolysis | fuel cells | methanation | DAC | ...) with marginal_cost == 0 -> flag. Water, sorbents, stack/catalyst degradation real. Zero-VOM defensible only for wires.
- topology: no orphan buses | no loads on suspicious carriers | no zero-impedance lines | no bidirectional lossy links (p_min_pu < 0 with efficiency < 1).
- time accounting: snapshot weighting columns consistent | cyclic storage set on full-year runs.
- carbon accounting: fossil carriers carry co2_emissions; 0 -> flag. CO2-chain tech (CCS|DAC|synfuels) w/o explicit co2 bus -> flag (! Link carrier co2_emissions NOT counted by GlobalConstraints). >1 heat load carrier per bus -> temperature-mixing flag.
- range screening: efficiencies | standing losses | costs inside ranges from references files below.

## Judgment checks beyond script

- merged buses hiding congestion relevant to THIS question? -> pypsa-market-design.
- VERIFY: VRE capacity factors per region. Europe: wind onshore 0.20-0.40 | offshore 0.35-0.55 | solar 0.10-0.22. Wrong cutout year | unit confusion shows here first.
- post-solve smells: storage round-trips creating energy | shadow prices 0 all hours (load not binding) | single technology absorbs whole expansion (missing p_nom_max | cost typo). Visual form -> pypsa-reporting diagnostic panel.
- LOPF = MW-only -> optimized dispatch may be AC-infeasible. Post-solve n.pf/n.lpf screens + applicability gate + escalation boundary -> references/power-flow-checks.md.

## Range references

- READ: file matching technology under review.
- references/ranges-generation.md -> thermal plants | VRE | hydro.
- references/ranges-storage.md -> BESS | TES | PHS | H2 storage.
- references/ranges-conversion.md -> electrolyzers | fuel cells | heat pumps | CHP | methanation | DAC.
- references/ranges-grid.md -> lines | transformers | HVDC | losses.
- ! Ranges = SCREENING bounds, not procurement data. Outside range -> question, not auto-reject.
- VERIFY: project-grade numbers vs PyPSA technology-data repo (pypsa-data-pipelines/references/cost-data.md).

## Extending

- new technology -> add ranges-file row AND rule in scripts/validate_network.py (GEN_EFF_RANGES / LINK_EFF_RANGES / CONVERSION_KEYWORDS). ! Both, or skill/script drift.
