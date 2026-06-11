# Hydrogen economics

## Utilization frontier
- electrolyzer tradeoff: run-hours up -> capex/kg down, marginal power hours cost more.
- optimal full-load hours ~3000-6000 h at today's capex.
- REPORT: LCOH as CURVE vs full-load hours, not point.

## LCOH decomposition (EUR/kg, 1 kg = 33.33 kWh LHV)
- LCOH = [annualized capex + FOM]/kg_annual + electricity_kWh/kg * P_el / 1000 + water/VOM.
- electricity_kWh/kg = 33.33 / efficiency_LHV (~50 kWh/kg at eff 0.67).
- ! grid fees/levies on power price often decide case. STATE: inclusion.
- heat revenue credit if heat recovery modeled -> pypsa-sector-coupling/references/hydrogen.md.

## Contract structures to test
- baseload PPA | as-produced VRE PPA + grid top-up | pure merchant.
- MODEL: as different price series | availability constraints on same asset network.
- RFNBO/additionality rules constrain WHEN green H2 draws power -> hourly matching = p_max_pu mask from contracted VRE profile.

## Sanity anchors
- ! merchant LCOH < ~2 EUR/kg at today's capex -> foresight bias | free water (marginal_cost 0) | unrealistically spiky price series.
- storage choice (cavern vs tank) shifts LCOH delivered-flat ~0.2-1 EUR/kg.
