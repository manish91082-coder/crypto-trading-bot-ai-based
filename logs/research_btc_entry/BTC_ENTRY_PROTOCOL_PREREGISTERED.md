# BTC: direction → entry → exit, without fixed timeframes. A fresh study, pre-registered 2026-10-25

This protocol is locked with SHA256 before any number is computed. It is a research simulation: no orders, and nothing live changes.

## Question (user, 2026-10-25)

- Forget timeframes. On BTC alone, find when a trade should be entered, in which direction (long or short), and when it should be exited after the minimum cost, on spot and on futures.
- Use every method (indicators, AI, maths), verified, with no rubber-stamping.
- Earlier project work is **not used** as a reference. Only the raw data and the fee table are inputs.

## Data (SHA256 → `input_manifest.csv`)

- `data/universe_hf/5m/BTCUSDT_5m_full.csv.gz` (SHA 657844920c9bd473…): 709,458 bars, 2020-01-01 … 2026-09-30, Binance spot, UTC. Its columns include `taker_buy_base`.
- `data/futures_um/BTCUSDT_funding.csv`: perp funding.
- `deploy/fees.json` v1, the single fee table. Per side: spot 0.085%; futures taker 0.046%; futures maker 0.028% (BNB fee + impact).
  - **Round trips:** spot 0.17%; futures taker 0.092%; futures maker 0.056% (information; a maker fill is not guaranteed).
- **Periods:**
  - **D** (develop) 2020-01-01 … 2023-12-31;
  - **V** (validate) 2024-01-01 … 2024-12-31;
  - **H** (holdout) 2025-01-01 … 2026-09-30, **opened once**, only for the final candidates.

## Exit: price-based, so no timeframe (triple barrier)

- **Entry** at the open of the bar after the decision bar.
- **Exit** at whichever comes first:
  - TP: price moves +a in the trade's direction;
  - SL: price moves −b against it;
  - time cap: 7 days (2,016 bars), exit at the close.
- **TP / SL fills** are at the barrier price. If a gap jumps through a barrier, the fill is at that bar's open. If one bar touches both, the SL counts (conservative).
- **Barrier sets (fixed):**
  - absolute: (a, b) ∈ {(0.5%, 0.5%), (1, 1), (2, 2), (4, 4), (1, 0.5), (2, 1), (4, 2), (0.5, 1), (1, 2)};
  - volatility-scaled: a = b = k·σ24 with k ∈ {1, 2, 3}, where σ24 = std of 5m log returns over the last 288 bars × √288.
  - 12 sets in all.
- **Net per trade** = direction-signed outcome − round-trip cost (− funding paid, for futures holds).
  - Futures: a long pays and a short receives positive funding for each funding event in (entry, exit].
  - Spot: longs only, no funding.
- **Break-even TP-first probability:** p* = (b + c) / (a + b), reported for every set.

## Direction / entry signals

Each is computed only from data up to the close of the decision bar.

