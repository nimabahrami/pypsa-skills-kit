# Screening ranges - conversion technologies

Format: tech -> efficiency (output/input) | VOM (nonzero!) | notes.

- Electrolysis AEL/PEM -> 0.62-0.70 H2_LHV/el | 1-3 EUR/MWh_el | heat byproduct 0.1-0.2 optional.
- Electrolysis SOEC -> 0.74-0.84 | 1-3 | needs heat input bus.
- Fuel cell -> 0.45-0.55 el/H2 | 1-3 | heat byproduct possible.
- H2 OCGT / CCGT -> 0.38-0.42 / 0.55-0.60 | 2-5.
- Heat pump air -> COP 2.0-3.8 (seasonal, time-varying!) | 1-3 EUR/MWh_th | ! eff > 1 LEGITIMATE here.
- Heat pump ground/large DH -> COP 3.0-5.5 | 1-3.
- Resistive heater / e-boiler -> 0.95-1.0 | 0.5-1.5.
- Gas boiler -> 0.90-1.05 (LHV; >1 = condensing vs LHV basis) | 1-3.
- CHP gas -> el 0.30-0.45 + heat 0.30-0.50, sum <= ~0.92 | 3-5 | needs polygon constraints.
- Methanation -> 0.77-0.80 CH4/H2 | 2-5 | CO2 input bus required.
- Fischer-Tropsch -> 0.6-0.7 fuel/H2 | 3-8 | CO2 + el inputs.
- Haber-Bosch (NH3) -> 0.85-0.90 NH3/H2 (+el) | 2-6.
- DAC -> 1.5-2.5 MWh_el+th per tCO2 | sorbent cost > 0 | output = co2 stored bus.

## Hard rules

- efficiency > 1 only ambient/waste-heat harvesters (heat pumps) | anything else -> bug.
- marginal_cost == 0 on any row above -> flag (water, catalysts, sorbents, stack wear exist). ! Zero-VOM electrolyzer = canonical unphysical model.
- multi-output links: sum of energy efficiencies respects energy balance (<= ~1 plus harvested ambient heat).
