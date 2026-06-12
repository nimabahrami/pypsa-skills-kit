---
name: pypsa-data-pipelines
argument-hint: [input data needed]
description: Build realistic PyPSA input data. Triggers: atlite | cutouts | wind/solar capacity factors | renewable profiles | heat demand | heat pump COP time series | technology-data | cost assumptions | annuities | fuel price assumptions | gas price | EUA/carbon price assumptions | powerplantmatching | existing fleets | existing power plant data | ENTSO-E load | cross-border data | demand profiles | cost inputs | realistic numbers instead of placeholders.
---

# PyPSA Data Pipelines

Model honesty = input honesty. Maps input class -> canonical open-source pipeline + pitfalls.

## Script first

- RUN `python scripts/audit_inputs.py audit network.nc` = time-series FORENSICS: solar-at-night timezone bugs | leap/DST artifacts | placeholder/flat profiles | inverted seasonality | negative loads. Boundary: static parameters/structure = pypsa-physical-realism validator; SERIES feeding the model = this script.
- `python scripts/audit_inputs.py convert annuity|ttf|api2 ...` = executable unit conversions (owners: references/cost-data.md).
! PyPSA-Eur/Earth project -> these pipelines run INSIDE the workflow (retrieve rules | configured cutouts | `data: costs:` version pin); override via config, don't rebuild by hand (pypsa-network-modeling/references/framework-workflows.md).

## Input class -> pipeline
- wind/solar capacity factors -> atlite (ERA5/SARAH cutouts) -> references/atlite-vre.md
- heat demand, COP series -> atlite heat functionality -> references/atlite-heat.md
- technology costs, annuities, fuel + CO2 price series -> references/cost-data.md
- hydro inflow -> atlite `cutout.runoff` aggregated to plants -> NORMALIZE to national annual generation statistics (EIA | national TSO) — raw runoff levels are not generation. ! reservoir vs run-of-river split + calendar alignment w/ the weather year.
- existing plant fleet -> powerplantmatching -> below
- load time series -> ENTSO-E | OPSD -> below

## powerplantmatching (brownfield fleets)
- RUN: `import powerplantmatching as pm; df = pm.powerplants()` = cross-matched EU fleet: capacity, fuel, year.
- SET: explicit fuel -> carrier mapping.
- SET: build_year/lifetime for multi-period runs -> pypsa-network-modeling/references/multi-period.md.
- VERIFY: national totals vs statistics before use. ! matching gaps: small CHP, hydro.

## Load data
- USE: ENTSO-E transparency (API via entsoe-py) | OPSD time series.
- ! timezone: UTC internally, convert once.
- ! DST duplicate/missing hours.
- ! leap years (2020|2024|2028): 8784 h — weather, load + weightings must agree; silent 8760 truncation drops Feb 29 stress days.
- scaling historical profiles -> scenario annual demand: profile shape | level = separate decisions -> document both.

## Weather-year discipline
- USE: SAME weather year for VRE profiles + heat demand + inflow. ! else system-stress correlations (cold dark doldrums) vanish.
- RUN: several weather years for robust planning. ! single benign year underestimates firm capacity need.

## Validation handshake
- CHECK: every generated input via pypsa-physical-realism screening: CF ranges | COP ranges | demand totals vs statistics.
- generation = this skill | judgment = pypsa-physical-realism.
