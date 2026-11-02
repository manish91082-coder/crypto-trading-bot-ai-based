# Green-candle study: BTC January 2026, all timeframes, plus the frozen rule on other periods. Locked 2026-10-27

This study is separate from the methods bench (`logs/research_methods_bench/`) and the oracle study (`logs/oracle_9m_2026/`).
- No shared code, no shared output folder.
- Code: `src/research/green_candle.py`.
- Verifier: `src/audits/verify_green_candle.py`, written separately. It uses only `gzip`/`csv` and plain Python loops, and no code from the main script.
- Outputs: `logs/green_candle_2026/`.
- Report (Hindi, one file): `RESEARCH_GREEN_CANDLE_JAN_2026_27_OCT_2026.md`.

## 0. What the user asked (2026-10-27)

- Take BTC January 2026 on every timeframe: 5m, 15m, 30m, 1h, 4h, 1d.
- Study the green candles: a green candle means the price went up from its open. Consecutive greens mean it kept going up.
- Build a mathematical description of how the market moved.
- **The user's trading idea:**
  - enter when the colour turns red → green;
  - exit when it turns green → red;
  - "a little early or late is fine".
- Same discipline as before; write it in one file.

## 1. Honesty rules (fixed now)

1. **Hindsight vs tradable.**
   - A candle's colour is known only after it closes.
   - "Catching every green candle" is a hindsight number (oracle), reported as such and never as a strategy result.
   - A tradable rule acts on the next bar's open after the deciding bar has closed.
2. **The user's rule is fully specified, with no tunable parameter.** The study fits nothing; it measures the rule as stated.
3. **January 2026 is the description period.**
   - The frozen rule is then checked on February–September 2026 and on 2020-01-01 … 2025-12-31.
   - **Known prior use, recorded honestly:**
     - 2020–2025 was used once before, by oracle Part D and by the methods bench;
     - 2026 was used by the oracle study;
     - neither tested this rule.
   - The data is not pristine, but the rule was not chosen by looking at those periods.
4. **Costs come only from `deploy/fees.json`:**
   - spot per side `paper_spot_per_side` = 0.00085, i.e. 0.17% per round trip;
   - futures per side `paper_futures_taker_per_side` = 0.00046, i.e. 0.092% per round trip;
   - futures maker sensitivity per side `bnb_maker` + `impact_per_side` = 0.00028.
5. Every win rate gets a 95% Wilson interval. No claim of "perfect" accuracy.
6. Any change to code or definitions after this lock is written to `CODE_CHANGES.md` before any result is used.

## 2. Data

