# S3: do futures features (funding + basis) add to the relative brains R6, R24, D1? (pre-registered)

Locked before any S3 model is trained. Code: `src/pipeline_1d/s3_futures_features.py`. Verifier: `src/audits/verify_s3_claims.py`.
Futures data is INFORMATION only; no futures trading. No GitHub.

## Why
- Chi, Hao, Hu & Ran (Journal of Futures Markets 43(8), 2023): in 2017–21 the BASIS was the strongest predictor of cross-sectional crypto futures returns, stronger at daily than at weekly frequency.
- Our relative brains never had futures inputs. Step 10 tested them only in the failed absolute brain.

## Data
- F1 files (`data/futures_um`): USD-M perpetual 1h closes and funding rates, SHA256-checked, 132 coins passing the scale gate.
- Spot 1h closes from `data/universe_all/1h`.
- Open interest and long/short ratios are NOT used: they exist for only 30 coins. A coverage-limited feature would mostly be missing in the 2024–26 universe.

## Added features (6, fixed; all known at the close of the row's bar, t_end)
| Feature | Definition |
|---|---|
| basis_now | perp close / spot close − 1, on the hour bar that ends at t_end |
| basis_7d | mean of the hourly basis over the last 168 hours (≥ 48 hours present) |
| fund_24h | sum of funding rates with event time in (t_end − 24h, t_end] |
| fund_7d | the same over 7 days |
| xr_basis_now, xr_fund_24h | cross-sectional percentile rank among the rows of the same bar (the research xr rule) |

- NaN where the coin has no perpetual (or fails the scale gate) at that time. HGB handles NaN.
- **D1:** the bar is the day, so t_end = the next 00:00.

## Design
- As Steps 25 / 29 / S2: the same test rows, labels, walk-forward, recipe and research portfolio rule (100 %, 0.25 %). Only the features are added.
- The baseline is the stored research prediction on identical rows.
- **Order:** R6, then R24, then D1, run one by one.
- **No 2018–19 exam is possible:** USD-M perpetuals did not exist for these coins. This weakness is stated now.

## Gates per brain
| Gate | Condition |
|---|---|
| G0 | Test rows identical to the research rows, AND basis_now coverage of the test rows ≥ 50 % |
| G1 | Paired AUC difference (new − base), month-block CI: CI low > 0 |
| G2 | Calmar(new) > Calmar(base) AND final(new) > final(base). This money gate exists because Steps 25 and 29 raised AUC but lowered money |
| G3 | AUC difference > 0 in at least 4 of the 6 years 2021..2026 (each year computed separately) |

**Decision:**
- PASS, if G0, G1, G2 and G3 all hold;
- SKILL_ADD_ONLY, if only G0 and G1 hold;
- FAIL otherwise. INVALID if G0 fails.
