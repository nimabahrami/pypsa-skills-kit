# Multi-market dispatch (day-ahead / intraday / imbalance)

Scope: ENERGY markets, asset-side. Reserves -> pypsa-market-design/references/reserves-ancillary.md. Interface construction -> SKILL.md Bias 2. Cross-market MW double-count rule -> storage-revenue.md (applies per market, not just reserves).

## Market reality (EU, 2026)

- SDAC day-ahead = 15-min MTU since 2025-10-01 | intraday auctions IDA1-3 (since 2024-06) = primary BESS channel alongside continuous ID (ID1/ID3 indices).
- ! hourly snapshots zero out quarter-hour spread revenue by construction -> DA (post-2025-10) + ID + imbalance backtests need 15-min snapshots. 35040 x 0.25 weightings sum to 8760 — existing checks survive.
- ! backtest windows spanning 2025-10-01 mix hourly + 15-min DA regimes — never naively resample across the break.
- ID liquidity: cannot trade unlimited volume at index price -> cap traded volume | haircut.

## Recipe A — sequential (industry default; the ONLY valuation-grade recipe)

1. SOLVE: asset vs DA price curve (interface per SKILL.md Bias 2) -> DA position.
2. FIX: DA position -> re-optimize residual flexibility vs ID prices, rolling windows.
3. VALUE: deviations at imbalance price, post-process (below).

Exact encoding of step 2 (the silent-failure point):
- DA schedule = Load w/ `p_set = s_DA(t)`. ! s_DA SELL-positive = MINUS the pass-1 interface-Generator dispatch (which is buy-positive). DA sales exit bus as consumption | DA buys = negative p_set (valid on Load).
- + ONE bidirectional ID interface Generator: `p_min_pu=-1`, `marginal_cost = +ID(t)`. Cost linearity prices buy (p>0 pays) + sell (p<0 earns) w/ one value — no per-direction sign exists or is needed. Bid/ask spread -> two one-directional Generators -> re-opens simultaneous buy-sell (see anti-pattern).
- ! `Generator.p_set` IGNORED by optimize() (power-flow attribute) — constrains nothing, no error.
- REUSE: native `optimize_with_rolling_horizon` (+ its 3 traps) = pypsa-solve-and-debug/references/performance.md item 4. The DA/ID two-pass position ledger is new, lives here.

## Co-optimization warning (not a valuation recipe)

- ! ANTI-PATTERN: one independent interface per market = LP wash-trading. Buys p_nom in cheap market | sells p_nom in dear market, zero physical flow -> fake profit >> real arbitrage. NEVER build.
- ! deviation bounds do NOT fix it: s_DA=+p_nom, d_ID=-p_nom passes |s_DA|<=p_nom AND |s_DA+d_ID|<=p_nom at zero flow -> books |DA-ID| x p_nom reversal P&L. Any pure LP w/ 2 simultaneous prices at one node maxes the cross-market spread by construction; P&L not decomposable post-hoc.
- clean guard = per-snapshot net-buy XOR net-sell binary -> pypsa-custom-constraints/references/tech-constraints.md exclusivity, BINARIES branch ONLY (its LP-safe shared-capacity form merely halves wash volume; no LP-safe form exists for the cross-market case). ! flag MILP cost.
- LP co-optimized forms = upper bound only, never bankable. Recipe A = default.

## Imbalance settlement

- post-process VALUATION ONLY — never an ex-ante optimization target (forecastability ~0; optimizing into imbalance prices = worst perfect-foresight bias in this suite).
- STATE pricing regime: dual pricing penalizes both directions | single pricing (NL, DE reBAP) can reward system-helpful deviations -> passive balancing tolerated NL | penalized/prohibited elsewhere.
