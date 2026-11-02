# T14: the A3 brain on an EXPANDED universe (A0 §2 "universe expansion", its own trial), pre-registered 2026-10-19

**Context.** A3 (T05, 10 coins, about 7k dev rows) FAILED its skill gate (AUC 0.514, CI touching 0). The user chose to test whether more data, from more coins, changes this. This protocol is locked before the expanded store is built and before any model is fitted. It is trial **T14**, registered before the run; that makes 14 of the 20 trials used.

## Universe (A0 §2)
- **Candidates:** every coin present in all five of:
  - `data/universe_hf/5m`;
  - `data/universe_all/1h`;
  - `data/universe_all/1d`;
  - `data/futures_um/*_funding.csv`;
  - `data/futures_um/*_perp_1h.csv.gz`.

  That is 135 coins, checked on 2026-10-19. The 10 research coins are included.
- **Point-in-time liquidity filter, per row.** The median of the daily perp quote volume (the sum of the 1h `quote_volume` per UTC day) over the 30 full days before the signal day must be ≥ 50,000,000 USDT, with at least 20 of those days present. Only data before the signal day is used.
- **Survivorship (stated, not fixed).** The candidate list is the coins whose files exist today.

## Signals, trades and features (identical code paths to A1c / A2)
- **Signals:** S-LAD and S-DTB from the real-time pivot timeline (`r2_realtime_pivots`, amendment 2); S-BRK and S-TRD with the A1 definitions and the one-open rule. Entries 2020-02-01 … 2026-09-30.
- **Trades:** `r2_a1_edge_map.one_trade` (3 ATR trailing, 60-bar time stop); base cost 0.054% per side; real funding; perp availability as in A1.
- **Features:** the same 36 features (`data/derived/r2_a2/feature_list.json`) with the same A2 functions. The F6 daily metrics exist for 30 coins only; elsewhere they are NaN, which HistGradientBoosting handles natively.
- **Regression check (must pass before modelling).** For the 10 research coins, every expanded row that matches an A2 store row (signal, coin, side, entry_time) must have identical features and identical net_base, within 1e-9.

## Model, walk-forward, decision rule, portfolio and gates
**Exactly as A3** (`logs/r2_4h_a3/A3_PROTOCOL_PREREGISTERED.md`, 49bd3f5e…). This covers:
- the HGB parameters;
- monthly walk-forward with purge and embargo;
- the 80/20 isotonic calibration;
- thr = the median calibrated p on the calibration slice;
- m = clip((p − 0.5)/0.1, 0.5, 1.5);
- the portfolio (8,000 USDT, f = 0.5%·m, K = 6, one position per coin, ≤ 3×, minimum notional, MTM DD);
- the gates G-A, G-B, G-C (100 random-skip portfolios), G-D, G-E, G-G, G-H and DSR.

The only change: **N trials = 14** in the DSR (T01–T14).

**Deferred to A5:** PBO and G-I, as in A3.

**Verdict.**
- **"T14 provisional PASS"** if all gates hold.
- Otherwise **"T14 FAIL"**: no AI sleeve.

## Verifier (own code) `src/audits/verify_r2_t14.py`
1. Rebuilds 300 random expanded rows from data truncated at T, with its own code (the A2 verifier method). Features must be equal.
2. Recomputes the liquidity filter for 300 random rows from the raw perp 1h files.
3. Re-fits 4 random months; p must equal the study's.
4. Recomputes AUC, G-B, take rate and tail share.
5. Re-implements the MTM portfolio for the AI and the baseline.
6. Checks the claims and SHAs.
