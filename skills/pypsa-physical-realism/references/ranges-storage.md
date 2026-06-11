# Screening ranges - storage

Format: tech -> per-direction eff | round-trip | standing_loss /h | energy capex (annualized EUR/MWh/a) | typical duration.

- Li-ion BESS -> 0.92-0.975 | 0.85-0.95 | 1e-6 - 1e-4 | 7k-20k | 1-8 h.
- PHS -> 0.85-0.92 | 0.72-0.85 | ~0 (evap small) | site-specific | 6-24 h+.
- Hot water tank (decentral) -> 0.9-1.0 thermal | - | 1e-3 - 1e-2 | 300-1500 | hours-days.
- Pit / seasonal TES -> 0.9-1.0 | - | 1e-5 - 3e-4 | 30-300 | weeks-months.
- H2 salt cavern -> ~1 (store) | - | ~0 | 100-600 | seasonal.
- H2 steel tank -> ~1 | - | ~0 | 3k-15k | days.
- Molten salt (CSP/Carnot) -> charge/discharge via converters | - | 1e-4 - 1e-3 | 600-2500 | 6-14 h.

## Rules

- round-trip > 0.97, electrochemical, grid scale -> flag (validator ROUND_TRIP_MAX = 0.97).
- StorageUnit max_hours outside [0.25, 1000] -> probably MWh/MW mix-up.
- cavern e_nom_max: geography-capped. ! 500 TWh caverns in region without salt formations = missing-potential bug, not result.
- battery inverter (power) cost -> ONE link only in Store+Links setups.
- V2G cycling wear -> 1-3 EUR/MWh in discharge marginal_cost (calendar-dominated shallow-cycling assumption). Grid-BESS wear range + derivation formula owned by pypsa-asset-economics/references/storage-revenue.md — reconcile via that formula.
