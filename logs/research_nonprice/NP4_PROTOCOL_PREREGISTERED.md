# NP4: the 24 h premium-index signal (PREM_Z) on the sealed holdout, run once. Locked 2026-10-26

## Background
- **The user asked (2026-10-26):** "24 घंटे वाला premium संकेत bhi karo test".
- **What is known so far:**
  - In NP1, PREM_Z at 24 h was S1-significant in D (t_IC −4.13) and confirmed in V (−2.31).
  - Its NP1 S2 rule had net +0.157% per trade in D (t 1.06) and +0.139% in V (t 0.60), and failed the S2 gate.
  - In D and V, the long side was stronger (+0.337% and +0.495% per trade) than the short side (−0.012% and −0.199%).
- **H** (2025-01-01 … 2026-09-30) has not been read by any stage (NP1 / NP2 / NP3 checks N5 / P5 / Q4). This run spends it, once, on the configs below.
- **Code:** main `src/research/nonprice_np4.py`; verifier `src/audits/verify_nonprice_np4.py`, independent.
- **Input:** `np1_features_1h.parquet`. PREM_Z there is past-only: it is the z of PREM_1H against the trailing 720 hourly values; NP1 verifier N1 / N1b.

## Configs (fixed now)

**Common to both**
- Decisions at 00:00 UTC every day.
- p = the percentile of PREM_Z among the 00:00 values of [t − 90 d, t). Past only, as in NP1 S2; ≥ 30 past values are needed.
- Hold 24 h: entry at close(t), exit at close(t + 24 h), futures price.
- Cost: taker 0.092% per round trip, from `fees.json`.

| Id | Rule | Note |
|---|---|---|
| **P1** | p ≥ 0.8 → short; p ≤ 0.2 → long | The exact NP1 S2 rule |
| **P2** | p ≤ 0.2 → long only | **Post-hoc variant:** chosen after seeing the D / V long / short asymmetry. It is flagged as such and counts in the multiple-test correction |

**Information row (no gate):** P2 at the spot cost (0.17% per round trip), using the futures return as a proxy for spot.

## Gate on H (each config; z = 2.24 is Bonferroni for 2 configs)
1. mean net per trade > 0, and the weekly-cluster lower bound at z = 2.24 is > 0;
2. ≥ 13 of the 21 H months have a positive sum. A month without a trade is not positive;
3. the 2025 sum > 0 and the 2026-01 … 09 sum > 0.

## Power, stated before the run
- **Expected trades:** about 255 for P1 and about 128 for P2, with a trade sd of about 3.1%.
- **What it takes to pass gate 1:** a P2 mean above about 0.6% per trade.
- **So even if P2's true mean were the D / V level (+0.3 … +0.5%),** it would probably fail gate 1.
- **How the result will be read:**
  - a pass = evidence;
  - a fail with a positive mean = "not proven; more forward data needed";
  - a fail with a negative mean = "the D / V result did not hold".

## Outputs (`logs/research_nonprice/`)

| File | Contents |
|---|---|
| `np4_trades.csv` | every H trade |
| `np4_daily.csv` | every H day × config, with zeros |
| `np4_monthly.csv` | the monthly table |
| `np4_summary.csv` | the summary and the gate results |
| `NP4_OUTPUT_SHA256.txt` | output SHAs |

## Verifier
1. Recompute the percentiles, every trade, and the daily / monthly / yearly sums and gates with plain loops.
2. Check the cost source.
