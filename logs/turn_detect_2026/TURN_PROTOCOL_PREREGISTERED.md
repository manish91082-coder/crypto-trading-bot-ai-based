# TURN-2026: can direction (a turn) be caught BEFORE the usual confirmation? BTC, 2026-01 … 2026-09. Locked 2026-10-27

**Request (user, 2026-10-27):** "Indicators and candles confirm the direction late; the market has already turned. Find what catches the direction earlier. Use only the 9 months Jan–Sep (not 5–6 years). Single and multiple indicators, timeframes 1m … 1d, a hidden timeframe between the visible ones (seconds vs minutes, the slow up-down-up 'creeping' turn), spot, futures, order book, long/short. Ground-verified, no shortcut."
- The user said "2022"; together with "January to now, September" and "9-month data set" this is read as **2026-01-01 … 2026-09-30**. The report states this reading.

## 0. Honest status of the data (stated before any number)
- **Already used on 2026 Jan–Sep (1m/5m klines):** the oracle study Part C (9 direction methods, 8 entry triggers, 100 configs; all ≈ coin flip), the green-candle study, and the fee-hurdle map. **None of the questions below was asked there.** But the months are not pristine for the researcher.
- **Spot 1s data:** Jan–May were used by the micro-momentum study. **Jun–Sep 1s are unopened (sealed).**
- **Split:**
  - **DISC = 2026-01-01 … 2026-05-31.** All exploration, feature screens and model fits.
  - **HOLD = 2026-06-01 … 2026-09-30.** Opened **once**, by the `hold` stage, only for what §8 sends there. The `hold` stage refuses to run if `hold_candidates.json` does not exist.
- **1M timeframe:** 9 bars in total (5 in DISC). No test is possible; this is stated, not run.
- **1d:** 151 DISC bars; it is run, but its power is low, and this is stated next to every 1d number.

## 1. Data (all checksum-verified, SHAs into `input_manifest.csv`)
- **Price (the traded venue):** Binance USDⓈ-M BTCUSDT perpetual **1m** klines, `data/external/binance_1s/futures_1m/BTCUSDT-1m-2026-0{1..9}.zip`. Columns used: open, high, low, close, volume, taker_buy_volume.
- **Spot 1s:** `data/external/binance_1s/spot_1s/BTCUSDT-1s-2026-0{1..9}.zip` (µs timestamps). Used for the sub-minute features and the spot-perp lead.
- **Derivatives / book (5m, `data/external/binance_public/clean/`):**
  - `metrics5m.parquet`: open interest (OI), top-trader long/short ratio, taker long/short volume ratio;
  - `premium5m.parquet`: perp premium index close;
  - `funding.parquet`: the 8h funding rate;
  - `depth5m.parquet`: book depth imbalance `imb1` (±1%) and `imb5` (±5%).
- **Cross-asset:** `data/universe_hf/5m/ETHUSDT_5m_full.csv.gz` (spot 5m).
- **Timing rule for 5m tables:** a 5m row stamped T is used only from T + 5 min (its close). Funding is used from its stamp.
- **Costs:** from `deploy/fees.json`, never typed:
  - taker round trip = 2 × `rules.paper_futures_taker_per_side` (0.092%);
  - maker round trip = 2 × (`futures_usdm.bnb_maker` + `impact_per_side`) (0.056%).

## 2. The null (the mathematical yardstick used everywhere)
- **Sign-randomized path:** r*_t = s_t × |r_t|, where r_t is the real 1m log return and the s_t are i.i.d. ±1 (seeded). The path starts at the real first price.
  - This keeps the exact volatility path (every quiet and every wild minute stays where it was), but removes all directional information at every scale.
  - **Under this null, no method can know the direction early.** A method has real early information only if it does **better on the real path than on the null paths**.
