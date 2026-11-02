# Root-cause study: why the ecosystem does not make steady (monthly or daily) profit. Pre-registered 2026-10-25

This protocol is locked with SHA256 before any number of this study is computed. It is a diagnostic: no strategy is selected here, and nothing goes live from it.

## User's challenge (2026-10-25, paraphrased)

- **Possible faults:** something must be wrong in the research, the training, the backtest, the formula or the implementation.
- **The user's premise:** the market always moves more than the minimum spread / fee within 5–15 minutes. Buying and selling anywhere should therefore make a profit above the fee, whatever the timeframe, on spot and futures.
- **The ask:** find the mistake, and find what is needed for steady daily profit.

## Fee ground truth (recorded before this lock)

- **Futures:** the demo account's `/fapi/v1/commissionRate` (2026-10-25) is maker **0.020%**, taker **0.040%** (BTC, ETH, SOL); feeBurn off.
- **Spot:** VIP 0 is 0.100%, or 0.075% with BNB (the official page, recorded in `logs/cost_study_step2/STEP2_COST_PROTOCOL_PREREGISTERED.md`).
- **Measured impact:** median about 0.010% per fill at 333–1,000 USDT (`cost_table_preliminary.csv`).
- **Round-trip costs used here:**
  - C1 futures maker + maker = 0.040%;
  - C2 futures taker + taker = 0.080%;
  - C3 spot BNB taker both sides + impact = 0.170%.

## Data

- `data/universe_hf/5m/<coin>_5m_full.csv.gz` for CORE10 (ADA, BNB, BTC, DOGE, DOT, ETH, LINK, LTC, SOL, XRP), 2020-01-01 … 2026-09-30, UTC.
- `data/universe_all/1d/BTCUSDT_1d.csv`.
- `data/futures_um/BTCUSDT_funding.csv`.
- `data/derived/eco/e2_daily_series.parquet`.
- `logs/eco/claims_eco_e2.json`.
- `logs/eco/monthly_outlook/MONTHLY_OUTLOOK_RESULTS.json`.
- The SHA of every file goes into `input_manifest.csv`.
- **Periods:** A = 2020-01-01 … 2025-09-30, and B = 2025-10-01 … 2026-09-30 (the ECO P3 year).

## Tests

**R1. Cost assumptions vs truth.**
- A table of the cost parameters in the live producers, read from the code:
  - N1 `n1_portfolio.py`: FEE 0.054%, FEE_SPOT 0.085%;
  - F4 1D: long fill 0.25%, short fill 0.10%, stop slippage 1%;
  - ECO `fee`.
- Each is compared with the truth above.
- The measured size of cost effects is taken from the E-3 decomposition (`E3_E4_RESULTS.md`). No re-run.

**R2. "Movement above the fee is profit" (random entries).**
- Per coin and horizon h ∈ {5m, 15m, 1h, 4h, 1d} = {1, 3, 12, 48, 288} 5m bars, on non-overlapping blocks of h bars.
- Entry at the block's first open. The direction is a fair coin (seed 2026).
- **Exit (a):** the close of the block's last bar.
- **Exit (b):** first touch of TP = +d or SL = −d from the entry, with d = m × C and m ∈ {1, 2, 5}, else the block's last close. Inside the block the 5m highs and lows are used.
  - If one bar touches both TP and SL, the SL is taken first (conservative). The TP-first variant is also reported, as the optimistic bound.
- **Net** = gross − C, for C ∈ {C1, C2, C3}.
- **Report:** mean net, win rate, and P(|gross| > C) vs P(signed gross > C), for periods A and B.

**R3. The accuracy needed vs the accuracy available.**
- Per horizon, E|r| over the CORE10 blocks. The break-even hit rate for symmetric moves is p* = 0.5 + C / (2 E|r|).
- **Available:** two fixed one-rule predictors on the same blocks:
  - MOM: direction = sign of the previous block's return;
  - REV: direction = the opposite sign.
- **Report:** their hit rate and mean net per horizon and cost, periods A and B.

**R4. Oracle bound (information).** Perfect direction: mean (|r| − C) per horizon.

**R5. Regime dependence of the ecosystem.**
- Monthly ECO-W2 returns (dev + P3 months from the outlook results) against two BTC measures of the same calendar month:
  - |BTC month return|;
  - the efficiency ratio ER = |close_end / close_start − 1| / Σ |daily return|.
- Spearman correlations.
- Calendar-year returns of `N1_alone` and `1D_alone_combo`, from the dev and P3 columns, next to the BTC year return.

**R6. In-sample → out-of-sample shrinkage.** CAGR and Calmar, dev vs P3, for ECO-W1, ECO-W2, N1_alone, 1D_alone_combo and 1D_alone (from `claims_eco_e2.json`).

**R7. Daily-profit reality.** The share of positive days for:
- ECO-W2 in dev and in P3;
- BTC funding carry (short-perp funding received per UTC day) in periods A and B.

## Reading rules (fixed now)

- **The premise is refuted** if, at every horizon and cost, the random-entry mean net is ≤ 0 within its 95% CI (t-interval over the blocks).
- **A "cost blunder" explains the P3 weakness only if** the measured cost effect is ≥ 50% of the dev-vs-P3 monthly return gap.
- **A "regime" explanation is supported** if the Spearman of the ECO month return vs BTC ER is ≥ 0.3, or the component year returns follow the BTC year return (Spearman ≥ 0.6).
- **Overfit is supported** if the P3 CAGR < 25% of the dev CAGR for the selected ECO-W2.

## Verifier (`src/audits/verify_root_cause.py`, own code)

- R2(a) and R2(b) for BTC at 1h and 4h, recomputed by plain loops (mean net and win rate equal within 1e-9).
- R3 for BTC: E|r| and the MOM hit rate.
- R5: the two Spearman values.
- R7: the ECO share of positive days.
- Manifest SHAs.

## Output

- `logs/research_root_cause/`.
- The Hindi report `RESEARCH_ROOT_CAUSE_25_OCT_2026.md`.
