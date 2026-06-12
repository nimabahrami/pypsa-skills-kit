# Framework workflows - PyPSA-Eur | PyPSA-Earth (config-first discipline)

Applies when the project is a Snakemake workflow built on PyPSA (PyPSA-Eur, PyPSA-Earth, derived workflows) — detect: Snakefile + rules/*.smk + config/ + scripts/build_*.py. Networks are GENERATED artifacts. Facts below verified vs PyPSA-Eur v2026.02.0 — releases move keys; VERIFY against the checked-out repo's config.default.yaml + rules/, not memory.

## The one rule

! NEVER hand-edit generated networks (resources/ | results/ .nc) or generated data — the next `snakemake` run overwrites silently. Change CONFIG + INPUT DATA -> re-run the workflow. Hand-editing = the framework equivalent of editing compiled output.

## Repo anatomy (PyPSA-Eur)

- config/config.default.yaml = all options + defaults | config/config.yaml = user overrides (deltas only). EDIT the user file. ! config.yaml is schema-validated -> invalid keys hard-fail. Multi-scenario runs: `run: scenarios:` + config/scenarios.yaml.
- rules/*.smk (build_electricity | build_sector | solve_overnight | solve_myopic | solve_perfect | retrieve | postprocess ...) | scripts/ = build_*.py, prepare_network.py, add_electricity.py, cluster_network.py, solve_network.py.
- resources/{run}/ = intermediate (unsolved networks) | results/{run}/ = solved + outputs | logs/ + benchmarks/ per rule.
- data: per-dataset retrieve rules, versions pinned in `data:` config vs data/versions.csv (e.g. `data: costs: {source, version}` -> technology-data).

## Where each suite operation lands

- build/extend network (this skill) -> config sections: `electricity:` (carriers, extendable_carriers, transmission_limit — replaces old {ll} wildcard), `renewable:` (per-tech cutout/turbine/potentials), `lines:`, `links:`, `load:`. New tech = config entry + costs row, not n.add().
- scenario dimensioning -> wildcards: `clusters` (spatial) | `opts` / `sector_opts` (legacy shims, default empty — Co2L | Ep | {n}h still parse but translate INTO config) | `planning_horizons`. Native keys: `electricity: co2limit*` | `costs: emission_prices:` | `clustering: temporal: resolution_elec`. Foresight = `foresight:` overnight | myopic | perfect.
- custom constraints (pypsa-custom-constraints) -> scripts/solve_network.py extra_functionality + toggles under `solving: constraints:` (CCL | EQ | BAU | SAFE exist) + `custom_extra_functionality` hook — CHECK before hand-rolling.
- costs/data (pypsa-data-pipelines) -> `data: costs: version` pin; overrides via `costs: overwrites:` | `capital_cost:` | `marginal_cost:` | `custom_cost_fn` CSV; atlite cutouts configured, not hand-built. ! `costs:` fill-value defaults: fuel=0, CO2 intensity=0 -> tech missing from the costs CSV silently burns FREE carbon-free fuel; CHECK every carrier landed in the cost table.
- solving/debug (pypsa-solve-and-debug) -> `solving: solver:` config; failures: READ logs/ + solver log first; re-run single rule: `snakemake -call <target>` (snakemake >= 8.11).
- validation/reporting/economics -> READ-ONLY on resources/ | results/ .nc = plain PyPSA networks; validator + standard_plots apply unchanged.

## Pitfalls

- ! editing config.default.yaml instead of config.yaml -> changes lost on upstream update + un-diffable.
- ! mixing manual n.add() patches w/ workflow reruns -> non-reproducible network; patches belong in `custom_extra_functionality` | a script wired into a rule.
- ! cluster count is a RESULT dimension: comparing runs across different `clusters` values confounds spatial resolution w/ scenario (congestion/prices especially — pypsa-market-design aggregation rules).
- PyPSA-Earth = same discipline, different data sources (OSM-based grids | global cutouts); config keys differ in detail — same one rule applies.
