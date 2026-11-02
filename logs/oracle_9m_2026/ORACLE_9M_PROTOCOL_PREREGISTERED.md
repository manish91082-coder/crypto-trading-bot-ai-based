# 9-month BTC study 2026-01-01 … 2026-09-30: ground-truth oracle, frozen v1 formula test, method ranking. Locked 2026-10-26

This is the continuation of the manual 10-day study (`logs/manual_day_study/`, protocol SHA 4ad5f71f…).
It is kept **separate** from the methods bench (Batch 1, `logs/research_methods_bench/`):
- no shared code;
- no shared output folder;
- it does not read Batch 1 results.

Code:
- `src/research/oracle_9m.py`;
- verifier `src/audits/verify_oracle_9m.py`, written separately, using plain Python loops and no code shared with the main script.

Outputs go to `logs/oracle_9m_2026/`.

## 0. What the user asked (2026-10-26)

- Take the 2026 data (Jan … Sep, 9 months).
- For every day and every timeframe, find every entry / exit / direction that could make a profit after costs, and the maximum possible run.
- Log it in a compact, reusable, verified format.
- From it, build mathematical formulas and rank every direction / entry / exit method by how solid it is.
- Same discipline as before: no fake numbers, no shortcuts.

## 1. Honesty rules (fixed now)

1. **Oracle numbers are hindsight.** They measure what was available and are never presented as a strategy result.
2. **Strategy results use only bars closed at the moment of the decision.**
3. **2026 is the discovery set.** Any formula fitted or ranked on 2026 is in-sample.
   - It is accepted only after a locked test on 2020-01-01 … 2025-12-31.
   - Those years are sealed: no oracle, no rule run and no statistic is computed on them until Part D is locked.
   - Known leak, recorded honestly: Batch 1 of the methods bench (generic indicators) runs on 2020–2026, and its results may be seen before Part D. It shares no rule with this study.
4. **Excluded from all 2026 statistics:** 2026-02-13, the manual-study Day 10. It is reported separately.
5. **"Perfect accuracy" is not claimed for any rule.** Every win rate is reported with a 95% Wilson interval.
6. **Costs come only from `deploy/fees.json`:**
   - futures taker per side 0.00046 (`paper_futures_taker_per_side`), i.e. 0.092% per round trip;
   - spot per side 0.00085 (`paper_spot_per_side`), i.e. 0.17% per round trip;
   - futures maker per side 0.00018 + impact 0.0001 = 0.00028, used only as a sensitivity row.

## 2. Data (SHA of every input is written to `input_manifest.csv` before the run)

- **Bars:**
  - `data/universe_hf/5m/BTCUSDT_5m_full.csv.gz`: the base;
  - `data/universe_hf/15m/BTCUSDT_15m_full.csv.gz`;
  - `data/universe_all/1h/BTCUSDT_1h_full.csv.gz`;
  - `data/universe_all/1d/BTCUSDT_1d.csv`.
- **Window:** 2026-01-01 00:00 … 2026-09-30 23:55 UTC (273 days), plus 2025-12-01 … 2025-12-31 for prior-day / 7-day levels only.
- **Pre-check on 2026-10-26:** 5m 78,624, 15m 26,208, 1h 6,552 and 1d 273 bars, with 0 missing and 0 duplicates.
- **Derived timeframes:**
  - 15m, 30m, 1h and 4h are aggregated from 5m by UTC clock: bars [t, t+tf), labelled by their open time.
  - The verifier checks that the 15m and 1h aggregates equal the 15m / 1h files exactly. The 1d aggregate must equal the 1d file.
- **No 1m** exists for 2026 (raw 1m timestamps are corrupt after 2024).
- Day = one UTC calendar day.

## 3. Part A: the oracle dataset (hindsight measurement)

Timeframes **TF = 5m, 15m, 30m, 1h, 4h**. All values are per day, within the day (flat at 00:00 and at the 23:55 close).

### A1. Extreme oracle (5m)
- **Best long:** max over 5m bars i < j of H_j / L_i − 1.
- **Best short:** max over i < j of 1 − L_j / H_i.
- Recorded: entry / exit time and price, gross %, net futures % (gross − 0.092), and for longs net spot % (gross − 0.17).
- i < j strictly, because the order inside one 5m bar is unknown.

### A2. Close-to-close oracle (each TF)
- The price points are P_0 = open of the first bar, then P_k = close of bar k (k = 1 … n).
- **Best long:** max over a < b of P_b / P_a − 1.
- **Best short:** max over a < b of 1 − P_b / P_a.
- This is the best one could do deciding only at bar closes of that TF.

### A3. Maximum possible run (each TF, exact dynamic programming)
- Choose any set of non-overlapping trades on the price points P.
- A trade from a to b (a < b) is worth:
  - long: P_b / P_a − 1 − 2c;
  - short: 1 − P_b / P_a − 2c.