- **Base:** `data/universe_hf/5m/BTCUSDT_5m_full.csv.gz` (UTC; the timestamp is the bar's open time).
- **Check files:** `data/universe_hf/15m/BTCUSDT_15m_full.csv.gz`, `data/universe_all/1h/BTCUSDT_1h_full.csv.gz`, `data/universe_all/1d/BTCUSDT_1d.csv`.
- **Manifest:** the SHA256 of every input goes to `input_manifest.csv` before the run.
- **Timeframes:** TF = 5m, 15m, 30m, 1h, 4h, 1d.
  - 15m … 1d are aggregated from 5m by UTC clock: a bar covers [t, t+TF) and is labelled by t.
  - Aggregation: open = first, high = max, low = min, close = last.
  - A bar exists if at least one 5m bar falls in it. Bars with fewer 5m bars than full are counted and reported as "incomplete".
- **Check:** the 15m, 1h and 1d aggregates must equal the files (OHLC, relative tolerance 1e-9) over the whole period. Any mismatch is reported, never silently fixed.
- **Periods:**
  - JAN = 2026-01-01 00:00 … 2026-01-31 23:55;
  - FS26 = 2026-02-01 … 2026-09-30;
  - Y2020 … Y2025 = calendar years;
  - P2025 = 2020–2025 pooled.
  - The manual-study day 2026-02-13 is **not** excluded: the rule has no fitted parameter, so that day cannot bias it.

## 3. Definitions

- **Candle return:** r = C/O − 1.
- **Colour:** G if C > O, R if C < O, D (doji) if C = O.
- **Green run:** a maximal block of consecutive G bars, of length L ≥ 1. A D or an R ends a run.
- **Run anatomy, for a green run of bars k … k+L−1 followed by bar k+L:**
  - g1 = r of the first green bar;
  - rest = C_{k+L−1} / C_k − 1, the move of greens 2..L, measured close to close (0 when L = 1);
  - after = r of bar k+L (the bar that ended the run), if it exists.

## 4. Part A: description of January 2026 (per TF)

- **A1.** n bars and the share of G / R / D. The G share gets a Wilson 95% interval.
- **A2.** Candle-return distribution for G and for R: mean, median, p25, p75.
  - Also the share of G bars with r > 0.17% (the spot round trip) and r > 0.092% (the futures round trip).
- **A3. Does colour predict the next colour?**
  - The transition matrix P(next | this) over {G, R, D}.
  - The Wald–Wolfowitz runs test on G vs not-G: z and two-sided p.
  - The lag-1 autocorrelation of r.
  - Reading: if P(G | G) ≈ the G share, the colour is close to a coin flip.
- **A4. Green-run length distribution** (L = 1, 2, 3, 4, ≥ 5).
  - Observed counts vs the counts expected if colours were independent with the observed G share p: P(L = k) = (1 − p) p^(k−1).
- **A5. Hindsight oracle "catch every green run":**
  - gross per run = C_last / O_first − 1;
  - net = gross − 2c for spot and for futures.
  - Reported: the sum over runs (simple sum, no compounding), the number of runs, and how many runs are still profitable after costs even with perfect hindsight.
  - Also the simple sum of all individual G candle returns.
- **A6. Run anatomy means:** g1, rest and after. These are the pieces the formula in §5 needs.

## 5. The formula (stated before the run)

For the user's rule (§6, R1):
- **Entry:** the open after green #1 closes, ≈ C_k.
- **Exit:** the open after the first red closes.
- **Without dojis, one trade =**
  - rest (greens 2..L)
  - \+ the first red's return
  - \+ open/close gaps
  - − 2c.
- **Relation to the hindsight run move:** oracle run move = g1 + rest. The rule misses g1 by construction and pays back one red candle.
- **The test:** R1 can be profitable only if E[rest] + E[first red] > 2c.
- **Coin-flip reading.** If colours are independent with G share p:
  - the expected number of further greens after green #1 is p/(1 − p);
  - E[rest] ≈ p/(1 − p) · E[r | G];
  - the giveback E[first red] = E[r | R] < 0.
  - Then the trade's expectation ≈ the unconditional mean of r times the bars held, i.e. close to 0 before costs.
- All these pieces are measured directly. The report states the measured values, and uses this reading only to interpret them.

## 6. Part B: the tradable rules (long only, one position at a time)

### R1, the user's rule exactly
- **Entry:** at the close of bar k, if flat and colour_k = G and colour_{k−1} ≠ G → buy at O_{k+1}.
- **Exit:** while long, at the close of bar m, if colour_m = R → sell at O_{m+1}.
- D bars are held through.

### R2, one confirmation variant (the only other rule)
- **Entry:** as R1, but it needs two consecutive G bars (colour_k = G, colour_{k−1} = G, colour_{k−2} ≠ G).
- **Exit:** same as R1.

### Shared rules
- **Period end:** a position still open at the last bar of a period is closed at that bar's close and flagged `forced`.
- **Each period is run on its own:** no position carries across periods.
- **Per trade:** gross = exit/entry − 1; net = gross − 2c for each cost mode.
- **Metrics per (rule, TF, period, cost mode):**
  - n trades;
  - win rate (Wilson 95%);
  - mean, median and sum of net;
  - compounded equity;
  - maximum drawdown of compounded equity;
  - time in market;
  - average bars held;
  - buy-and-hold of the period: last close / first open − 1.
- **Bootstrap:** a 95% CI of the mean net per trade, iid over trades, 10,000 resamples, seed 7.
  - For the decision in §7, Bonferroni over 12 configs (2 rules × 6 TF): a 99.583% CI.
- **Random control** per (rule, TF, period), 1,000 seeds (seed s = 1 … 1000):
  - each actual trade is replaced by a long with the same number of bars held, entered at a uniformly random bar open of the same period (overlap allowed), with the same cost;
  - p = the share of seeds whose mean net ≥ the actual mean net.
- **Daily / monthly / yearly logging:** net P&L is attributed to the UTC day, month and year of the trade's **exit**.
  - Daily tables cover every day of January 2026, days with no trade written as 0.
  - Monthly and yearly tables cover all periods.

## 7. Part C: decision rule (fixed now)

A (rule, TF) is called a **candidate** only if **all** of these hold with futures taker costs:
1. P2025 pooled: the Bonferroni 99.583% CI lower bound of the mean net per trade > 0.
2. FS26 pooled: the mean net per trade > 0.
3. At least 60% of the 81 months (2020-01 … 2026-09) have net > 0.
4. P2025 random-control p < 0.05.

A candidate is not a trading claim. At most it can go to forward paper tracking through a separate FWD-WATCH amendment. If no config is a candidate, the report says so plainly.

## 8. Verifier (`src/audits/verify_green_candle.py`), checks V1–V6

- **V1.** The protocol SHA equals `PROTOCOL_SHA256.txt`; the input SHAs equal `input_manifest.csv`.
- **V2.** It rebuilds 15m … 1d from the 5m csv with its own loop for JAN and compares every OHLC with the main output. It also checks that the 15m / 1h / 1d aggregates equal the files for JAN.
- **V3.** For JAN, per TF, it checks:
  - the counts of G / R / D;
  - the 3×3 transition counts;
  - the number of green runs and the run-length counts;
  - the oracle sums.
- **V4.** For JAN, per TF and rule, it compares every trade with the main trade list: entry/exit time, entry/exit price and net (tolerance 1e-9).
- **V5.** For every period, rule and TF, it checks the trade count and the sum of net (futures).
- **V6.** The output SHA file matches the output files.

**Hand check, in the report:** all 31 1d candles of January 2026 are listed with O/H/L/C, colour and r. The R1 trades on 1d are worked out by hand in the report and must equal the script.

## 9. Outputs

All in `logs/green_candle_2026/`:
- `input_manifest.csv`;
- `bars_jan2026.parquet` (all TF bars of JAN with colour and r);
- `partA_jan2026.json`;
- `runs_jan2026.csv`;
- `trades_all.parquet`;
- `metrics.csv`;
- `daily_jan2026.csv`;
- `monthly.csv`;
- `yearly.csv`;
- `random_control.csv`;
- `decision.json`;
- `RESULTS.json`;
- `OUTPUT_SHA256.txt`;
- `run_log.txt`;
- `verify_output.txt`.