- **Volume, taker, OI, premium, funding and depth** stay real in the null. Their link to the randomized price is broken, so the null measures whether they predict the **real** direction.
- **Higher timeframe bars** are rebuilt from the null 1m path (OHLC from 1m OHLC: the 1m bar's high/low offsets relative to its close are kept with the bar, sign-flipped with the bar's return; documented in CODE_NOTES).

## 3. Part T0: what "late confirmation" costs (descriptive)
- **ZigZag on 1m closes, timeframe-free,** thresholds θ ∈ {0.5, 1, 2, 4, 8}%. A pivot is confirmed when the close moves θ from the running extreme. For each turn the code records:
  - the extreme time t* and price;
  - the confirmation time t_c and its lag in minutes;
  - the leg size (extreme to the next extreme).
- **Report, per θ:**
  - median lag;
  - the share of the leg already gone at confirmation;
  - the "follow confirmed turns" system: always in the direction of the last confirmed turn, entry at the next 1m open after t_c, exit at the next open after the opposite confirmation. Gross and net per trade.

## 4. Part T1: turn-completion test (the core math)
- **Event (causal):**
  - In a down leg (last confirmed pivot = high) the running low L is tracked. The event UP(f) fires at the first 1m close ≥ L × (1 + f θ) after L was set.
  - If a new lower low is made later, L resets and the event can fire again for the new L.
  - DOWN(f) is the mirror case.
