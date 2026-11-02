# N3: EVT tail-risk monitor (pre-registered; information only, no trading rule)

- Code: `src/execution/n3_evt_monitor.py`
- Synthetic validation: `src/audits/test_n3_evt_synthetic.py`
- Verifier: `src/audits/verify_n3_monitor.py`

No orders. No change to any trading rule. It does not count as a strategy trial.

## Method: peaks-over-threshold (POT) with a generalized Pareto tail
Sources:
- McNeil & Frey (2000, *Journal of Empirical Finance*)
- Embrechts, Klüppelberg & Mikosch (1997)
- Crypto backtest support: Opala, Fischer & Svoboda (2022): POT was the only method passing a 99.9 % backtest for BTC / ETH / LTC

**Steps:**
- **Loss:** L = −daily return of the line's mix equity.
- **Threshold:** u = the 90th percentile of L in the fitting sample. Excesses y = L − u for L > u. N_u = number of excesses, n = sample size.
- **Fit:** ξ, β from `scipy.stats.genpareto.fit(y, floc=0)` (maximum likelihood).
- **Estimates:**
  - VaR_p = u + (β/ξ)·[((n/N_u)(1−p))^(−ξ) − 1]
  - ES_p = VaR_p/(1−ξ) + (β − ξu)/(1−ξ), valid for ξ < 1
  - p = 0.99 and 0.999
- **Validation before use** (`test_n3_evt_synthetic.py`): on 200,000 draws of a Student-t (ν = 4) loss, the estimates must match the true t quantiles within 5 % (VaR99, VaR99.9) and the true ES99 within 10 %. On an exponential sample (ξ ≈ 0) VaR must match within 5 %.

## Lines and data
| Line | Fitting sample | Forward days |
|---|---|---|
| **LS_RS** (F4 primary) | F7 RS backtest mix daily returns (`logs/strategy_f7_risk/equity_MAIN_AI_RS.csv`, 2021–26) | F4 ledger days, appended as they arrive |
| **LO** (16B spot paper) | F7 OFF_LO mix daily returns (= Step 27 M_AI3-50 %) | 16B forward days, appended |

**Each day after F4 (task 09:30 IST):**
- Fit on the backtest + all forward days up to yesterday.
- Write the estimate for the NEXT forward day.
- Then, when that day arrives, record whether its loss exceeded VaR99 / VaR99.9.
- Hash-chained ledger: `logs/monitor_n3_evt/ledger.csv`.

## Evaluation at forward day 90 (no trading consequence)
- **Kupiec unconditional-coverage test** of the 99 % VaR on the forward days: number of exceedances vs the expected 0.9.
- **Reported:** exceedances, p-value, and whether the 35 % kill switch and the per-coin caps are consistent with the estimated tail (e.g. the 99.9 % one-day ES).
- Any proposal to change a limit is a NEW pre-registered decision.
