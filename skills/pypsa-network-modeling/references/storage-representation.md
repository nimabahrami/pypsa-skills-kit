# Storage representation: StorageUnit vs Store + Links

Applies: BESS | TES (thermal) | PHS (pumped hydro) | hydrogen storage | ammonia tanks. Logic technology-agnostic.

## Decision rule

- P,E in FIXED ratio (4h battery | PHS with given reservoir) -> StorageUnit with `max_hours`.
- P,E sized INDEPENDENTLY (grid battery expansion planning | electrolyzer + cavern | TES + separate charger) -> Store (energy) + charge Link + discharge Link.
- Charge/discharge devices physically different (electrolyzer in, fuel cell out) -> always Store + Links.

## StorageUnit

- `max_hours` = energy capacity / power capacity. ! Extendable StorageUnit scales P+E together -> wrong for grid-battery capacity expansion.
- `efficiency_store` | `efficiency_dispatch` = per-direction. Round-trip = product.
- SET `cyclic_state_of_charge=True` for annual runs -> prevents free end-of-horizon drain.
- USE `inflow` (MW) + `spill` for hydro reservoirs.

## Store + Links pattern (expansion-study default)

```python
n.add("Bus", "battery", carrier="battery")
n.add("Store", "battery store", bus="battery", carrier="battery",
      e_nom_extendable=True, e_cyclic=True, capital_cost=c_energy,  # EUR/MWh/a
      standing_loss=1e-5)                                            # per hour
n.add("Link", "battery charger", bus0="AC", bus1="battery",
      p_nom_extendable=True, efficiency=0.96, capital_cost=c_power)  # EUR/MW/a
n.add("Link", "battery discharger", bus0="battery", bus1="AC",
      p_nom_extendable=True, efficiency=0.96, capital_cost=0)
```

Pitfalls:
- SET power capital_cost on ONE link | split deliberately. ! Duplicating on charger + discharger double-counts inverter.
- ! Charger + discharger can run simultaneously at negative marginal prices (burning energy "profitable") -> couple via custom constraint (pypsa-custom-constraints/references/tech-constraints.md) | accept knowingly.
- `standing_loss` = fractional per snapshot-hour: battery 1e-5/h | small hot water tank up to ~1e-2/h | large pit TES ~1e-4/h | H2 cavern ~0.
- Coupled sizing ratios (discharger p_nom = charger p_nom) -> custom constraint, not component attribute.

## E-/P- attribute mapping

- Store: `e_nom` | `e_nom_extendable` | `e_nom_min`/`e_nom_max` (geography/policy caps + floors) | `e_min_pu` | `e_max_pu` | `e_cyclic`.
- StorageUnit: energy = `p_nom * max_hours`; uses `state_of_charge_initial` | `cyclic_state_of_charge`.
