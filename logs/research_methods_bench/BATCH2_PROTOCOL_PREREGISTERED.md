# Methods bench Batch 2: A3 volatility + A4 volume / order flow. Pre-registered 2026-10-27

This protocol is locked with SHA256 before any Batch 2 number is computed. It is research only: no orders, and nothing live changes.

## 0. What applies unchanged

- **The bench:** `MASTER_BENCH_PROTOCOL_PREREGISTERED.md` Part 1 (0ee7aff8…) and `MASTER_BENCH_AMENDMENT_1_PREREGISTERED.md` (626f670a…) apply as written. That covers:
  - data, costs, scales, carry, entry and exits X1 / X2 / X3;
  - periods D / V / H / FULL, metrics, the 8-measure ranking, gates G1–G6;
  - random control for every configuration, R-stress, R-delay, R-year;
  - daily / monthly / yearly reports for both costs.
- **The engine:** the functions of `src/research/methods_bench.py` (46b16cd6…) and `src/research/btc_entry_study.py` are used unchanged.
- **DSR N** = 1,726 (Batch 1 N) + the number of Batch 2 primary configurations.

## 1. Honest status of H (stated before the run)

- H (2025-01-01 … 2026-09-30) was already used by Batch 1 and by NP4.
- The master protocol uses H once **per batch**. These Batch 2 rules have never been run on H, so their H numbers are a first evaluation. But the period is no longer pristine for the researcher.
- **Consequence:** an `edge = True` result in Batch 2 is **not** a claim of profit. It only makes the configuration a candidate for forward tracking (data from 2026-10-01 on) under a separate, locked amendment to FWD-WATCH. Only the forward result can support a claim.

## 2. Notation (on one scale frame; every value at bar t uses bars ≤ t only)

- **Bars:** o, h, l, c, v (base volume), qv (quote volume), tb (taker-buy base volume), nt (trade count). They are aggregated like the bench `agg`, adding qv and nt as sums.
- **Returns:** r_t = ln(c_t / c_{t−1}).
- **Primitives:**
  - **ATR_n:** Wilder ATR of the true range TR.
  - **EMA / SMA:** as in the bench.
  - **zs(x):** the bench z-score over 500 bars (min 250).
- **q(X)** = the rolling percentile rank of X_t among the last 500 values, including X_t (min 250; average rank for ties; pandas `rolling(500, min_periods=250).rank(pct=True)`).
- **TS20** = sign(c_t − c_{t−20}).
- **Readings:** "follow" is the signal as defined; "fade" is its negative.

## 3. Regime rules (non-directional measures, 16 measures × 4 readings)

A volatility or liquidity measure has no direction by itself. Each measure M is tested in the two standard regime readings, each with follow and fade:

| Reading | Signal |
|---|---|
| `LOW_follow` | q(M) < 0.2 → TS20, else 0 |
| `LOW_fade` | −(`LOW_follow`) |
| `HIGH_follow` | q(M) > 0.8 → TS20, else 0 |
| `HIGH_fade` | −(`HIGH_follow`) |

| ID | Measure M | Exact definition |
|---|---|---|
| A3.01 | NATR14 | ATR14 / c |
| A3.02a | RV20 | std (ddof 1) of r over 20 bars |
| A3.02b | EWMA | sqrt of ewm(r², alpha 0.06, adjust False, min_periods 20) (RiskMetrics λ 0.94) |
| A3.03a | Parkinson20 | sqrt(mean_20(ln(h/l)²) / (4 ln 2)) |
| A3.03b | GarmanKlass20 | sqrt(mean_20(0.5 ln(h/l)² − (2 ln 2 − 1) ln(c/o)²)) |
| A3.03c | RogersSatchell20 | sqrt(mean_20(ln(h/c) ln(h/o) + ln(l/c) ln(l/o))) |
| A3.03d | YangZhang20 | sqrt(σo² + k σc² + (1 − k) σrs²); σo² = var_20(ln(o_t / c_{t−1})), σc² = var_20(ln(c/o)) (ddof 1), σrs² = mean_20 of the RS term; k = 0.34 / (1.34 + 21/19) |
| A3.04a | GARCH | GARCH(1,1) one-step forecast σ_{t+1} (known at t) |
| A3.04b | GJR | GJR-GARCH(1,1) one-step forecast |
| A3.04c | EGARCH | EGARCH(1,1) one-step forecast |
| A3.08a | VoV20 | std_20 of ln(RV20) |
| A3.08c | Kurt50 | pandas rolling(50) kurtosis of r |
| A4.08 | VPIN50 | Σ_50 abs(2 tb − v) / Σ_50 v, with the **real** taker-buy volume instead of the bulk-classification approximation |
| A4.09a | Kyle50 | rolling(50) cov(r, x) / var(x), where x = 2 tb − v |
| A4.09b | Amihud20 | mean_20(abs(r) / qv) |
| A4.09c | Roll50 | 2 sqrt(max(0, −cov_50(Δc_t, Δc_{t−1}))) / c |

