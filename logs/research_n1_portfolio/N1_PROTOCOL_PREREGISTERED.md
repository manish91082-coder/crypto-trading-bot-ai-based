# N1: rule-only multi-sleeve portfolio (trial T15), pre-registered 2026-10-20, before any N1 number is computed

**Parent.** A0 (`4d49d411…`) discipline: trial registry, independent verifier, gates. Research only: no orders, no money, the 1D cloud system and laptop production are not touched, `archive/` is not used.

**Sources.** The sleeves come from:
- TFX (`04db1fea…`) and TFX-S (`120c92b4…`): the trend-long / RSI-long / trend-short cells, ρ and N_eff;
- DISC (`a9f46d40…`): D4 1D XS momentum, D6 crisis hedge.

The Gemini items (heat cap, correlation dampener) come from `REVIEW_GEMINI_NOTEBOOK_AND_RESEARCH_20_OCT_2026.md` §6.

**Honest status of the test.**
- The sleeves were chosen after looking at the 2020-02 … 2026-09 data (TFX, TFX-S, DISC). N1 is therefore a **portfolio-level confirmation in-sample**, not an out-of-sample test.
- The overfitting gates (DSR with all earlier trials plus the TFX N_eff, PBO, random-entry control) account for this.
- The only data not used to choose anything are:
  - 2018-04 … 2019-12 (gate G7, spot, run once);
  - the forward data from 2026-10-17.

## 1. Question
Does a fixed, rule-only portfolio of four low-correlated sleeves earn money at the portfolio level? It must hold:
- with stops, overlap, real funding and taker costs;
- beyond a random-entry control;
- in both P1 and P2;
- after deflation for every trial so far.

## 2. Data (fixed)
- **Bars.** `data/universe_hf/5m/<coin>_5m_full.csv.gz`, resampled to 1h (left-closed, UTC) and, from those 1h bars, to 4h / 8h / 12h / 1D. OHLC aggregation is associative, so these TF bars are identical to TFX's 5m → TF bars. The code asserts this by reproducing TFX's gross returns.
- **Signals.**
  - TFX trade files `data/derived/tf_edge_map/{U1,U2}/<tf>/<coin>.parquet` (SHA-listed in the claims), i.e. the TFX state-machine trades: entry at the open of the bar after the signal bar, exit at the open of the bar after the exit-signal bar.
  - U2 is used without LUNAUSDT and STRAXUSDT (U2X, as in TFX-S / DISC).
- **Funding.** The real history `data/futures_um/<coin>_funding.csv`. A trade pays or receives `side × rate × notional_at_entry` at every funding time f with entry_time < f ≤ exit_time (the TFX convention). A trade whose entry is before the coin's first funding record is not tradable (perp missing) and is dropped.
- **Liquidity (U2X, sleeves C and D).** TFX `liq_days`: the 30-day median perp quote volume ≥ 50 M USDT, shifted one day.
- **Windows.**
  - dev = entries 2020-02-01 … 2025-09-30, split into P1 (to 2023-12-31) and P2 (2024-01-01 … 2025-09-30);
  - P3 = 2025-10-01 … 2026-09-30, reported only;
  - G7 = 2018-04-17 … 2019-12-31 (§7).

## 3. Sleeves (signals exactly as TFX / DISC; nothing re-tuned)

| Sleeve | Universe | Signals (sub-signals per coin) | Side | Gross budget g |
|---|---|---|---|---|
| A trend-long | U1 (core10) | TSMOM20, EMAX20/50, MACD12/26/9, DONCH20/10 × {4h, 8h, 12h, 1D} = 16 | long | 0.8 |
| B oversold-long | U1 | RSI14 < 30 entry / > 50 exit × {8h, 12h, 1D} = 3 | long | 0.4 |
| C trend-short (crash hedge) | U2X, liquid at entry (TFX U2 files) | the same 16 trend sub-signals | short | 0.4 |
| D XS momentum | U2X liquid | DISC D4 on 1D: 20-day return, top / bottom quintile, long top and short bottom, equal weight, rebalance every 5 days, decision at day close, open-to-open | long + short | 0.4 (0.2 long + 0.2 short) |

**Notional of one sub-position, as a fraction of the sizing equity E_m (§4):**
- A: 0.8 / (16 × 10) = 0.005;
- B: 0.4 / (3 × 10) = 0.01333;
- C: 0.4 / (16 × max(10, n_d)), where n_d = the number of U2X coins liquid on the entry day;
- D: 0.2 / (number of coins in the leg), per coin.

So gross ≤ 2.0 × E by construction, except C when n_d falls within a month; the maximum realised gross is reported.

## 4. Simulator (fixed)
- **Capital.** E0 = 10,000 USDT.
- **Sizing base.** E_m = the mark-to-market equity at the start of the calendar month of the entry. Positions are fixed in units after entry, i.e. no intra-trade rebalancing.
- **Costs.**
  - Taker 0.054% per side (0.045% fee with BNB + 0.009% spread/slippage), on the entry notional at entry and on the exit notional at exit; real funding as in §2.
  - D: 0.054% × turnover at every rebalance, plus each leg's funding.
- **Stops (A, B, C).**
  - Fixed initial stop = entry ∓ 3 × ATR14(TF) of the signal bar. ATR14 is Wilder's: TR with the previous close, EWM α = 1/14, adjust = False.
  - The stop is checked on every 1h bar from the entry hour up to the hour before the signal exit.
  - A long is stopped if the 1h low ≤ stop; the fill is min(1h open, stop). Shorts mirror this.
  - After a stop the sub-signal is flat until its next TFX entry.
  - D has no stop: it is market-neutral by construction.
