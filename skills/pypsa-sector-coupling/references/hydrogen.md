# Hydrogen chains

## Canonical chain
```
AC bus --electrolysis Link--> H2 bus --Store (cavern/tank)
                               |--fuel cell / H2 turbine Link--> AC bus
                               |--pipeline Links--> other H2 buses
                               |--Load (industry offtake)
```

## Electrolysis
- BUILD: Link AC -> H2. efficiency ~0.62-0.70 LHV (alkaline/PEM today) | ~0.74+ SOEC (SOEC wants heat input -> second bus).
- SET: marginal_cost nonzero (water + stack degradation, ~1-3 EUR/MWh_el). ! zero-VOM electrolyzer = classic unphysical model -> pypsa-physical-realism checks.
- heat recovery: bus2 = heat, efficiency2 ~0.1-0.2 if district heating nearby.

## Storage
- salt cavern: capex ~1-3 EUR/kWh, geography-constrained -> CAP e_nom_max by cavern potential per region.
- steel tank: ~10x-50x cavern cost -> USE when no salt formations.
- SET: standing_loss ~0. Compression electricity = separate Link input if material.

## Reconversion
- fuel cell efficiency ~0.5 | H2 OCGT ~0.38-0.42 | H2 CCGT ~0.55-0.60.
- round-trip elec -> H2 -> elec ~0.30-0.40. ! H2 cycling beating batteries for daily storage -> suspect parameter bug.

## Transport & derivatives
- pipelines = Links | bidirectional via two anti-parallel links | retrofit gas pipelines ~0.3-0.6x new-build cost.
- NH3 | methanol | FT = multi-input/multi-output Links chaining H2 + N2/CO2 buses.
- ! CO2 sourcing (DAC | point capture | biogenic) must be explicit bus -> else carbon accounting wrong. READ industry-biomass-ccs.md.
