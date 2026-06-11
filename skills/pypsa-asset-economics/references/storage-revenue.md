# Storage revenue (BESS, TES)

## Revenue streams - modeling each
- energy arbitrage -> falls out of dispatch vs prices. ! mind all THREE biases in SKILL.md.
- reserves (FCR/aFRR) -> co-optimize (pypsa-market-design/references/reserves-ancillary.md) | post-process. Reserving > ~30-50% of power into FCR derates arbitrage. ! naive addition of both revenues double-counts same MW.
- capacity payments = exogenous EUR/MW/a -> add outside optimization.

## Degradation economics
- cycling wear as marginal_cost on DISCHARGE link: wear EUR/MWh = cell replacement cost / (cycle life * usable energy) — no /2 when applied discharge-only. LFP @ 100-150 EUR/kWh, 5000-8000 cycles -> 12-30 EUR/MWh full attribution. Common practice discounts for calendar-dominated aging + falling future cell prices -> 5-15 EUR/MWh typical | 1-5 only at bottom-of-market cell costs. STATE basis.
- ! no wear cost -> optimizer micro-cycles on noise -> overstates cycles + revenue.
- calendar-life-dominated chemistries -> lower wear cost deliberately.
- cycle-count caps (e.g. warranty 365 cycles/a) -> e_sum-style custom constraint -> pypsa-custom-constraints.
- long-term capacity fade (multi-year/merchant models): step `e_max_pu` DOWN per period (`e_nom` static — cannot derate) | augmentation = new Store tranches w/ `build_year` -> mechanics: pypsa-network-modeling/references/multi-period.md. ! tranches share charger/discharger Links — power capacity must not silently multiply.
- wear marginal cost internalizes cycle fade ECONOMICALLY | e_max_pu trajectory = TOTAL realized fade PHYSICALLY. Both present -> derating schedule must be consistent w/ the cycling the wear cost already priced.

## Sanity anchors
- daily-cycling BESS captures ~ mean(top-N minus bottom-N hour spread) * round-trip efficiency.
- ! model revenue >> price-series spread statistics -> foresight | eff > 1 | double-counted capacity.
- revenue per MW falls as BESS fleet grows (intra-day spread compression). Single-asset price-taker runs ignore this. STATE: when fleet sizes large.
