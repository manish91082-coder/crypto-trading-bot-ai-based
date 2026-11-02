# Ground-level audit of MASTER_INTEGRATED_RESEARCH_17_OCT_2026.md, plus a loss / trade / profit study: pre-registered (2026-10-18)

This protocol is locked with SHA256 before any result is computed. It is a historical research simulation: no orders, no AI training, nothing deployed, the cloud 1D system and the laptop production files are not touched. `archive/` is not used. Every change after the lock goes into `CODE_CHANGES_AFTER_LOCK.md`.

**Question (user, 2026-10-18):**
- Audit the master integration file: gaps, missing items, errors, add-ons, enhancements and improvements.
- Verify everything at ground level.
- Show how loss minimisation, trade maximisation and profit maximisation can be worked on.
- Use the same discipline as before.

## Part A: numeric audit of the master file (no new results)
- Every number in the master file that comes from a local source is re-read from that source by the independent verifier `src/audits/verify_master_audit.py`.
  - Sources: S1 summary CSV, ladder tables A1–A5 and B4, `internal_tf_stats.md`, `commission_demo.json`, and the SHAs listed in Part 0.
- **PASS:** the source value rounds to the master's value at the master's precision, or lies inside the master's stated range.
- **FAIL:** listed as an erratum.
- Numbers that come only from external literature are marked "external, not re-checked here".

## Part B: portfolio-level ground study (new results)
### Data (fixed)
- **Trades:** `logs/research_probe_scalein/trades.parquet` (S6; verifier PASS). The signals, stops, trailing (3 ATR), 60-bar time stop and variants are unchanged.
- **Real funding:** `data/futures_um/<coin>USDT_funding.csv` (Binance USDT-M funding history) for the same 10 coins.
- **Timeframes:**
  - 4h is primary;
  - 1h and 1D are secondary;
  - 5m and 15m are excluded, because the master already rejects them (N1).
- **Period:** entry from 2020-02-01 to 2026-09-30.
  - P1 = 2020-02..2023-12, P2 = 2024-01..2025-09, P3 = 2025-10..2026-09.
  - P3 was already seen in earlier work. It is reported but is not a clean holdout.

### B1. Real funding instead of the assumed 0.01% per 8h
- **Holding interval of a trade:**
  - entry_time is the open of the entry bar;
  - end = entry_time + (exit_idx + 1) × bar length;
  - for an add fill at bar i, its own interval starts at entry_time + i × bar length.
- **Funding events counted:** timestamps t with start < t < end (open interval).
- **Funding paid, in R:** Σ over fills and events of units × rate(t) × sign × fill_px / R_price.
  - sign = +1 for long (long pays a positive rate), −1 for short.
- **Real-funding net R:** = base net R + assumed funding R − real funding R.
  - The assumed part is exactly the term the S6 simulation charged: 0.0001 × fill_px × held_bars × bar_h / 8 / R_price per unit.
- **Perp availability:** a trade whose entry is before that coin's first funding timestamp is flagged "no perp".
  - Such trades are excluded from all Part B portfolio runs; the count is reported.
- **Reported:**
  - mean real funding R and mean assumed funding R per TF × side;
  - mean net R under both.

### B2. Portfolio simulation (fixed rules)
- **Capital:** start equity E = 8,000 USDT (the 2,000 reserve is never used).
- **Event order:**
  - signals are processed by entry_time; ties go by TF (1D, 4h, 1h), then by coin name;
  - before each entry, every position whose end ≤ entry_time is closed and its P&L realised.
