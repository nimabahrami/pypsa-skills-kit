# VRE capture prices and PPAs

- market value = capture price = sum(p_t * lambda_t * w_t) / sum(p_t * w_t).
- capture rate = capture price / time-weighted mean price.
- cannibalization: capture rates fall w/ technology penetration (solar fastest - correlated output). ! investment case must use SCENARIO capture rate from capacity-expansion run, not today's.
- curtailment: revenue accrues on DISPATCHED energy. REPORT: curtailment share separately (result, not loss to hide).
- PPA structures vs model prices: pay-as-produced (buyer takes shape risk) | baseload (seller buys shape from market; cost = baseload price minus capture price) | proxy/CfD (strike vs reference price).
- EVALUATE: re-price SAME dispatch under each contract; dispatch unchanged for must-run VRE.
- negative-price rules: subsidy void at negative prices -> ADD: p_max_pu = 0 response | custom constraint. Materially changes capture rates in high-RES scenarios.