**The three GARCH models (A3.04):**
- **Fit:** demeaned r; Gaussian maximum likelihood; parameters fitted **only on D-period bars** (completion time < 2024-01-01) of that scale, then filtered forward over all bars.
- **The equations:**
  - GARCH: σ²_{t+1} = ω + α ε_t² + β σ²_t.
  - GJR: adds γ ε_t² 1[ε_t < 0].
  - EGARCH: ln σ²_{t+1} = ω + β ln σ²_t + α(|z_t| − sqrt(2/π)) + γ z_t.
- **Constraints:** ω > 0, α ≥ 0, β ∈ [0, 1), α + β (+ γ/2) < 1; EGARCH |β| < 1.
- **Start:** σ²_0 = the D sample variance.
- **Optimiser:** scipy L-BFGS-B (SLSQP for the stationarity constraint), fixed start values.
- The fitted parameters are logged.

## 4. Directional A3 rules (8 rules × follow / fade)

| ID | Rule | follow signal |
|---|---|---|
| A3.01x | ATR expansion | TR_t > 2 × ATR14_{t−1} → sign(c_t − o_t), else 0 |
| A3.05 | Squeeze release | "in squeeze" = BB(20, 2, ddof 0) inside the Keltner channel SMA20 ± 1.5 × ATR20 (upper below upper, lower above lower). Release = in squeeze at t − 1 and not at t → sign(c_t − SMA20_t), else 0 |
| A3.06a | NR7 breakout | bar t − 1 has the smallest range h − l of bars t − 7 … t − 1; then c_t > h_{t−1} → +1, c_t < l_{t−1} → −1, else 0 |
| A3.06b | NR4 breakout | the same with 4 bars |
| A3.06c | Inside-bar breakout | h_{t−1} < h_{t−2} and l_{t−1} > l_{t−2}; then c_t > h_{t−1} → +1, c_t < l_{t−1} → −1 |
| A3.07 | Williams volatility breakout | c_t > o_t + 0.5 (h_{t−1} − l_{t−1}) → +1; c_t < o_t − 0.5 (h_{t−1} − l_{t−1}) → −1 |
| A3.08b | Realized skewness | pandas rolling(50) skew of r: > 0.5 → −1, < −0.5 → +1. This is the standard reading (high skew → lower returns), named "fade"; follow is its negative |
| A3.09 | Jump | BV_t = (π/2) × mean of abs(r_i) abs(r_{i−1}) over i = t − 50 … t − 1; abs(r_t) > 4 sqrt(BV_t) → sign(r_t) (follow), else 0 |

## 5. Directional A4 rules (13 rules × follow / fade)

Here mfm = ((c − l) − (h − c)) / (h − l), and 0 when h = l. Cumulative series start at the first bar of the data.

| ID | Rule | follow signal |
|---|---|---|
| A4.01a | OBV | OBV = cumsum(sign(Δc) v); OBV > EMA20(OBV) → +1, else −1 |
| A4.01b | Chaikin oscillator | ADL = cumsum(mfm v); EMA3(ADL) − EMA10(ADL): sign |
| A4.01c | CMF20 | Σ_20(mfm v) / Σ_20 v > 0.05 → +1, < −0.05 → −1, else 0 |
| A4.02a | VPT | VPT = cumsum(v × pct_change(c)); VPT > EMA20(VPT) → +1, else −1 |
| A4.02b | Ease of Movement | emv = (Δ((h + l) / 2)) (h − l) / v; SMA14(emv): sign |
| A4.02c | Klinger | trend = +1 if (h + l + c) rises, else −1; dm = h − l; cm = cm_{t−1} + dm_t if the trend is unchanged, else dm_{t−1} + dm_t; vf = v abs(2 dm / cm − 1) trend; KO = EMA34(vf) − EMA55(vf); KO > EMA13(KO) → +1, else −1 |
| A4.03a | NVI | starts at 1000; changes by pct_change(c) only when v_t < v_{t−1}; NVI > EMA255(NVI) → +1, else −1 |
| A4.03b | PVI | the same, on v_t > v_{t−1} |
| A4.04a | CVD state | cvd20 = Σ_20(2 tb − v) / Σ_20 v: sign |
| A4.04b | CVD extreme | zs(cvd20) > 2 → +1, < −2 → −1, else 0 |
| A4.05 | Trade intensity | zs(nt) > 2 → sign(c_t − o_t), else 0 |
| A4.06 | Relative volume | v_t / SMA20(v)_{t−1} > 2 → sign(c_t − o_t), else 0 |
| A4.07 | Volume profile | profile of the last 100 bars (including t): 50 equal bins between their lowest low and highest high; each bar's v goes to the bin of (h + l + c)/3. POC = the fullest bin (lowest index on ties). The value area grows from the POC, each step adding the fuller of the two neighbouring bins (the upper one on ties, a lone side when the other is exhausted), until it holds ≥ 70% of the volume. VAH / VAL = the upper / lower edge of the area. c_t > VAH → +1, c_t < VAL → −1 (breakout reading = follow; fade = return to value) |

