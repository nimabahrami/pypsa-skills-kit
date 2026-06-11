# Technology-specific constraints

## CHP back-pressure / extraction feasibility polygon
- extraction-condensing units: backpressure coefficient c_b + power-loss coefficient c_v. Per snapshot, on Link electricity output p_el + heat output p_heat -> recover from Link-p via efficiencies
- back-pressure line: p_el >= c_b * p_heat
- iso-fuel line: p_el + c_v * p_heat <= p_nom_el
- pure back-pressure units: equality p_el = c_b * p_heat
- READ: PyPSA-Eur solve_network.py = reference implementation, mirror it

## Electrolyzer minimum load
- exact: p >= min_pu * p_nom when "on" -> requires binary
- LP-friendly compromise: p >= min_pu * p_nom unconditionally (unit never off)
- OK for baseload-H2 studies | wrong for arbitrage studies. ! State which chosen

## Battery charger/discharger exclusivity
- strict exclusivity -> binaries
- LP-safe mitigation: p_charge + p_discharge <= p_nom (single inverter) -> removes most simultaneous cycling. ! Document residual slack
- ADD: couple p_nom of both links (capacity ratio recipe) -> optimizer can't size apart when hardware shared

## Hydro cascades
- upstream turbine outflow (+ delay) -> downstream reservoir: link StorageUnit-p_dispatch of plant u at t to inflow of plant d at t+tau
- tau in whole snapshots
- ! spillage must appear | droughts -> infeasible model

## EV charging windows / departure SOC
- USE profile-based bounds first: e_min_pu series -> SOC >= x at departure hours | availability in p_max_pu
- custom constraints only for fleet-level logic profiles can't express (e.g. total fleet energy recovered within N hours)

## Flow-based market coupling (zonal PTDF)
- sum_z PTDF_{cnec,z} * NP_z <= RAM_cnec per critical network element
- net position NP_z = built from zone balance variables
- formulation guidance -> pypsa-market-design/references/flow-based.md. Here: linopy mechanics only
