---
name: pypsa-sector-coupling
argument-hint: [sector or technology]
description: Non-electric tech + multi-energy systems in PyPSA. Triggers: heat pumps | thermal energy storage | district heating | CHP | hydrogen chains | electrolysis | electrolyzers | H2 storage | reconversion | pipelines | EVs | V2G | biomass | industry demand | CCS | DAC | heat | hydrogen | transport | industry | second energy carrier | multi-output Links | COP | sector coupling | Link efficiency exceeds 1.
---

# PyPSA Sector Coupling

Grammar: Bus per carrier per location | Link = universal converter | Store = carrier inventory. Most bugs = one of these misused.

## The three patterns

- converter = Link (elec -> heat | elec -> H2 | H2 -> elec). ! efficiency > 1 legal ONLY for un-modeled environmental energy harvest (heat pump COP); otherwise = free-energy bug -> pypsa-physical-realism flags it.
- multi-output converter = Link + bus2/efficiency2 (+ bus3...). Cases: CHP (elec + heat) | electrolyzer + heat recovery | Fischer-Tropsch (fuel + heat). efficiency_i = output_i per unit bus0 input.
- CO2 accounting: BUILD explicit CO2 buses where CCS | DAC | synfuels appear. CO2 as output -> negative efficiency to "co2 atmosphere" store = standard PyPSA-Eur trick.
- inventory = Store on carrier bus (heat tank | H2 cavern | EV fleet battery state). SET standing_loss for thermal decay.

## Carrier/bus design rules

- one heat bus per temperature level. ! residential ~60°C != industrial steam — never one bus.
- one H2 bus per location -> connect via pipeline Links (efficiency ~1 minus compression elec as separate input) | shipping chains.
- ! never put carrier-X demand on carrier-Y bus "because it balances" -> prices + statistics meaningless.

## Reference routing — READ before modeling sector

- heating -> references/heating.md: heat pumps (time-varying COP) | resistive heaters | TES | CHP back-pressure | district heating topology | building retrofits as virtual generators.
- hydrogen -> references/hydrogen.md: electrolysis/storage/reconversion chains | cavern vs tank | pipelines | derived fuels (NH3, methanol, FT).
- transport -> references/transport.md: EV fleets | charging availability | V2G | demand-side response as shiftable load.
- industry -> references/industry-biomass-ccs.md: process heat/feedstock demand | biomass potentials as constrained Generators/Stores | CCS + DAC chains.

## Cross-skill handoffs

- operational coupling (CHP feasibility polygon | electrolyzer min load | EV charging windows) = constraints -> pypsa-custom-constraints.
- plausible COPs | efficiencies | losses -> pypsa-physical-realism ranges files. Its validator WARNs: CO2-chain tech (CCS|DAC|synfuels) w/o explicit co2 bus (Link carrier co2_emissions NOT counted by GlobalConstraints) | >1 heat load carrier per bus.
- COP/heat-demand time series generation -> pypsa-data-pipelines (atlite-heat.md).
- LCOH | heat-pump-vs-boiler business cases -> pypsa-asset-economics.
