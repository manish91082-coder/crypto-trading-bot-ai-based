# Step 28: volatility → position size for the M_AI3 portfolio (pre-registered)

Locked before any result is computed. Code: `src/pipeline_1d/step28_vol_sizing.py`. Verifier: `src/audits/verify_step28_claims.py`.
No trading, no deploy, no GitHub.

## Question
- The M_AI3 50 % setup still had a 49 % drawdown (2021–26) and lost 35 % in 2018–19.
- Volatility is predictable: the next-period volatility correlates +0.23 to +0.41 with the past one (5m–1d), while direction does not.
- Does sizing by recent volatility (less money in stormy times, more in calm times) give a better risk/return than the same average exposure held fixed?
- Literature basis: Moreira & Muir (2017), "Volatility-Managed Portfolios", Journal of Finance; Harvey et al. (2018), "The Impact of Volatility Targeting", Journal of Portfolio Management. Not assumed true for crypto; tested here.

## Data (already verified, read only)
- `logs/strategy_1d_step27_combine/sleeves_{MAIN,PRE}_f100.csv`: daily equity of D1, H4 and H1 at 100 % invested, with 0.25 % fills (Step 27 G0 PASS).
- **Mix return:** r_t = M_t / M_{t−1} − 1, where M = the mean of the three sleeves.
  - MAIN = 2021-01-01..2026-09-30.
  - PRE = 2018-02-01..2019-12-31 (the frozen brains; never used for design).

## Rule (PRIMARY, fixed)
**Volatility estimate.** σ_{t−1} = standard deviation of the last 20 daily mix returns up to t−1.

**Scale.** k_t = 0.5 × the median of all σ values known up to t−1.
- This is causal and needs ≥ 60 σ values.
- Before that, w = 0.5.
- In PRE, the median also starts from the PRE data only, which is causal.

**Target weight.** w*_t = clip(k_t / σ_{t−1}, 0, 1). This is the share of capital invested on day t.

**No-trade band.**
- The held weight changes to w*_t only if |w*_t − w_{t−1}| > 0.10; otherwise w_t = w_{t−1}.
- When it changes, the cost is |Δw| × 0.25 % of equity.

**Equity.** E_t = E_{t−1} × (1 + w_t × r_t) − cost_t.

**Approximation stated now.**
- This scales the 100 % sleeve returns. It does not re-run the position-level simulators with a daily changing exposure.
- The approximation error is measured: FIXED 0.5 with this method vs the real Step 27 f = 0.5 runs ($53,883.75 MAIN; $6,546.09 PRE). It is reported.

## Comparators (same method and costs)
- **FIXED_050:** w = 0.5 every day.
- **FIXED_MEAN:** w = the mean of the VOL strategy's daily w in that period. This is the same average exposure, computed after the fact for fairness only.
- **SHUFFLED:** 1,000 random permutations (seed 28) of the VOL strategy's w series over the days of the period.
  - Same weights, random timing.
  - The same band and cost rule.

## Gates (all must hold in BOTH periods → PASS)
**MAIN:**
- G1: Calmar(VOL) > Calmar(FIXED_MEAN) and > Calmar(FIXED_050).
- G2: MaxDD(VOL) < MaxDD(FIXED_MEAN).
- G3: Calmar(VOL) > the 95th percentile of SHUFFLED Calmar.

**PRE** (a losing period, where Calmar is negative and not meaningful):
- G1: final(VOL) > final(FIXED_MEAN) and > final(FIXED_050).
- G2: MaxDD(VOL) < MaxDD(FIXED_MEAN).
- G3: final(VOL) > the 95th percentile of SHUFFLED finals.

**Decision:**
- PASS → VOL sizing becomes a shadow line in the forward log (only after the user agrees). The 50 % paper portfolio stays the primary forward test.
- FAIL → reported, and nothing changes.

## Report-only (no gates, so no fishing)
- Windows of 10 and 60 days; bands 0 and 0.05.
- The same rule on the BTC sleeve.
- Per-year returns.
- Average and minimum/maximum w.
