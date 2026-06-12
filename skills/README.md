# PyPSA Skill Suite

9 self-contained skills, industry-grade PyPSA modeling. 1 folder = 1 skill (SKILL.md + references/ + scripts/) -> install|test|version independently.
Human contributors: READ NOTATION.md first (symbol grammar | edit rules | sync contracts — never model-loaded, prose allowed there).

## Architecture

Split by operation/concern, never by technology|package. Technologies (BESS|heat pumps|TES|H2|EVs|CHP|hydro|CCS) = reference files inside skills, scoped to that skill's aspect only.

- pypsa-network-modeling = build/extend network -> references/storage-representation.md | grid-transmission.md | multi-period.md | framework-workflows.md
- pypsa-sector-coupling = represent non-electric tech -> references/heating.md | hydrogen.md | transport.md | industry-biomass-ccs.md
- pypsa-custom-constraints = express behavior linopy-side + verify it landed -> references/generic-patterns.md | tech-constraints.md
- pypsa-physical-realism = physical sanity -> references/ranges-*.md + scripts/validate_network.py
- pypsa-market-design = market representation -> references/flow-based.md | reserves-ancillary.md | congestion-analysis.md + scripts/price_diagnostics.py
- pypsa-asset-economics = defensible business case -> references/storage-revenue.md | multi-market-dispatch.md | hydrogen-economics.md | heat-economics.md | vre-ppa.md
- pypsa-data-pipelines = realistic input sourcing -> references/atlite-vre.md | atlite-heat.md | cost-data.md + scripts/audit_inputs.py
- pypsa-solve-and-debug = solve failures + result meaning (numbers/thresholds; figures -> pypsa-reporting) -> references/infeasibility.md | performance.md | interpreting-results.md | optimize-levers.md
- pypsa-reporting = render solved results: diagnostic panel + deliverable figures -> references/design-system.md | chart-catalog.md | diagnostics.md + scripts/standard_plots.py

## Scaling rule

! New technology (ammonia|DSR|gravity storage) NEVER adds skill. ADD: entries to 2-4 reference files + assertions in pypsa-physical-realism/scripts/validate_network.py.
! New chart type NEVER adds skill. ADD: chart-catalog.md entry + plot_* function in standard_plots.py + CARRIER_COLORS row.
Only a new OPERATION (rare — reporting was one) may add a skill. Skill count frozen at 9 -> always-in-context overhead frozen.

## Token economics (JIT hydration)

- L1 always loaded: 9 names + descriptions, ~1250 tokens (measured 2026-06-12; re-measure after description edits).
- L2 on trigger: 1 SKILL.md = thin router.
- L3 on demand: ~1 reference file/task. Scripts execute outside context -> only output enters.

## Trigger testing

- WRITE: 2-3 realistic prompts per skill. VERIFY: right skill loads, only that one.
- USE boundary prompts, e.g. "add a CO2 budget to my hydrogen model" -> custom-constraints (single door for ALL system-wide caps; its step 0 = native GlobalConstraint before linopy), never sector-coupling|realism.
- ! "sanity-check my solved model" -> solve-and-debug (battery) | physical-realism acceptable; NOT reporting unless a figure/deliverable is requested.
- ! "build a sector-coupled model" loads network-modeling AND sector-coupling routinely -> merge skills, demote split to references.

## Domain guard + suite tooling

- Scope = PyPSA/linopy ONLY. PyPSA = planning/scheduling engine — AC voltage detail | dynamics | protection | distribution feeders = other tools (pandapower|PSS/E|ANDES|OpenDSS; the PowerSkills suite covers those). In-suite: n.pf/n.lpf screening of optimized dispatch only; escalation-boundary owner = physical-realism references/power-flow-checks.md.
- stack ambiguous ("plot my results", no tool named) -> RUN `python skills/detect_stack.py <dir>`: exit 0 = PyPSA | 2 = other stack, do NOT apply pypsa-* skills | 3 = ask the user.
- `evals.json` = trigger-precision cases (positives + adversarial negatives). Test description edits against it.
- `test_scripts.py` = suite smoke test: compiles every script, exercises detect_stack, solves a synthetic net, runs validator + plots. RUN before every release.

## Compatibility

- Verified against: PyPSA 1.0.7 | pandas 2.3 | matplotlib 3.10 | HiGHS 1.13 | linopy 0.6.
- Version-sensitive prose facts name their version inline ("PyPSA 1.x stores ..."). New PyPSA major -> RUN test_scripts.py + re-verify version-sensitive claims (list: NOTATION.md Compatibility policy).

## Maintenance cadence (every ~6 months or on dependency major release)

1. RUN `python skills/test_scripts.py` -> 0 failures.
2. RUN `python skills/run_evals.py` -> trigger precision report; fix collisions before adding triggers.
3. CHECK screening ranges (physical-realism ranges-*.md + wear costs + fuel/CO2 levels) vs latest technology-data release; record release tag checked.
4. Re-measure L1 token count if any description changed -> update Token economics above.
5. CHECK PyPSA changelog for renamed attributes/APIs referenced in prose.

## Conventions

- EUR | MW | MWh | tCO2.
- `capital_cost` = ANNUALIZED EUR/MW (Store: EUR/MWh) per investment period.
- Reference ranges = screening values for sanity checks, not procurement data. VERIFY project numbers against PyPSA technology-data repo.
