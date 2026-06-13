---
name: pypsa-asset-economics
argument-hint: [asset + revenue question]
description: Asset business cases + revenues w/ PyPSA. Triggers: revenue | profit | business case | arbitrage | merchant operation | capture price | market value | LCOH | LCOE | bankability | BESS arbitrage | TES arbitrage | revenue stacking | intraday | imbalance | multi-market | electrolyzer utilization | heat pump operating economics | VRE capture prices | PPAs | degradation cost | calendar vs cycle aging cost | SOH revenue impact | capacity fade economics | is a wear/degradation cost plausible. ! three bias corrections (foresight | merchant | fees) mandatory before quoting investable numbers.
---

# PyPSA Asset Economics

- PyPSA default answers "what minimizes SYSTEM cost", not "what does THIS asset earn".
- ! correct (or disclose) three biases in every revenue number.

## Bias 1 - perfect foresight
- optimizer sees all prices/weather in advance.
- perfect-foresight storage arbitrage overstates revenue ~10-30% (daily cycling) | more for multi-day strategies.
- Fixes, increasing effort:
1. report perfect-foresight numbers WITH label + haircut range.
2. rolling horizon dispatch (24-48h windows, limited lookahead) -> native `optimize_with_rolling_horizon` + its 3 traps: pypsa-solve-and-debug/references/performance.md item 4.
3. dispatch vs FORECAST price series -> settle vs outturn. Multi-market sequence (DA -> ID -> imbalance) -> references/multi-market-dispatch.md.

## Bias 2 - system vs merchant optimization
- system-cost run -> asset dispatched to help SYSTEM; merchant asset maximizes own profit vs prices.
- price-TAKING asset setup:
1. SOLVE: system model WITHOUT asset (or asset marginal) -> price series.
2. BUILD: single-asset network = one bus + ONE bidirectional market-interface Generator (`p_min_pu=-1`, `marginal_cost = +price(t)`) + asset -> solve. Cost linearity: buy (p>0) pays price | sell (p<0) earns price — one value, both directions. Objective = merchant profit max. ! `-price(t)` = sign-INVERTED on an interface (paid to buy); `-price(t)` correct ONLY in the other encoding: on the asset's OWN output component w/ free sink (revenue-max trick).
- price-MAKING assets (large vs market) -> iterate | accept system-run dispatch as equilibrium approximation. STATE: which.

## Bias 3 - wholesale price != asset price
- merchant assets pay grid fees | levies | taxes ON TOP of wholesale — jurisdiction-specific. ! storage double-charging (fees on charge AND discharge) + exemptions w/ SUNSET dates can flip a BESS business case alone. STATE: which non-market cost components included; never quote model arbitrage as investable w/o them.

## Revenue accounting (post-solve, any run)
- RUN: `scripts/revenue_report.py solved_network.nc`.
- per-asset decomposition: energy revenue = sum_t p * lambda_bus(t) * w(t) | energy cost (links' bus0 side) | VOM | annualized capex | net margin.
- USES: n.buses_t.marginal_price -> run must produce meaningful prices (which runs do: pypsa-market-design).
- figures from this output -> pypsa-reporting chart-catalog #7 (diverging net-margin bar).

## Metrics
- LCOE/LCOH = (annualized capex + fixed O&M + sum variable costs) / annual output.
- LCOH: electricity at MARGINAL price vs PPA price shifts answer EUR/kg levels. STATE: power sourcing assumption. 1 kg H2 = 33.33 kWh LHV.
- capture price = market value = revenue-weighted mean price; capture RATE = capture price / time-weighted mean.
- VRE capture rates fall w/ penetration (cannibalization). ! never extrapolate today's capture rate -> high-RES scenario.
- IRR/NPV on model cashflows: STATE discount rate + lifetime consistent w/ annuity in capital_cost | else double-discount.

## Technology references - READ matching one
- references/storage-revenue.md -> BESS + TES arbitrage | stacking | degradation cost.
- references/multi-market-dispatch.md -> DA + intraday + imbalance sequencing | 15-min granularity | co-optimization traps.
- references/hydrogen-economics.md -> electrolyzer utilization frontier | LCOH.
- references/heat-economics.md -> heat pump vs boiler dispatch economics.
- references/vre-ppa.md -> capture prices | cannibalization | PPA structures.
