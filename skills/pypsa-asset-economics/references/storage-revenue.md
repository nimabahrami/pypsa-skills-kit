# Storage revenue (BESS, TES)

## Revenue streams - modeling each
- energy arbitrage -> falls out of dispatch vs prices. ! mind all THREE biases in SKILL.md.
- reserves (FCR/aFRR) -> co-optimize (pypsa-market-design/references/reserves-ancillary.md) | post-process. Reserving > ~30-50% of power into FCR derates arbitrage. ! naive addition of both revenues double-counts same MW.
- capacity payments = exogenous EUR/MW/a -> add outside optimization.

## Degradation economics
- cycling wear as marginal_cost on DISCHARGE link: wear EUR/MWh = cell replacement cost / (cycle life * usable energy) — no /2 when applied discharge-only. LFP @ 100-150 EUR/kWh, 5000-8000 cycles -> 12-30 EUR/MWh full attribution. Common practice discounts for calendar-dominated aging + falling future cell prices -> 5-15 EUR/MWh typical | 1-5 only at bottom-of-market cell costs. STATE basis.
- ! no wear cost -> optimizer micro-cycles on noise -> overstates cycles + revenue.
- calendar-life-dominated chemistries -> lower wear cost deliberately.
- BESS: `marginal_cost_storage` (EUR/MWh of energy HELD per snapshot) = the CALENDAR-fade lever, distinct from discharge-Link cycle wear. positive -> optimizer holds LOWER average idle SOC -> approximates calendar aging by penalizing held energy. ! flat per-MWh-held, NOT itself SOC-dependent (true SOC-nonlinear aging -> segmented bands below). lever lives on the energy reservoir (Store OR StorageUnit); attr listing -> pypsa-network-modeling/references/storage-representation.md.
- BESS: revenue streams as separate Links on a shared Store -> can carry DIFFERENT wear adders in `marginal_cost` (peak-shaving cycling wears differently from a reserve product).
- cycle-count caps (e.g. warranty 365 cycles/a) -> e_sum-style custom constraint -> pypsa-custom-constraints.
- BESS: convex DOD-dependent wear (ESCALATION — use ONLY if DOD-dependence materially changes the answer; default = flat wear above). linearize by splitting the battery into k parallel Stores on ONE bus across SOC bands, each band a HIGHER discharge wear cost. ! bands must PARTITION energy (sum of band `e_nom` = total usable, NOT duplicate) + SHARE one converter -> else silently multiplies energy/power capacity. power cap (linopy) -> pypsa-custom-constraints/references/tech-constraints.md. requires Store+Links (StorageUnit monolithic, no parallel bands).
- BESS: long-term capacity fade, TWO tiers. CHEAP (exogenous): step `e_max_pu` DOWN per period from the warranty curve, no feedback (`e_nom` static — cannot derate) | augmentation = new Store tranches w/ `build_year` -> mechanics: pypsa-network-modeling/references/multi-period.md. PROPER (iterative): optimize year n -> compute realized fade from the dispatch profile ex-post -> derate `e_nom`/`e_max_pu` -> optimize n+1 (outer Python loop around `n.optimize()`). tradeoff: exogenous ignores how dispatch intensity drives fade; iterative closes that loop at the cost of the loop. ! tranches share charger/discharger Links — power capacity must not silently multiply.
- wear marginal cost internalizes cycle fade ECONOMICALLY | e_max_pu trajectory = TOTAL realized fade PHYSICALLY. Both present -> derating schedule must be consistent w/ the cycling the wear cost already priced.
- perfect-foresight runs burn storage near horizon end (remaining life worthless at t=T) -> inflated late-horizon cycling + revenue. fix: price cumulative throughput (the wear `marginal_cost` above) = value of life carried past the horizon | terminal SOC constraint = cruder alternative. general to any cycling store (PHS/TES too) -> SKILL.md Bias 1 for the foresight concept.

## Sanity anchors
- daily-cycling BESS captures ~ mean(top-N minus bottom-N hour spread) * round-trip efficiency.
- ! model revenue >> price-series spread statistics -> foresight | eff > 1 | double-counted capacity.
- revenue per MW falls as BESS fleet grows (intra-day spread compression). Single-asset price-taker runs ignore this. STATE: when fleet sizes large.
