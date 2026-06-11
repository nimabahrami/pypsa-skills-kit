# Industry, biomass, CCS / DAC

## Industry demand
- BUILD: Loads on correct carrier bus: electricity | H2 (DRI steel, ammonia) | process heat by temperature band | methanol/naphtha feedstock.
- flat profiles acceptable for continuous processes. ! never put steam demand on electricity bus.

## Biomass
- = constrained resource: Generator | Store drawn down over year, with e_sum_max / annual cap from potentials. ! NOT unlimited fuel.
- SPLIT: sustainable residues vs energy crops -> separate carriers, different costs + CO2 attributes.

## CCS / DAC carbon accounting
- ! explicit buses, always.
- BUILD buses: "co2 atmosphere" (Store, e_min_pu < 0 allowed -> counts negative emissions) | "co2 stored" (Store, sequestration potential cap, EUR/tCO2 cost).
- point-source capture: multi-link -> capture_rate 0.85-0.95 share of process CO2 to "co2 stored" | remainder to "co2 atmosphere". Capture energy penalty = electricity/heat inputs.
- DAC = Link consuming electricity + heat -> output to "co2 stored" | synfuel chains.
- ! CO2 GlobalConstraint and explicit CO2-bus system = ALTERNATIVES. Mixing without care -> double-counts emissions.
