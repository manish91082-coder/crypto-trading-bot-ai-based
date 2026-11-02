# ECO 10,000 USDT: what a month can look like. Descriptive analysis, pre-registered 2026-10-25

This protocol is locked with SHA256 before any number is computed. **It is descriptive only:** nothing is fitted, chosen or changed, and it is not a forecast or a promise.

## Question (user, 2026-10-25)

If 10,000 USDT is put into the integrated ecosystem (ECO-W2, now running on the demo account), what is at the end of one month? The user asks for a worst, an average and a best case, all ground-verified.

## Evidence used (each with its SHA in the output)

1. **Backtest daily equity of the deployed design ECO-W2:** `data/derived/eco/e2_daily_series.parquet`, columns `dev|ECO-W2` and `P3|ECO-W2`.
   - The E-1 / E-2 verifier (`verify_eco_stdout.txt`) reproduced these numbers.
   - **dev** = 2021-01-01 … 2025-09-30. The strategies and the weights were chosen on it, so it is **in-sample** and optimistic.
   - **P3** = 2025-10-01 … 2026-09-30. It was "report only" in the ECO protocol, not used for the selection. It is the most recent year.
2. **Live plan ledger** `data/eco/ledger.jsonl` (VM, hourly since 2026-10-21 19:03 UTC). The eco equity of real forward cycles: paper fills at the mark, no orders.
3. **Measured execution gap:** the E-3 replay of 2026-09 (`E3_E4_RESULTS.md`): executor 9,817.25 vs paper combination 9,697.27. **It is reported as recorded and not blended into the backtest numbers.**
4. **Structural limits from the config** (`deploy/eco_config.json` v3): kill switch K = 0.30 of the peak, the outage guard at ±50%, coin cap 20%, gross cap 1.5.
   - These are design limits, tested in `test_eco_core.py` (T7, S6, A2-2, A2-5). They are not performance numbers.

## Computations (on 10,000 USDT, k = 1)

**For each window, dev and P3 separately:**
- **Calendar months:** month return = last equity of the month / last equity of the previous month − 1. The first month of a window is measured from its first value.
  - Report: n, worst, P10, P25, median, mean, P75, P90, best, share > 0; and the USDT at month end = 10,000 × (1 + r).
- **Rolling 30 days** (every start day; equity at day d + 30 / equity at day d − 1): the same percentiles.
- **Within-month drawdown:** the worst peak-to-trough inside any 30-day span, as a % of 10,000.
- **Worst 3 consecutive calendar months.**

**Live:** eco equity at the first and the last ok cycle, the max and min, the number of cycles, and the days covered.

## Presentation rule

- **Worst / average / best** are given per window as **(worst month, median month, best month)**, with the mean shown next to them.
- The **P3** numbers are the primary ones, because they are the most recent and not used for selection.
- **dev** is shown as the optimistic upper reference.
- Every number names its window. **No single blended "expected" number is given.**

## Verifier (`src/audits/verify_monthly_outlook.py`, own code)

Plain loops recompute, from the parquet:
- every monthly return;
- the percentiles (nearest-rank cross-check against numpy linear interpolation within 1e-9: both are reported, and the report uses numpy linear);
- the rolling 30-day minimum and maximum;
- the live numbers from the ledger.

## Output

- `logs/eco/monthly_outlook/` (results JSON + SHA).
- The Hindi report `RESEARCH_ECO_MONTHLY_OUTLOOK_25_OCT_2026.md`.
