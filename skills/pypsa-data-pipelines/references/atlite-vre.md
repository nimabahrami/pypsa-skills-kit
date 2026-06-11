# atlite - VRE capacity factors

## Workflow
```python
import atlite
cutout = atlite.Cutout("europe-2019.nc", module="era5",
                       x=slice(-12, 35), y=slice(33, 72),
                       time="2019")
cutout.prepare()  # downloads ERA5 via CDS API - needs ~/.cdsapirc credentials

cf_wind = cutout.wind(turbine="Vestas_V112_3MW", capacity_factor=True)
cf_pv   = cutout.pv(panel="CSi", orientation="latitude_optimal",
                    capacity_factor=True)
```
- BUILD: aggregate to regions via availability matrix: `cutout.availabilitymatrix(regions, excluder)` (the public API; no `atlite.gis.compute_availability`).
- SET: land-use exclusions (CORINE/WDPA via ExclusionContainer) -> per-region profiles + p_nom_max potentials in one pass.

## Pitfalls
- ! ERA5 winds bias low in complex terrain -> bias-correct against actual generation (per-country correction factors = standard practice).
- ! turbine choice shifts CF >=10 points -> match class to era; modern low specific power for greenfield.
- solar `capacity_factor=True` = per-unit of panel capacity (DC-ish); inverter ratio assumptions = yours.
- offshore: SET hub height + offshore turbine; exclude depth via GEBCO.
- ! one weather YEAR per study, consistent across all profiles -> SKILL.md discipline.