## 6. A4.10 information-driven bars (built from 5m bars, no scale; 3 rules × follow / fade)

Thresholds are set per UTC day from the **prior 30 complete days** only. No bar forms in the first 30 days (signal 0).
- **Volume bars:** cumulative v of 5m bars; the bar closes at the 5m bar where the sum reaches θ = (mean daily v of the prior 30 days) / 48; the sum then resets to 0.
- **Dollar bars:** the same with qv.
- **Imbalance bars:** cumulative signed volume s = Σ(2 tb − v); the bar closes when abs(s) ≥ θ_i = 2 × (mean over the prior 30 days of the absolute hourly signed volume, by UTC clock hour); s resets to 0.

**Signals:**
- Volume and dollar bars: TS20 on the bar closes, i.e. sign(close of bar k − close of bar k − 20).
- Imbalance bars: the sign of the last bar's imbalance s.
- The value is set at the 5m bar where the info-bar closes (known at its close) and is carried forward to the next info-bar.
- NaN 5m bars (exchange gaps) add nothing.

## 7. Configurations

- Regime: 16 × 4 = 64 per scale. A3 directional: 8 × 2 = 16. A4 directional: 13 × 2 = 26. Per scale 106; × 3 scales = **318**. Info-bars: **6**.
- **Total: 324 signal configurations × 3 exits = 972 primary configurations.**
- DSR N = 1,726 + 972 = **2,698**.

**Names:**
- `{ID}_{Measure}_{LOW|HIGH}_{follow|fade}_{scale}` for regime rules;
- `{ID}_{Rule}_{follow|fade}_{scale}` for the other scale rules;
- `A4.10_{Volume|Dollar|Imbalance}Bars_{follow|fade}` for the info bars.

## 8. Out of scope (stated now)

- **A4.11 order-book imbalance:** history exists only from 2023, so it cannot run on the 2020–2026 bench. It was tested in NP1 under its own protocol.
- **A4.12 aggTrades:** its aggressor volume aggregated to 5m is exactly the taker-buy volume already used in A4.04, A4.08 and A4.09.

## 9. Execution changes that do not change any number

- **Gate phase:** the gate phase (random control, bootstrap CI, DSR per configuration) runs in 3 worker processes, calling the same `fast_control`, `boot_ci` and `dsr`. Each configuration's seeds are fixed (0–199 for the control, 7 for the bootstrap), so the order of execution cannot change a number.
- **Progress:** the gate phase writes a progress line every 25 configurations.

## 10. Pre-run check (before any metric)

**Lookahead test.** For 20 random cutoffs in 2021–2026, the signals are recomputed on data truncated at the cutoff (GARCH parameters from D are fixed). Every signal value at bars before the cutoff must equal the full-data value. Any difference stops the run.

## 11. Verifier (`src/audits/verify_methods_batch2.py`, own code)

- **W1:** input manifest SHAs; protocol lock.
- **W2:** 300 random (bar, rule, scale) signal values recomputed with plain-loop code, including its own scale aggregation and carry. The rules covered:
  - NR7;
  - Williams VB;
  - squeeze release;
  - Parkinson LOW;
  - RV20 HIGH;
  - CVD state;
  - relative volume;
  - OBV;
  - NVI;
  - jump;
  - volume profile;
  - dollar-bar TS20.
  - A value whose own computed margin from the decision threshold is below 1e-9 (relative) is listed as "boundary" and not counted as a mismatch.
- **W3:** X3 reversal trades of 5 random configurations replayed by a loop.
- **W4:** daily → monthly → yearly for 5 configurations × 3 exits × 2 costs × 4 periods; every calendar day present.
- **W5:** the ranking order recomputed from the 8 measures.
- **W6:** the random control, by its own sequential loop, for one X1, one X2 and one X3 configuration.
- **W7:** R-stress and R-delay H means of 3 configurations recomputed.
- **W8:** the lookahead test repeated on 5 new random cutoffs.

## 12. Report

- **Hindi report** `RESEARCH_METHODS_BENCH_BATCH2_<date>.md`. It gives:
  - the ranking;
  - the top 20 with monthly and yearly tables;
  - the family summary (A3 regime, A3 events, A4 flow, A4.10);
  - the comparison with Batch 1.
- The edge label is reported as defined, together with the §1 caveat.
