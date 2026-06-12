# atlite - VRE capacity factors

Canonical workflow = atlite's own worked notebooks (create_cutout | landuse-availability | historic-comparison) — do NOT restate; this file = the pitfalls those notebooks don't print.

- cutout: ERA5 via CDS API (needs ~/.cdsapirc); ! solar in Europe: SARAH-3 radiation beats ERA5 (known ERA5 radiation bias) — use `module=["sarah", "era5"]` | `cutout.wind(turbine="Vestas_V112_3MW", capacity_factor=True)` | `cutout.pv(panel="CSi", orientation="latitude_optimal", capacity_factor=True)`.
- regions + potentials: `cutout.availabilitymatrix(regions, excluder)` (the public API) + ExclusionContainer (CORINE/WDPA) -> per-region profiles + p_nom_max in one pass.

## Pitfalls

- ! ERA5 winds bias low in complex terrain -> bias-correct against actual generation (per-country correction factors = standard practice).
- ! turbine choice shifts CF >=10 points -> match class to era; modern low specific power for greenfield.
- solar `capacity_factor=True` = per-unit of panel capacity (DC-ish); inverter ratio assumptions = yours.
- offshore: SET hub height + offshore turbine; exclude depth via GEBCO.
- ! atlite CFs are GROSS: real parks lose ~10-15% (wake | availability | electrical | degradation) — net-down for site studies; country bias correction absorbs it in system studies. STATE which.
- ! one weather YEAR per study, consistent across all profiles -> SKILL.md discipline.
