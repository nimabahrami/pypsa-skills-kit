# Reserves and ancillary services

## Products (EU naming)

- FCR = seconds, symmetric | aFRR = minutes, up/down | mFRR = 15 min.
- screening sizing: FCR ~ +/-3000 MW continental Europe shared | aFRR/mFRR per zone ~ +/-1-3% of load | probabilistic.

## Modeling options, increasing fidelity

1. static derating: s_max_pu / p_max_pu headroom -> free, crude.
2. reserve margin constraint on capacity -> pypsa-custom-constraints generic pattern.
3. explicit reserve variables co-optimized w/ energy: reserve-up/down variables per unit | headroom: p + r_up <= p_nom * p_max_pu, p - r_down >= 0 | system requirement: sum(r) >= R_t. USE: linopy custom variables (m.add_variables) = only pattern in suite that ADDS variables. ! flag extra solve cost.
4. storage providing reserves: reserve ENERGY headroom too (SOC coupling), not just power. ! omitting -> overstates battery reserve value.

## Boundary with asset-economics

- modeling requirement = here.
- valuing asset reserve REVENUE (price series, stacking, derating of arbitrage) = pypsa-asset-economics/references/storage-revenue.md.
