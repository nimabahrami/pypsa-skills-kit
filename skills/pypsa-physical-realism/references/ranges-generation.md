# Screening ranges - generation

Efficiencies = electrical, LHV basis. capital_cost below = ANNUALIZED EUR/MW/a screening order of magnitude. VERIFY costs vs technology-data repo.

Format: tech -> efficiency | VOM EUR/MWh_el | annualized capex EUR/MW/a | notes.

- CCGT -> 0.55-0.63 | 3-5 | 50k-90k | fuel cost separate via fuel price/eff.
- OCGT -> 0.35-0.42 | 2-4 | 30k-60k | peaker; high marginal cost expected.
- Coal -> 0.38-0.46 | 4-8 | 110k-200k | co2_emissions ~0.34 t/MWh_th.
- Lignite -> 0.35-0.43 | 5-9 | 130k-220k | ~0.40 t/MWh_th.
- Nuclear -> 0.33-0.37 | 8-14 | 350k-700k | min load 0.4-0.5 if committable.
- Wind onshore -> 1.0 (p_max_pu carries resource) | 1-3 | 70k-110k | CF 0.20-0.40 EU.
- Wind offshore -> 1.0 | 2-5 | 130k-220k | CF 0.35-0.55.
- Solar PV -> 1.0 | 0.5-2 | 25k-55k | CF 0.10-0.22 EU.
- Run-of-river -> 0.9 (turbine) | 0-2 | given fleet | inflow series required.
- Biomass -> 0.25-0.45 | fuel-dominated | 150k-350k | ! constrained resource.

## Red flags

- VRE efficiency != 1 AND p_max_pu profile -> double-derating.
- thermal generator marginal_cost 0 -> fuel forgotten.
- CF outside range -> wrong cutout year | wrong turbine class | per-unit/MW confusion.

## CO2 (t/MWh_thermal)

- coal 0.34 | lignite 0.40 | gas 0.20 | oil 0.27 | biomass 0 only under explicit sustainability accounting.