| Family | Rule (fixed grid) |
|---|---|
| F0 Random | Every bar; direction by a fair coin (the control) |
| F1 Drift | Always long; always short |
| F2 Momentum | dir = sign(r_L) if \|r_L\| > k·sd_L. L ∈ {1h, 4h, 24h, 72h, 7d} = {12, 48, 288, 864, 2016} bars; k ∈ {0, 1, 2}; sd_L = std of r_L over the trailing 90 days |
| F3 Reversal | The opposite of F2, same grid |
| F4 Breakout | Long if close > the max high of the last N bars; short if close < the min low. N ∈ {12, 48, 288, 2016}. Follow and fade versions |
| F5 Z-score | z = (close − SMA_N) / sd_N, N ∈ {48, 288, 2016}. Long if z ≤ −k, short if z ≥ k (fade), k ∈ {2, 3}; plus the follow version |
| F6 RSI | Wilder RSI(14) on 5m closes, and on 1h and 4h closes (resampled, last closed bar). Fade: < 30 long, > 70 short. Strict: < 20 long, > 80 short. Plus the follow versions |
| F7 Squeeze | σ24 in the bottom 10% of its trailing 90 days; dir = sign(r_4h) (follow) |
| F8 Order flow | TBR_W = Σ taker_buy_base / Σ volume over W ∈ {1h, 4h, 24h}, z-scored vs the trailing 90 days. z ≥ k long, z ≤ −k short (follow) and the opposite (fade); k ∈ {1.5, 2.5} |
| F9 Volume shock | Volume over the last 1h ≥ 3 × the trailing 7-day mean 1h volume; dir = sign(r_1h), follow and fade |
| F10 Calendar | For each (weekday, UTC hour) bucket, the D-period mean 1h return. Long the bucket's hour if the D mean > 0, short if < 0. **This family uses a time exit (the end of that hour), not barriers.** Reported for all buckets, and for Sunday separately |
| F11 Funding | The latest funding rate vs its trailing 90-day distribution: > P90 short and < P10 long (fade), plus the follow version |
| F12 AI | Two HistGradientBoosting classifiers (long label: the TP-first outcome for a long; short label: the same for a short) on all F2–F11 continuous features + hour + weekday. Decisions every 6 bars (30 min). Monthly walk-forward: train on all decisions whose outcome was known before the month, starting 2021-01; predict the month. Barrier sets: (1%, 1%) and 2σ24. Trade if p ≥ p* + m, m ∈ {0, 0.02, 0.05}; if both sides qualify, the higher p − p* wins. Fixed params: max_depth 3, 300 iterations, lr 0.05, min_samples_leaf 200, random_state 0 |

## Trade simulation

- Walk forward in time. When flat and the signal fires at bar t, enter at t+1, and exit at the barrier.
- The next entry is allowed only after the exit (no overlap, one position at a time).
- A configuration = family param × barrier set × cost model:
  - futures taker, long + short (**primary**);
  - spot, long trades only;
  - futures maker (information).

## Selection (D, then V; H stays closed)

1. **On D, primary cost:**
   - keep configurations with n ≥ 200 trades and mean net > 0;
   - rank by t = mean / se, where se comes from weekly-block standard errors;
   - keep the top 3 per family.
2. **On V:** keep those with mean net > 0 and n ≥ 50.
3. **Finals:** at most 10 overall, by D t.
4. **N (multiple testing)** = every configuration evaluated on D.

## Holdout gates (finals only; all must hold to call a final "an edge")

- **G1:** H mean net > 0, and the weekly-block bootstrap 95% CI lower bound > 0 (2,000 resamples, seed 7).
- **G2:** n ≥ 100 trades in H.
- **G3:** it beats random entry. 200 seeds of the same number of trades, the same direction mix and the same barrier set, placed at random eligible bars of H with no overlap. The final's mean net must be ≥ the 95th percentile.
- **G4:** mean net > 0 in both 2025 and 2026-01 … 09.
- **G5:** DSR > 0.95 on per-trade net with N from the selection.

## Also reported (information)

- The F0 random and F1 drift results in every period.
- The break-even table.
- For every final: the TP-first rate vs p*, the median hold (time to exit), and the long/short split.
- The same finals under spot and maker costs.

## Verifier (`src/audits/verify_btc_entry.py`, own code)

- **V1:** manifest SHAs.
- **V2:** 500 random (bar, barrier set) outcomes recomputed by a plain bar loop from the raw csv.
- **V3:** 300 random (bar, family config) signal values recomputed by loops.
- **V4:** every final's H trade list replayed by a loop (entries, exits, net, the gate numbers G1 / G2 / G4).
- **V5:** the random control for one final recomputed with its seeds.

## Output

- `logs/research_btc_entry/`.
- The Hindi report `RESEARCH_BTC_DIRECTION_ENTRY_EXIT_<date>.md`.