- A new trade may start at the point where the last one ended (a reversal).
- **Maximise the sum of trade values** (no compounding).
- **Modes:**
  - **FUT:** long + short, c = 0.00046;
  - **SPOT:** long only, c = 0.00085;
  - **FUT_MAKER:** sensitivity only, c = 0.00028.
- Recorded: the maximum total, the number of trades, and every trade in the optimal set.

### A4. Every trade of the optimal FUT and SPOT sets is stored
- date, tf, mode, side;
- entry_time, entry_px, exit_time, exit_px;
- bars held, gross %, net %;
- **MAE %** and **MFE %:** the worst / best 5m low / high between the entry point and the exit point, entry bar excluded. For an entry at the close of bar a: the bars a+1 … b.

### A5. Day descriptors

**Price and timing**
- O / H / L / C, return %, range %, volume;
- time of high and low (5m), and which came first;
- **body ratio** |C − O| / (H − L).

**Day type (fixed thresholds)**

| Body ratio | Type |
|---|---|
| ≥ 0.6 | TREND |
| ≤ 0.3 | RANGE |
| otherwise | MIXED |

**Context**
- first-8h range % = max H / min L − 1 over 00:00 … 07:55;
- prior-day H / L / C, and the prior close position in its range;
- 7-day H / L, from the 7 full prior days;
- distance in % from the day low and the day high to the nearest round thousand, prior-day low / high and 7-day low / high.

### A6. Sweep-reclaim events (15m; a base-rate table for the round-number warning of the 10-day study)

**Levels** for each day:
- round thousands k·1000;
- prior-day high and low;
- 7-day high and low.

**Events**
- **Bullish:** a 15m bar s whose low is below L and whose close is above L.
- **Bearish:** the mirror (high above L, close below L).
- One row per (bar, level).

**Recorded per event**
- time, side, level type, level, depth % = (L − low) / L, or (high − L) / L for the bearish side;
- whether bar s or bar s−1 (same day) set a new day extreme so far;
- whether a confirmation came within 2 bars (the H2′-c rule in §4);
- **forward labels:**
  - max favourable and max adverse excursion % from the close of s to the day's end;
  - return to the day close %;
  - whether the sweep low (or high) remained the day extreme.

### A7. Storage
- Parquet (zstd), one file per table:
  - `oracle_day.parquet`;
  - `oracle_tf.parquet` (A2 and A3 totals);
  - `oracle_trades.parquet` (A4);
  - `sweep_events.parquet` (A6).
- `SCHEMA.md` describes every column.
- `OUTPUT_SHA256.txt` holds a SHA256 for every output file.

## 4. Part B: frozen test of the 10-day formula v1 on 2026 (first out-of-sample check of v1)

The rules are written exactly as in `RESEARCH_MANUAL_10_DAYS_BTC_26_OCT_2026.md` §5. Where that text was ambiguous or used information not yet known, the choice is fixed here.

**Lookahead found in the 10-day table (recorded honestly):**
- Q1 needs the 00:00 … 07:55 range, which is known only at 08:00.
- Yet in the 10-day table it skipped Day 9, whose trade entered at 00:30.
- So the v1 + Q1 number there (+8.23%) contained lookahead.
- Here Q1 is applied in a real-time form.

### Signal: H2′-c, on the 15m bars of the day

**Levels:** round thousands, prior-day high / low, 7-day high / low.

**Long**

| Step | Condition |
|---|---|
| Sweep | Bar s has low_s < L and close_s > L for at least one level L |
| New day low | Bar s, or bar s−1 of the same day, set a new day low. Bar k sets one if k = 0 or low_k < min(low_0 … low_{k−1}) |
| Confirmation | Bar c is the first of s+1, s+2 with close > open, and every low of the bars s+1 … c is ≥ low_s. Without one, there is no trade |
| Entry | The open of bar c+1 |
| Stop | SL = low_s × (1 − 0.0025) |
| Risk | R = entry − SL |
| Target | TP = entry + 2R |

**Short:** the exact mirror, using a new day high and SL = high_s × (1 + 0.0025).

**Detail**
- If several levels qualify on one bar, it is one signal.
- One position at a time.
- A new signal is taken only if its entry bar opens at or after the previous exit time.
- Signals whose entry bar would be after 23:45 are not taken.
- If a long and a short both qualify on the same bar (impossible by construction) → skip.

### Execution (5m bars from the entry onward)

**SL / TP per 5m bar**
- If the open is beyond SL → exit at the open.
- Else if the low ≤ SL (long) → exit at SL.
- Else if the open is beyond TP → exit at the open.
- Else if the high ≥ TP → exit at TP.
- **The SL is checked first** when both fall in one bar.

**End of day:** an exit at the 23:55 bar close.

**Cost:** net = gross − 0.092% (futures). A spot long-only view uses gross − 0.17%.

