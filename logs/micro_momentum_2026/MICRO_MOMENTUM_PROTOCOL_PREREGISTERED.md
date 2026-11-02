# Micro-momentum study: "price rising for 1–3 minutes with volume → enter". BTC 1-second data, 2026. Locked 2026-10-27, before any download

This study is separate from all earlier studies: no shared code, no shared output folder.
- **Code:**
  - `src/data/fetch_binance_1s.py` (download);
  - `src/research/micro_momentum.py` (study);
  - `src/audits/verify_micro_momentum.py` (independent verifier: own csv/zip reading and loops, no import from the study code).
- **Outputs:** `logs/micro_momentum_2026/`.
- **Report (Hindi, one file):** `RESEARCH_MICRO_MOMENTUM_1S_2026_<date>.md`.

## 0. What the user asked (2026-10-27)

- A candle is only a picture of price arithmetic. The price comes first and the candle after.
- If the price keeps rising, minute after minute (1, 2, 3 minutes), with a rhythm and with volume, that is the time to enter.
- If it keeps falling with volume, a red is coming: exit.
- Scan at the finest level available, and research how to decide the entry. Ground-level, no shortcuts, same discipline.
- **Download permission:** given by the user on 2026-10-27 for:
  - Binance spot BTCUSDT 1s klines, 2026-01 … 2026-09;
  - Binance USD-M futures BTCUSDT 1m klines, 2026-01 … 2026-09.

## 1. Honesty rules (fixed now)

1. **The question is predictive, not descriptive.**
   - "Rising now" is known.
   - The test is whether the move **after** the signal, measured from a fill that happens after the signal, is larger than the cost.
   - Every future return starts at least 1 second after the signal second.
