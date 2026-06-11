# atlite - heat demand and COP

## Heat demand profile
Degree-day style from cutout temperature:
```python
hd = cutout.heat_demand(threshold=15.0)  # daily-ish profile per grid cell
```
- BUILD: aggregate to regions.
- SET: scale to ANNUAL national space-heating demand from statistics.
- profile shape = weather | level = energy balances. ! never both from atlite.

## Time-varying COP
- COP = f(T_source, T_sink). USE: empirical fits (Ruhnau et al. 2019, "When2Heat"): COP = a + b*dT + c*dT^2, dT = T_sink - T_source. ! b < 0, c > 0 (ASHP: 6.81 - 0.121*dT + 0.000630*dT^2) — COP FALLS with dT.
- air-source: T_source = ambient from cutout | ground-source: T_source = soil temperature.
- sink: 35C floor heating | 55-70C radiators = building stock assumption -> document.
- SET: feed as Link efficiency time series -> pypsa-sector-coupling/references/heating.md.

## Pitfalls
- ! constant COP overstates winter heat pump output during system stress.
- ! heat demand + VRE from DIFFERENT weather years -> destroys cold-calm correlation sizing backup capacity.
- ! district heating return temperatures != building-level -> separate COP series for large DH heat pumps.
