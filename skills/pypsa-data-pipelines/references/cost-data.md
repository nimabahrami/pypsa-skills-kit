# Cost data - technology costs, fuel + CO2 prices

## Source
- github.com/PyPSA/technology-data = versioned CSVs per projection year (costs_2030.csv, costs_2040.csv, ...).
- columns: investment | FOM | VOM | lifetime | efficiency per technology; literature source per value.
- USE: TAGGED RELEASE; record version in model metadata. ! numbers move between releases.

## From raw costs to capital_cost
```python
def annuity(r, n):
    return r / (1 - (1 + r) ** -n)

capital_cost = (annuity(discount_rate, lifetime) + FOM_fraction) * investment
# EUR/MW/a (EUR/MWh/a for energy capacities)
```
- discount_rate: social 2-4% -> system planning | WACC-like 5-10% -> investor-perspective runs. ! choice changes technology rankings -> state it.
- SET: one currency-year price base; deflate/inflate before mixing sources.
- ! CSV units vary (EUR/kW, EUR/m3, EUR/(tCO2/h)) -> convert explicitly. Unit bugs = top source of absurd expansion results.

## Crosswalk
- BUILD: explicit mapping table technology-data name -> your carrier names, kept in repo.
- ! implicit string matching breaks on renames between releases.

## Fuel + CO2 prices (volatile -> time series, not scalars)

Two encodings — pick ONE per plant, never mix:
- (a) direct Generator: `n.generators_t.marginal_cost = fuel(t)/eff + co2(t)*EF/eff + VOM` (EUR/MWh_el).
- (b) fuel-bus (sector-coupled): fuel price on supply Generator at fuel bus (`marginal_cost = fuel_price(t)`, EUR/MWh_th) | VOM only on conversion Link | CO2 via carrier `co2_emissions`.
- ! formula (a) on a Link -> every term mis-scaled by 1/eff | (a) on a plant behind a priced fuel bus -> fuel double-counted.
- ! CO2 same-instrument rule: never represent the SAME instrument twice — EUA price in marginal_cost AND ETS cap double-prices (cap dual stacks on price). Distinct stacked instruments (UK CPS / national floor + ETS cap) may coexist — state both. Backtest/dispatch -> exogenous EUA | normative expansion -> cap.

Sources by study type:
- backtest -> historical spot: TTF/THE gas | API2 coal | EUA.
- forward dispatch -> EEX/ICE forward curves (monthly granularity standard).
- SYSTEM expansion -> deterministic low/central/high scenario sets (TYNDP | IEA WEO) = industry reporting standard; explicit hedging-under-uncertainty -> native `n.set_scenarios` stochastic, PyPSA >= 1.0 (pypsa-solve-and-debug/references/optimize-levers.md); asset valuation needs multi-scenario / P50-P90 price sets -> pypsa-asset-economics Bias-1.

Conversions (! direction matters):
- TTF quotes HHV -> LHV basis: ÷0.901 (+11%) to match LHV efficiencies (ranges-generation.md convention).
- API2 = USD/t @ 6000 kcal/kg NAR -> ÷6.978 = USD/MWh_th -> FX (currency-year discipline above).
- EUA already EUR/tCO2 — no conversion.

Screening emission factors EF (t/MWh_th; canonical: pypsa-physical-realism/references/ranges-generation.md):
- coal 0.34 | lignite 0.40 | gas 0.20 | oil 0.27.
