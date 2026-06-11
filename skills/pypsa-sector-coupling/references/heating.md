# Heating technologies

## Heat pumps
- BUILD: Link electricity bus -> heat bus, efficiency = COP > 1. ! ONLY legitimate efficiency > 1 besides other ambient-heat devices.
- ! COP must be TIME-VARYING (source-temperature dependent) -> pass series via `efficiency` in link_t. Generate from temperature data -> pypsa-data-pipelines/references/atlite-heat.md.
- ! constant-COP models overstate winter output exactly when it matters.
- screening COPs: air-source 2.0-3.8 seasonal | ground-source 3.0-5.5 (owner: pypsa-physical-realism ranges-conversion.md) | decentral units < large DH heat pumps using rivers/sewage (3-4 even in winter).
- sink temperature: COP at 35°C floor heating >> 70°C radiators.

## Resistive heaters / electric boilers
- = Link electricity -> heat, efficiency 0.95-1.0. Cheap capital | expensive operation -> pair with TES to absorb negative-price hours.

## Thermal energy storage (TES)
- BUILD: Store on heat bus + charger/discharger Links (charger only if heat source feeds directly).
- SET standing_loss per hour: small tank 1e-3 to 1e-2 | large pit / seasonal storage 1e-5 to 3e-4 (owner: ranges-storage.md).
- ! seasonal TES needs e_cyclic=True + full-year snapshots.

## CHP
- = multi-output Link: bus0=fuel | bus1=electricity (efficiency) | bus2=heat (efficiency2).
- ! bare multi-link -> optimizer picks any output mix. Real back-pressure / extraction-condensing plants obey feasibility polygon (c_b, c_v coefficients) -> custom constraints: pypsa-custom-constraints/references/tech-constraints.md.

## District heating
- BUILD: separate "urban central heat" bus per network.
- distribution losses = Link efficiency 0.85-0.92 | load uplift.
- DH unlocks large heat pumps + CHP + pit TES that decentral buses cannot host. ! keep decentral and central heat buses distinct.
