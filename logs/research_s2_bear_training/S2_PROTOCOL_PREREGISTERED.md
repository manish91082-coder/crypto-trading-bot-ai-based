# S2: add the 2017–19 bear-market data to the TRAINING of R6, R24 and D1 (pre-registered)

Locked before any S2 model is trained. Code: `src/pipeline_1d/s2_bear_training.py`. Verifier: `src/audits/verify_s2_claims.py`.
No trading, no deploy, no GitHub.

## Why
- All three brains learned only from 2020+ data; the SHA-verified 2017–19 data was used only as an exam.
- Exactly there, in the bear market, the brains were weakest. In 2018–19, with $10k at 100 %: R24 $2,837 and D1 $3,424, vs BTC hold $6,961.

## What changes (one thing only)
- The **training set** of every monthly walk-forward model gets extra rows from 2017-08..2019-12. They are built by the SAME code as the research rows, on `data/universe_pre2020`:
  - **R6 / R24:** `step23/24.build_rows` on the 1h files. Members = top 30 by 30-day USD volume of the reference 30 + half A among the pre-2020 coins (`daily_members`, the research train rule). For R24, the train hours are hr % 3 == 0, as in research.
  - **D1 (R5):** `core_rows_1d.build` on the pre-2020 folders (exactly as Step 22). Rows = reference coins + half-A eligible coins. Label_r5 is relative to the pre-2020 reference median (the research rule). The model is trained with `step13.wf_transfer`, the research recipe.
- **Unchanged:** test months (2021-01..2026-09), test rows, features, labels, recipe (HGB, KW, random_state), simulators, costs.
- The baseline is the stored research prediction on the identical rows: Step 23 R6_AI, Step 24 R24_AI, Step 19 U_AI.

## Price of this step (stated now)
- 2018–19 can no longer serve as an unseen exam for these models.
- From now on the only unseen judge is the forward log.

## Gates per brain
| Gate | Condition |
|---|---|
| G0 | Test rows identical to the stored research rows (symbol, time), in the same order. Pre-2020 training rows > 0 and all dated < 2020-01-01 |
| G1 | Paired AUC difference (new − base), month-block CI (Step 25 `paired_auc_diff`): CI low > 0 |
| G2 | Research portfolio rule at 100 % and 0.25 %: Calmar(new) > Calmar(base) AND the 2022 return (new) > the 2022 return (base) |
| G3 | AUC difference within 2022 alone > 0 (point estimate) |

**Decision per brain:**
- PASS, if G0, G1, G2 and G3 all hold;
- SKILL_ADD_ONLY, if only G0 and G1 hold;
- FAIL otherwise. INVALID if G0 fails.

**Order:** R6 first, then R24, then D1, run one by one.

## Report-only
- The M_AI3-50 % mix rebuilt with the PASSing brains vs the original.
- The F2 long-short with the new brains is done in the plan's later step F3, not here.
