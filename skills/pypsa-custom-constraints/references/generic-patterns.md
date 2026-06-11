# Generic constraint recipes (linopy)

All snippets assume `m = n.model` inside extra_functionality | after create_model().
! PyPSA 1.x linopy variable dims = `(snapshot, name)` — component dimension is called `name`, NOT the component class; capacity vars (`*-p_nom`) exist only for extendables, dim `(name,)`. Select via `.sel(name=...)`.
! NEVER divide/multiply two pandas Series w/ different indices inside an expression (snapshot-index / component-index -> all-NaN union). Build per-component coefficients as `xr.DataArray` on dim `name`, per-snapshot ones on dim `snapshot`.

## CO2 budget (GlobalConstraint insufficient, e.g. cumulative multi-period)
```python
import xarray as xr
em = n.carriers.co2_emissions  # t/MWh_thermal
gens = n.generators.query("carrier in @em.index[@em>0].tolist()")
p = m.variables["Generator-p"].sel(name=gens.index)
factor = xr.DataArray(em[gens.carrier].values / gens.efficiency.values,
                      coords={"name": gens.index})      # t/MWh_el per generator
w = xr.DataArray(n.snapshot_weightings.generators)      # dim: snapshot
m.add_constraints((p * factor * w).sum() <= budget_t,
                  name="custom-co2-cumulative")
```

## Capacity reserve margin (firm capacity >= peak * (1 + margin))
```python
firm = n.generators.query("carrier in @firm_carriers")
ext = firm.query("p_nom_extendable").index
fix = firm.query("~p_nom_extendable").p_nom.sum()
p_nom = m.variables["Generator-p_nom"].sel(name=ext)
m.add_constraints(p_nom.sum() >= peak_load * (1 + margin) - fix,
                  name="custom-reserve-margin")
```
! fixed-fleet constant moved to RHS — classic omission.
! per-carrier/per-bus capacity caps or floors need NO linopy: GlobalConstraint `type="tech_capacity_expansion_limit"` (sense ">=" gives minima). Hand-roll only cross-carrier mixes like this one.

## Spinning reserve (headroom on online units, linear approximation)
- per snapshot: sum_i (p_nom_i * p_max_pu_i - p_i) >= R
- ! extendable units -> variable*variable product. Linearize: reserve fixed share | USE committable units

## Capacity ratio coupling (size A = k * size B)
```python
pA = m.variables["Link-p_nom"].sel(name="fuel cell")
pB = m.variables["Link-p_nom"].sel(name="electrolysis")
m.add_constraints(pA - k * pB == 0, name="custom-h2-ratio")
```

## Annual energy quota (e.g. >= x% renewable supply)
- sum RE generation w/ generator weightings >= share * total load (constant RHS)

## Budget constraint on total CAPEX
- sum(capital_cost_i * p_nom_i) <= B over extendable components
- ! units = ANNUALIZED EUR. Overnight budget -> de-annualize first
- ! transmission-only budget needs no linopy: GlobalConstraint `"transmission_expansion_cost_limit"` | volume cap (MWkm): `"transmission_volume_expansion_limit"`. Hand-roll only mixed gen+grid budgets.