### Variants (all reported; none is chosen after seeing the result)

| Variant | Rule |
|---|---|
| **V1-A** | H2′-c + SL / 2R TP / end-of-day exit |
| **V1-B** | V1-A + Q1 real-time: no entry before 08:00 UTC, and no entry at all that day if the 00:00 … 07:55 range < 1.0% |
| **V1-C** | V1-B + the day-type exit (below) |
| **V1-AC** | V1-A + the day-type exit (no Q1) |
| **V1-S** | V1-B, long only, spot cost |

**Day-type exit (V1-C, V1-AC):** while in a trade, the TP is removed and the position is held to the 23:55 close if either:
- (a) at 08:00 the first-8h range is ≥ 3.0%; it applies from the 08:00 bar onward;
- (b) a 5m bar's high goes above the prior-day high (long) or its low below the prior-day low (short); it applies from the next 5m bar. Within the bar that triggers it, the SL and TP are checked first.

**Not tested in v1 (recorded):** E1 ("target 0.1% before the level"). The 10-day text did not define it exactly, and defining it now after seeing those days would be a new fit.

### Reported per variant
- **Every trade** (`v1_trades.csv`).
- **Daily, monthly and full-period table** (`v1_daily.csv`, `v1_monthly.csv`). Days with no trade get a 0 row; no day is skipped.
- **Summary figures:**
  - trades, wins, win rate with Wilson 95%;
  - mean net % per trade, sum;
  - mean per day;
  - % months positive;
  - worst month;
  - max losing streak.
- **Capture:** v1 net vs the A3 FUT 15m oracle per day.
- **Random control:** 200 seeds.
  - Same number of trades, at random entry bars of the same days.
  - The same side mix, SL distance (the same R %) and exit logic.
  - Recorded: the share of seeds whose sum ≥ v1's.

**Pass condition for "v1 survives 2026"** (fixed now). All four must hold:
1. sum net > 0;
2. Wilson lower bound of the win rate > the break-even rate p* = (1 + cost / R̄) / 3, using the mean R of the variant (for a 2R target);
3. ≥ 5 of the 9 months positive;
4. random-control share ≤ 0.05.

Anything else = "v1 does not survive", reported as is.

## 5. Part C: method ranking on 2026 (in-sample; defined in Amendment 1 before it runs)

**Scoring metrics fixed now:**

| Kind | Metrics |
|---|---|
| **Direction methods** | Agreement with the oracle day direction (sign of the A3 FUT 15m net-long vs net-short, or close vs open), Wilson 95%; vs always-long and vs 50% |
| **Entry methods** | Distance from the A1 / A2 perfect entry (% and minutes); capture = realised gross / A2 best gross of that side |
| **Exit methods** | Share of the available MFE taken; giveback = MFE − realised |
| **Whole rules** | Net per trade and per day; weekly-cluster t; % months positive; worst month; random-control share |

- The method families and their exact definitions are written in Amendment 1, locked with SHA **before** any of them is scored.
- The ranking is one table, sorted by the lower bound of the 95% CI of mean net per day.

## 6. Part D: sealed test 2020–2025 (defined in Amendment 2 after Part C)

- The rules frozen at the end of Part C are run once on 2020-01-01 … 2025-12-31.
- Excluded: the 9 manual-study days in those years.
- The same metrics, gates and random control apply.
- Daily / monthly / yearly reports.

## 7. Part E: manual AI-reasoned days (continuation of the 10-day logs)

- **Selection:** one day per ISO week of 2026-01 … 2026-09, seed 20261027, numpy `default_rng`, uniform within the week's days in the window, excluding 2026-02-13.
- **Method:** the same as `logs/manual_day_study/MANUAL_DAY_STUDY_PROTOCOL.md`.
  - The reasoning is written before the calculator check;
  - `check_claims.py` verifies every number.
- **Files:** `logs/oracle_9m_2026/manual/day_NN_<date>.md`.
- They feed the hypotheses of Part C. They are not evidence.

## 8. Verification

`src/audits/verify_oracle_9m.py` must pass before any number is reported.

| Check | What it verifies |
|---|---|
| **K1** | Input SHAs and bar counts; the aggregates equal the 15m / 1h / 1d files |
| **K2** | A1 / A2 recomputed by plain double loops, for every day and TF |
| **K3** | A3 recomputed by a plain-loop interval DP, every day and TF and mode; the trade lists sum to the total. On 300 random 9-point windows, exhaustive enumeration of all trade sets equals the DP |
| **K4** | MAE / MFE recomputed for every stored trade |
| **K5** | Sweep events recomputed independently; equal row sets |
| **K6** | Part B re-implemented independently in plain loops; equal trade lists (times, prices, exits) and equal daily / monthly sums |
| **K7** | Costs read from `deploy/fees.json`; no other fee literal in the main code |

A step-by-step `run_log.txt` gets a timestamped line per stage.