2. **Split by time:**
   - **DISC** = 2026-01 (discovery; the user's month);
   - **VAL** = 2026-02 … 2026-05;
   - **HOLD** = 2026-06 … 2026-09.
   - HOLD is sealed: no statistic of any kind (not even Part A) is computed on HOLD until §7 has picked at most one config. HOLD is then opened once.
   - If nothing is picked, HOLD stays sealed for a later idea.
   - Before HOLD is opened, the HOLD zips are only checksum-checked at download (no unzip, no read). QC of HOLD months (§2.2–2.3) runs only when HOLD is opened.
   - **Known prior use, recorded honestly:** 2026 5m/1h/1d data was used by the oracle, green-candle and methods-bench studies. This 1-second data is new to the project, but the minute-level moves inside it overlap with that earlier use.
3. **Costs come only from `deploy/fees.json`:**
   - futures taker per side `rules.paper_futures_taker_per_side` = 0.00046 (fee + impact), i.e. 0.092% per round trip. This is the primary cost.
   - spot per side `rules.paper_spot_per_side` = 0.00085, i.e. 0.17% per round trip;
   - maker sensitivity per side `futures_usdm.bnb_maker` + `impact_per_side` = 0.00028 (a sensitivity row only; maker fills are not guaranteed).
4. **Price source:**
   - Prices are **spot** BTCUSDT 1s closes (last trade of the second).
   - The futures 1m klines are used only to measure how closely spot and futures move (§2.3). That number is reported next to any futures-cost result.
5. Every win rate gets a 95% Wilson interval. No claim of perfect accuracy. No result is presented without its cost line.
6. Any change after this lock is written to `CODE_CHANGES.md` (time-stamped) before the changed code produces a number that is used.

## 2. Data

### 2.1 Files
- **Spot 1s:** `data/spot/monthly/klines/BTCUSDT/1s/BTCUSDT-1s-2026-MM.zip`, MM = 01 … 09.
- **Futures 1m:** `data/futures/um/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-2026-MM.zip`, MM = 01 … 09.
- **Source:** the official Binance bucket, data.binance.vision.
- **Integrity:** each zip is checked against Binance's own `.CHECKSUM` (sha256) and is kept only if it matches.
- **Storage:** `data/external/binance_1s/` (new, empty directory). Manifest: `MANIFEST.csv` (key, bytes, sha256, checksum_ok, time).
- **Reading:** read as data only (csv inside zip). Nothing in them is executed.

### 2.2 Spot 1s columns and QC
- **Columns:** open_time, open, high, low, close, volume, close_time, quote_volume, count, taker_buy_base, taker_buy_quote, ignore.
- **Timestamp unit:** the open_time unit is detected from the magnitude (µs if > 1e14, else ms) and logged.
- **Grid:** every UTC second of the month.
  - A missing second is filled with close = the previous close, volume = taker_buy = count = 0, and flagged.
  - Missing seconds are counted per day and reported.
  - A day with > 1% missing seconds is reported. It is not dropped.
  - Duplicate seconds are counted; the first row is kept.
- **Integrity check against the existing 5m file:**
  - 5m bars built from the 1s data must equal `data/universe_hf/5m/BTCUSDT_5m_full.csv.gz` on open, high, low and close (relative tolerance 1e-9) for every 5m bar of the months processed.
  - Every 5m volume must match within 1e-6 relative.
  - Mismatches are counted and reported, never fixed silently.

### 2.3 Spot vs futures alignment
- For each processed month, compute 1-minute log returns from spot (1s data → 1m) and from the futures 1m file.
- Report:
  - their correlation;
  - the mean absolute difference;
  - the share of minutes where the sign differs.

## 3. Definitions (P_t = spot close of second t; all windows end at t and use seconds ≤ t only)

**Windows:** W ∈ {60, 120, 180, 300} seconds.

**Features at second t:**
- **R_W** = P_t / P_{t−W} − 1.
- **UPMIN(t)** = the largest n ≤ 10 such that P_t > P_{t−60} > P_{t−120} > … > P_{t−60n}.
  - In words: the price was higher than one minute earlier, n times in a row, on a sliding minute grid.
  - This is the user's "1 minute, 2 minutes, 3 minutes continuously up".
  - **DOWNMIN(t)** is the same with "<".
- **RHYTHM_W** = up / (up + down) over the seconds in (t−W, t].
  - Up = close above the previous second's close; down = close below it.
  - If there are no changes, the value is NaN.
- **STRAIGHT_W** = |P_t − P_{t−W}| / Σ|P_s − P_{s−1}| over s in (t−W, t].
  - It ranges from 0 to 1; 1 means a straight line. If the denominator is 0, the value is NaN.
- **VOLR_W** = the volume in (t−W, t] divided by W × (the mean volume per second over (t−W−3600, t−W]).
  - In words: the current window's volume relative to the hour before it. NaN if that hour had no volume.
- **TAKER_W** = Σ taker_buy_base / Σ volume over (t−W, t]. NaN if the volume is 0.

**Future return** (latency L = 1 s, horizon h ∈ {30, 60, 120, 180, 300, 600} s):
- F_h(t) = P_{t+1+h} / P_{t+1} − 1.
- In words: you act one second after the signal second and hold h seconds.
- **Month boundary:** the features need the prior hour, and the future needs t+601. Seconds without the full history or future inside the processed month are excluded. The first hour plus 300 s of each month and the last 601 s are lost.

## 4. Part A: the mathematics first (DISC = 2026-01 only)

**A1. Unconditional F_h** for each h:
- mean, std, p5, p50, p95;
- the share of seconds with |F_h| > 0.092% and with |F_h| > 0.17%.

**A2. Conditional means by decile:**
- For each feature (R_W, RHYTHM_W, STRAIGHT_W, VOLR_W, TAKER_W, for every W) and each h, report the mean of F_h per decile of the feature.
- The decile cut points are computed on DISC (descriptive).
- Also reported: the top-decile mean minus the overall mean.

**A3. E[F_h | UPMIN = n]** for n = 0, 1, 2, 3, 4, 5+, and the same for DOWNMIN (the mirror). Count of seconds per cell.

**A4. The user's combination, as events.**
- An event starts at the first second where the condition is true after a second where it was false.
- Conditions:
  - UPMIN ≥ N, N ∈ {1, 2, 3};
  - VOLR_60 ≥ k, k ∈ {1, 1.5, 2, 3};
  - TAKER_60 ≥ s, s ∈ {0, 0.55, 0.60}, where s = 0 means no taker filter.
- Mean F_h per event, n events. Mirror (DOWNMIN with TAKER_60 ≤ 1 − s) reported the same way.

**A5. Uncertainty:**
- Every A2–A4 mean gets a 95% CI from a day-block bootstrap: resample the 31 days with replacement, 2,000 resamples, seed 7.
- Seconds are heavily overlapping, so iid CIs are not used.

## 5. Part B: tradable rules (long only, one position at a time)

**Entry signal E(N, k, s) at second t:**
- UPMIN(t) ≥ N, VOLR_60(t) ≥ k and TAKER_60(t) ≥ s, with the grid of §4 A4.
- The signal must **start** at t: it was false at t−1.
- If flat → buy at P_{t+L}.

**Latency:** L = 1 s (primary); L = 5 s (a sensitivity row for the configs reported in §7).

**Exits:**
- **XT60, XT180, XT300, XT600:** sell at P_{e+h}, where e is the fill second and h = 60 / 180 / 300 / 600 s.
- **XU (the user's exit):** sell at P_{t'+L} at the first second t' > e where the "falling with volume" signal holds:
  - DOWNMIN(t') ≥ 1;
  - RHYTHM_60(t') < 0.5;
  - VOLR_60(t') ≥ 1.
  - A cap of 1800 s from e applies (sell at P_{e+1800}).

**Grid:** 36 entries × 5 exits = **180 configs**.

**Other trade rules:**
- After an exit fill at second x, a new entry needs a signal start at a second > x.
- A trade whose exit would fall after the last usable second of the period is closed at that second's close and flagged `forced`.
- **Per trade:** gross = exit/entry − 1; net = gross − 2c for each cost mode.
- **Metrics per (config, period):**
  - n trades;
  - win rate with its Wilson interval;
  - mean, median and sum of net;
  - compounded net;
  - max drawdown;
  - trades per day;
  - average hold in seconds;
  - number of forced trades.

**Daily / monthly logging:**
- Net P&L is attributed to the UTC day of the exit fill.
- Every day of every processed month is written for every config (0 if no trade).

## 6. Statistics for Part B

- **CI of the mean net per trade:** day-block bootstrap (resample days within the period), 2,000 resamples, seed 7.
- **Random control** (only for configs that reach §7 steps 2–3):
  - 1,000 seeds; each trade is replaced by a long with the same holding seconds, entered at a uniformly random usable second of the same period, with the same cost;
  - p = the share of seeds with mean net ≥ the actual mean net.

## 7. Selection and decision (fixed now)

1. **DISC → VAL shortlist.** On DISC, with futures taker cost, a config is shortlisted if:
   - n ≥ 30 trades;
   - mean net > 0;
   - the day-block 95% CI lower bound > −0.05% (a loose filter, because DISC is only one month).
   - At most the 10 best by DISC mean net go forward.
   - **If the shortlist is empty, Part B stops here.** The full grid is still run on VAL and reported for transparency, and HOLD stays sealed.
2. **VAL test (the shortlist only).** A config passes if:
   - the VAL mean net > 0;
   - the VAL day-block CI lower bound at 1 − 0.05/m > 0, where m = the shortlist size (Bonferroni);
   - the random control p < 0.05;
   - at least 3 of the 4 VAL months have net > 0.
3. **HOLD (opened once).** Of the configs that pass VAL, only the one with the highest VAL mean net is run on HOLD.
   - It is a **forward-watch candidate** if the HOLD mean net > 0 and the HOLD day-block 95% CI lower bound > 0.
   - Even then, it is only a candidate for forward paper tracking through a separate FWD-WATCH amendment. It is never a live trading claim.
4. **Latency sensitivity:** the L = 5 s result is reported for every shortlisted config. A config whose L = 5 s mean net is ≤ 0 is flagged "latency-fragile" in the report.

## 8. Verifier (`src/audits/verify_micro_momentum.py`), checks M1–M7

- **M1.** The protocol SHA, the download manifest (each zip sha256 equals the Binance CHECKSUM, recomputed) and the SHA of every output file.
- **M2.** For DISC it re-reads the 1s zip with `zipfile` + `csv` and its own second grid. At 3,000 random usable seconds (seed 99) it recomputes R_60, R_300, UPMIN, DOWNMIN, RHYTHM_60, STRAIGHT_60, VOLR_60, TAKER_60 and F_60 / F_300, and compares them with the main output (tolerance 1e-9 relative; NaN must match NaN).
- **M3.** For DISC it rebuilds the 5m OHLC from its own grid and checks it against the 5m file (count of mismatches must equal the main script's).
- **M4.** For DISC it recomputes, with its own loops, every trade of 6 configs:
  - the best DISC config;
  - the worst DISC config;
  - E(1, 1, 0) and E(3, 2, 0.6), each with XT60 and XU.
  - Entry/exit seconds and prices must match exactly; net within 1e-12.
- **M5.** For DISC, A3 counts (UPMIN 0 … 5+) and their mean F_60 are recomputed and compared.
- **M6.** For VAL, the trade count and sum of net of the same 6 configs are compared.
- **M7.** The shortlist and the decision follow §7 exactly, recomputed from `metrics.csv`.

## 9. Outputs (`logs/micro_momentum_2026/`)

- `download_manifest.csv`;
- `qc_months.csv` (missing / duplicate seconds per day, 5m check, spot-futures alignment);
- `features_sample_disc.parquet` (the 3,000 verifier seconds with all features: the main script writes the same seed-99 sample);
- `partA_disc.json`;
- `partA_deciles_disc.csv`;
- `partA_events_disc.csv`;
- `trades_<period>.parquet`;
- `metrics.csv`;
- `daily.csv`;
- `monthly.csv`;
- `random_control.csv`;
- `decision.json`;
- `RESULTS.json`;
- `OUTPUT_SHA256.txt`;
- `run_log.txt`;
- `verify_output.txt`.
