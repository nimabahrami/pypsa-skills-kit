# Transport and flexible demand

## EV fleets (aggregated)
- BUILD: one "EV battery" bus + Store per region.
- charger = Link AC -> EV battery. SET time-varying p_max_pu = charging AVAILABILITY profile (share of fleet plugged in).
- driving demand = Load on EV bus with trip profile.
- V2G = discharge Link EV battery -> AC | capped by availability + user-set participation share (10-30% = defensible screening range).
- battery wear for V2G -> discharge link marginal_cost. Values: pypsa-physical-realism/references/ranges-storage.md (V2G 1-3 EUR/MWh) | derivation: pypsa-asset-economics/references/storage-revenue.md.
- SOC departure readiness: e_min_pu profile (e.g. >= 0.75 at 07:00) | custom constraint for fancier logic.

## Demand-side response (generic shiftable load)
- SPLIT: firm Load + flexible part.
- flexible part = Store with bounded energy debt (e_min_pu < 0) | paired shift-in/shift-out Links + recovery-time custom constraint.
- ! document implied payback period explicitly.