- **Risk budget:** r = f × E, where E is the realised equity at that moment.
- **Notional:** N = r / (R_pct + 0.01 + 0.0009), where R_pct = R_price / entry_px. This is the master's sizing rule: stop + 1% slippage + round-trip fee.
- **Skip rules** (counted by reason):
  - (a) the coin already has an open position on the same TF;
  - (b) another TF on the same coin holds the opposite direction (one-way mode; the master's §6.3);
  - (c) the number of open positions is already at K;
  - (d) total open notional + N > 3 × E;
  - (e) N is below the coin's minimum notional: BTC 50, ETH 20, LINK 20, others 5 USDT; for BTC, N / entry_px must also be ≥ 0.001.
- **P&L in USDT** = N × netR × R_pct, using the real-funding base net R from B1.
- **Metrics:**
  - final equity; CAGR over 6.66 years;
  - max drawdown of realised equity; Calmar = CAGR / maxDD;
  - trades taken and per year; win rate;
  - worst calendar month; longest losing streak;
  - max total leverage (open notional / E);
  - returns in P1, P2 and P3;
  - skip counts.

### Grids (fixed in advance; nothing else is run)
**G1, risk and concentration (4h, both sides, V0):**
- f ∈ {0.25%, 0.5%, 1.0%} × K ∈ {3, 6, 10, unlimited}: 12 runs.

**G2, trade maximisation (V0, f = 0.5%, K = 10):** streams
- 4h;
- 1h;
- 1D;
- 4h+1h;
- 4h+1D;
- 4h+1h+1D.

Also reported: the correlation of monthly summed R between the 4h, 1h and 1D streams.

**G3, loss-minimisation rules.** Baseline: 4h, V0, f = 0.5%, K = 6. Each rule is applied alone:
- **L1 drawdown de-risking:** when realised equity is ≥ 10% below its peak, f is halved until a new peak.
- **L2 loss-streak pause:** after 4 consecutive losing trades (by exit time), no new entries for 24 h.
  - **Control:** 50 random-pause runs (seed 20261018 + i) with the same number of 24 h pauses, started at uniformly drawn trade entry times.
- **L3 same-direction cap:** at most 3 open positions in the same direction.
- **L4 test entry:** V2 (25/25/50) instead of V0, with real funding recomputed from its fills.
- **L5 longs only.**

**Robustness for the G3 baseline (not rules):**
- R1: all fees and spread × 1.5;
- R2: futures taker 0.05% (FAQ), i.e. 0.054% per side instead of 0.045%;
- R3: no BNB, i.e. 0.049% per side.

For R1–R3, the per-side cost is changed in the trade's fee term only; real funding is unchanged.

**Pre-registered verdict for each G3 rule ("helps / does not help"):**
- **Helps** = BOTH:
  - its maxDD is lower AND its Calmar is higher than the baseline over the full period;
  - the same holds in at least 2 of P1, P2, P3. A period's maxDD and Calmar are computed on the equity path inside that period.
- For L2, it must in addition beat the 90th percentile of the random-pause Calmar.
- Otherwise: "does not help", or "trade-off" when it lowers maxDD but also lowers Calmar.

### B3. Cost levers (trade level; 4h and 1D; V0; real funding)
Mean net R under each fee scenario, with the fee term recomputed from entry_px and exit_px:

| Scenario | Entry, per side | Exit, per side |
|---|---|---|
| base | 0.045% | 0.045% |
| maker entry | 0.018% (0.02% maker × 0.9 BNB, no spread) | 0.045% (taker) |
| FAQ taker | 0.054% | 0.054% |
| no BNB | 0.049% | 0.049% |
| spot long (longs only, no funding) | 0.085% | 0.085% |

**Check:** before this table is computed, the recomputed base fee term must reproduce S6's `V0_base_cost` minus the assumed funding to 1e-9.

### B4. Profit-maximisation descriptives (4h and 1D; V0; real funding)
- **Tail share:** the share of the sum of positive net R that comes from the top 5%, 10% and 20% of trades.
- **Exit reason:**
  - time stop = exit_idx == 59, the last bar of the 60-bar window;
  - otherwise a stop.
  - Reported: counts, mean R, and the share of time-stopped trades whose gross R > 2. This is descriptive only, an input for A4; no hold-length change is tested here.
- **Win/loss:** the mean win R / mean loss R ratio, and the win rate.

### B5. Feasibility at 10,000 USDT (from G1, f = 0.5%, K = 6)
- the median and 95th percentile of N;
- the share of signals skipped for minimum notional;
- max leverage.

## Verifier (separate code, its own implementation)
`src/audits/verify_master_audit.py`:
1. Part A checks, with PASS/FAIL per claim.
2. Recomputes real funding for 300 random trades, with its own loop over the funding files, and must match to 1e-9.
3. Re-implements the portfolio loop independently for G1 (f = 0.5%, K = 6) and for G3-L1. Final equity and maxDD must match to 1e-6.
4. Checks the claims JSON against the CSVs, and the protocol, trades and funding-file SHAs.

## Honest limits (fixed in advance)
- Rule signals only, no AI. This measures the portfolio and risk mechanics around the ladder signals, not the final AI system.
- Equity is realised-only; open-trade mark-to-market drawdown is not modelled, so the true intraday DD is larger.
- Funding is computed with the fill price as notional, not the mark price at each funding time.
- **Survivorship:** the 10 coins are large survivors chosen today.
- Every Part B choice made from these results is a design prior. It must be re-tested inside the A0 trial budget (20) before it can be called proven.