- **Outcome:** *complete* if a later close reaches L × (1 + θ) before a close below L; *fail* otherwise. An event still open at the end of the period is dropped and counted.
- **Grid:** θ ∈ {0.5, 1, 2, 4, 8}%, f ∈ {0.25, 0.5, 0.75}, both directions pooled.
- **Random-walk value:** P(complete) ≈ f (gambler's ruin). The exact discrete null value is the mean over **100 sign-randomized paths** (seeds 1…100).
- **Statistic:**
  - Δ = P_real − P_null;
  - 95% CI by day-block bootstrap (2,000 resamples, seed 7);
  - null p-value = share of null paths with P ≥ P_real.
- **Economic version (per θ, f; taker and maker):**
  - enter at the next 1m open after the event, in the turn direction;
  - exit at the next 1m open after the outcome close.
  - Net per trade with day-block CI.
  - **Break-even:** p* with this geometry is printed beside it.

## 5. Part T2: does anything at the event moment predict completion?
**Features at the event close (all causal; "oriented" = multiplied by +1 for UP and −1 for DOWN, so that a high value means "supports the turn"):**

| id | feature |
|---|---|
| F01 | bounce minutes (L → event) |
| F02 | prior leg (last pivot → L) / θ |
| F03 | volume per minute during the bounce / mean volume per minute in the 60 min before L |
| F04 | oriented taker-buy share during the bounce (Σ taker_buy / Σ volume − 0.5) |
| F05 | oriented taker-buy share in the 15 min before L (exhaustion) |
| F06 | oriented OI change, L → event (last closed 5m rows) |
| F07 | oriented premium change, L → event |
| F08 | oriented funding (contrarian: −dir × last funding rate) |
| F09 | oriented depth imbalance imb5 (last closed 5m row) |
| F10 | oriented sign of EMA20 slope on closed 1h bars |
| F11 | the same on 4h |
| F12 | the same on 1d |
| F13 | creeping/staircase on 1m: share of bounce minutes whose low is above the previous minute's low (oriented) |
| F14 | retests: number of closes within 0.1 θ of L in the 120 min before L (double bottom / top) |
| F15 | ETH lead: oriented ETH 5m return since L's 5m bar minus BTC's |
| F17 | creeping on 1s: share of 10-s windows in the last 10 min of the bounce whose low is above the previous window's low (oriented) |
| F18 | bounce speed (f θ / F01) |
| F19 | perp − spot oriented return during the bounce (spot 1m from 1s closes) |
| F20 | realized 1m volatility over the prior 24 h (not oriented) |
| F21 | oriented change of the top-trader long/short ratio, L → event (contrarian sign: −dir) |

- **Coverage:** F17 and F19 need spot 1s data. In DISC they come from Jan–May; in HOLD they open with the sealed Jun–Sep 1s files.

**Screen on DISC:**
- AUC of each feature for "complete" within each (θ, f), with a day-block bootstrap CI.
- Bonferroni over 20 features × 5 θ × 3 f = 300 tests: a feature is "real" if its 99.983% CI excludes 0.5.

**Combined model (no feature selection):**
- Per (θ, f): logistic regression on all features, standardized on DISC (sklearn, L2, C = 1.0, max_iter 1000; missing values → DISC median).
- **Trade rule fixed now:** take the event if p̂ > p* (the taker break-even for that geometry). There is no threshold tuning.
- **DISC estimate:** leave-one-month-out (fit on 4 months, test on the 5th, for each month).
- **HOLD:** the model is fit on all of DISC and applied once.

## 6. Part T3: detector library on every timeframe (single, multiple, multi-timeframe, flow)
- **Timeframes:** 1m, 5m, 15m, 30m, 1h, 4h, 8h, 12h, 1d. Bars are built from the 1m perp, UTC-anchored.
- **Each detector gives a state d_t ∈ {−1, 0, +1} at the bar close.**
- **Trading:** always in d (flat when 0). A trade opens or flips at the next bar's open.
- **Metrics:**
  - gross and net (taker) per trade;
  - number of trades;
  - accuracy P(sign(next-bar return) = d | d ≠ 0).

**Detectors:**

| code | detector | params |
|---|---|---|
| P1 | EMA slope sign | n 5, 20, 50 |
| P2 | EMA cross | 5/20, 20/50 |
| P3 | Hull MA slope | 9, 21 |
| P4 | ZLEMA slope | 10, 30 |
| P5 | Kalman local-linear-trend slope sign | q/r 1e-2, 1e-3 |
| P6 | linear-regression slope t-stat, sign if \|t\| > 2 else 0 | 20, 50 |
| P7 | two-sided CUSUM on vol-standardized returns (k 0.5): the last alarm side | h 4, 8 |
| P8 | Donchian breakout state | 20, 55 |
| P9 | MACD histogram sign | 12/26/9 |
| P10 | RSI14 > 50 | — |
| P11 | Bollinger fade (%b > 1 → −1, < 0 → +1, hold) | 20, 2 |
| P12 | Heikin-Ashi colour | — |
| P13 | curvature: sign of Δ² EMA10 (the turn of velocity) | — |
| P14 | swing structure: 3-bar fractals; HH+HL → +1, LH+LL → −1, hold | — |
| P15 | Ehlers 2-pole SuperSmoother slope | 10, 20 |
| M1 | multi-timeframe: P1(5) on TF, only when it agrees with P1(20) on TF2 (TF2 = two steps up the TF list, capped at 1d) | — |
| M2 | majority vote of P1(20), P3(21), P6(20), P9, P10, P14, P15(20) | — |
| Q1 | taker imbalance (Σ taker_buy / Σ volume − 0.5) EMA5 sign | TF ≥ 5m |
| Q2 | OI × price: price up and OI up → +1; price down and OI up → −1; OI down → 0 (one TF bar) | TF ≥ 5m |
| Q3 | premium change sign (one TF bar) | TF ≥ 5m |
| Q4 | depth imbalance imb5 sign | TF ≥ 5m |
| Q5 | funding contrarian (−sign of the last funding) | TF ≥ 1h |
| Q6 | ETH lead (sign of ETH's last closed 5m-aggregated TF-bar return) | TF ≥ 5m |
| Q7 | top-trader long/short contrarian (−sign of the ratio change over one TF bar) | TF ≥ 5m |

**Null for every config:**
- 20 sign-randomized paths (seeds 1…20); bars and price detectors are rebuilt on each path.
- Flow detectors use real flow against the null price.
- z = (real gross per trade − null mean) / null sd.

**DISC shortlist:**
- z > 3.5 (about Bonferroni for ~700 configs);
- net per trade > 0 (taker);
- n ≥ 30 trades.

## 7. Part T4: hidden timeframe scan
- **Grid:**
  - seconds q ∈ {1, 2, 3, 5, 7, 10, 15, 20, 30, 45} s (spot 1s);
  - minutes q ∈ {1, 2, 3, 5, 7, 10, 13, 15, 20, 30, 45, 60, 90, 120, 180, 240, 360, 480, 720, 1440} (perp 1m).
- **Per q:**
  - variance ratio VR(q) = Var(r_q) / (q Var(r_1)), over the base 1s or 1m;
  - lag-1 autocorrelation AC1 of non-overlapping q-returns;
  - for minute q, AC1 for every phase offset 0 … min(q, 60) − 1 (bar starts shifted). Report the min, median and max.
- **Null:** 100 sign-randomized paths. Bonferroni over all q × phase cells.
- **Economic check for any flagged q:** follow or fade the sign of the last q-return (phase 0), with net per trade at taker and maker.
- These are not selected for HOLD unless the net is > 0 on DISC.

## 8. What goes to HOLD (written to `hold_candidates.json` by the DISC stage, mechanically)
- **(a) T2 combined models:** every (θ, f) whose leave-one-month-out DISC net (taker) per taken trade is > 0, with ≥ 30 taken trades.
- **(b) T3:** every shortlisted config (§6).
- **(c) T1 economic:** every (θ, f, cost) whose DISC net CI lower bound is > 0.
- **(d) T4:** every flagged q with DISC net > 0.
- **Also, in every case (report-only):**
  - the T1 completion rates real vs null;
  - the T2 single-feature AUCs, for features that were "real" in DISC.

**HOLD pass for a candidate (all must hold):**
1. n ≥ 30 trades;
2. mean net > 0 with a day-block 95% CI lower bound > 0 at Bonferroni level α = 0.05 / k (k = number of candidates);
3. better than its null: z > 2 for T3; random-take control p < 0.05 for T2 and T1 (1,000 draws of the same number of events);
4. ≥ 3 of 4 HOLD months positive.

**Meaning:** a pass makes the candidate a **forward-watch candidate** only, under a separate locked amendment. It is not a claim of profit, because the 1m/5m months were seen by earlier studies (§0).

## 9. Logging (user's standing rule)
- Every trade of every T1 economic config, every T2 model and every T3 shortlist / HOLD config is written to parquet.
- Daily, monthly and (single-year) totals are written for every calendar day in each period, including days without trades (0).
- Files: `daily_*.csv`, `monthly_*.csv`.

## 10. Verifier (`src/audits/verify_turn_2026.py`, own code, plain loops)
- **V1:** protocol / input SHAs; HOLD not opened before `hold_candidates.json` existed (file mtimes and the stage log).
- **V2:** ZigZag pivots for θ 1% and 4% recomputed by a loop; all pivots identical.
- **V3:** T1 events and outcomes for θ 1%, f 0.5 recomputed by a loop; counts and completion share identical. The null P from its own sign-randomization (seed 777, 50 paths) must lie within 2 pp of the main null.
- **V4:** 300 random feature values (T2) recomputed from raw files.
- **V5:** 300 random detector states (T3) recomputed by loops for 12 detectors; 3 configs' trades replayed.
- **V6:** VR and AC1 for 5 q recomputed.
- **V7:** daily → monthly totals and calendar completeness.
- **V8:** the HOLD pass decisions recomputed from the trade files.

## 11. Report
- Hindi, `RESEARCH_TURN_DETECT_2026_<date>.md`. Every number is linked to its file.
- It states the "2022 → 2026" reading and the §0 data status.