- **Mark-to-market.** Every 1h close (D at the daily opens, 00:00 UTC). MTM-DD = max(1 − equity / running max) over the hourly curve. Calmar = CAGR / MTM-DD.
- **Separate runs.** Each window (dev, P1, P2, P3, G7) is a separate run from E0 with the trades entering in that window. Positions still open at the window end are marked at the last close.

## 5. Configurations (all count as trials in DSR and PBO)

| Id | Change against K0 |
|---|---|
| K0 | primary: A + B + C + D, 3-ATR stops, equal notional |
| K1 | no stops (A, B, C exit only on the signal) |
| K2 | heat cap: Σ over open A/B/C positions of w × \|entry − stop\| / entry ≤ 6% (Elder's "6% rule", adapted to open stop-risk only). A new entry is scaled down to fit and skipped if nothing fits. Trades are processed in time order; a position leaves the heat when it exits. D is excluded (no stop). |
| K3 | correlation dampener: A/B/C entry weight × m_d, with m_d = min(1, sqrt((1 + 9ρ_ref) / (1 + 9ρ̄_d))). ρ̄_d = the mean pairwise correlation of core10 daily close-to-close returns over the 60 days ending at the last complete day before the entry. ρ_ref = the expanding median of ρ̄ (needs ≥ 180 days, else m = 1). |
| K4 | without D (the original 3-sleeve plan) |
| K5 | without C |
| K6 | inverse-vol sizing: A/B/C entry weight × clip(σ_med / σ_c, 0.5, 2). σ_c = the coin's std of daily close-to-close returns over the 60 days before the entry day. σ_med = the median σ over that sleeve's eligible coins on that day (core10 for A/B, liquid U2X for C). |

**Pre-registered selection (dev data, like A4):**
- An overlay (K1 no-stop, K2, K3, K6) is adopted only if its dev Calmar **and** its P1 Calmar **and** its P2 Calmar all exceed K0's.
- A sleeve is removed (K4 → without D, K5 → without C) only by the same rule.
- All adopted changes are applied together = the FINAL config. If it differs from K0–K6, it is one more configuration in the trial count.

## 6. Gates on the FINAL config ("N1 PASS" needs all of G1–G7)
- **G1 random entry.** Dev Calmar > the 95th percentile of 100 random-entry portfolios (seed 20261024 + i).
  - Every A/B/C sub-trade is moved to a uniformly drawn entry bar of the same coin, TF and calendar year (for C: only liquid days), keeping the side, the hold in TF bars, the stop rule (ATR at the new signal bar) and the weight rule.
  - D: at every rebalance, long and short sets of the same sizes are drawn at random from the eligible coins.
- **G2 cost.** Dev mean monthly return > 0 at 1.5× and at 2× (fee + spread), and with every stop fill 0.3% worse.
- **G3 stability.** Calmar > 0 in P1 and in P2.
- **G4 bootstrap.** The 95% CI (calendar-month block bootstrap, 2,000 draws, seed 20261024) of the dev mean monthly return lies above 0.
- **G5 DSR ≥ 0.95.**
  - Monthly dev returns.
  - N = 14 earlier trials + 5 (TFX/DISC N_eff) + the number of N1 configurations (7, or 8 with a distinct FINAL).
  - The SR variance is that of the configurations' monthly Sharpe ratios.
  - Formula as in A4.
- **G6 PBO < 0.30.** CSCV, 16 contiguous blocks of dev monthly returns over K0–K6.
- **G7 out-of-time 2018–19, run once.**
  - Data: `data/universe_pre2020/1h` spot bars, 2018-04-17 … 2019-12-31, signals with the TFX code.
  - A and B on the core10 coins that exist. C and D on coins whose 30-day median spot quote volume ≥ 50 M (shifted one day).
  - Costs: spot 0.085% per side for longs. Shorts at 0.054% per side, with funding ignored (no perp history for most coins; stated as a limitation).
  - D is inactive on days with fewer than 10 eligible coins.
  - Gate: Calmar > 0.

**Report only:**
- P3;
- every calendar year;
- per-sleeve contributions;
- maximum gross and the maximum net exposure per coin;
- BTC buy-and-hold over the same windows;
- the monthly correlation with the 1D system (`logs/strategy_1d_step27_combine/sleeves_MAIN_f50.csv`, column D1, 2021-01 onward);
- a sizing table at 0.5× / 1× / 1.5× all budgets (information; the risk level is the user's choice).

If N1 FAILS, the report says so and N2 is built only as a report on top of K0 (no PASS claim).

## 7. Outputs
- `logs/research_n1_portfolio/`: `N1_configs.csv`, `N1_years.csv`, `N1_sleeves.csv`, `N1_random_entry.csv`, `N1_gates.json`, `N1_g7_pre2020.csv`, `claims_n1.json`, `run_log.txt`;
- trade ledgers `data/derived/n1/trades_<config>.parquet` and hourly equity `data/derived/n1/equity_<config>.parquet`.

## 8. Verifier `src/audits/verify_n1.py` (own code; does not import the N1 module)
1. 300 random A/B/C sub-trades are recomputed from the raw 5m files with its own resample, ATR, stop scan, fees and funding, to 1e-9 R. Without stops, the gross equals the TFX file gross.
2. The FINAL dev equity curve is rebuilt from the trade ledger with its own event-by-event accounting. Final equity and MTM-DD are compared to 1e-6 relative.
3. 50 random D rebalances are recomputed from 1D bars.
4. PBO, DSR, the bootstrap CI and the selection rule are recomputed from the saved monthly matrix.
5. SHAs: the protocol lock, the TFX trade files, the claims, and the registry line T15.

Any change after the lock goes into `CODE_CHANGES_AFTER_LOCK.md`.
