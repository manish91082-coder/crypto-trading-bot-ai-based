# Step 29: do support/resistance + volume-at-price + swing-state features add to the 1h R24 brain? (pre-registered)

Locked before any Step 29 model is trained. Code: `src/pipeline_1d/step29_srv_features.py`. Verifier: `src/audits/verify_step29_claims.py`.
No trading, no deploy, no GitHub.

## Design
- Identical to Step 25: the same R24 rows, labels, walk-forward, recipe, simulator and gates. Only the added features differ.
- The baseline is the stored Step 24 R24_AI prediction on the IDENTICAL rows.

## Added features (6, fixed; all known at the close of the hour bar)
All computed on the coin's own 1h data, with the Phase 1 code (`clip_atr`, `sr_nearest`, `vap_at`, `zz`, `state_lookup`):

| Feature | Definition |
|---|---|
| sup_dist_atr_1h, res_dist_atr_1h | distance from the close to the nearest UNBROKEN k = 3 fractal support below / resistance above, in ATR14 (1h) |
| vap_7d | share of the last 7 days' 1h USDT volume within ±0.25 ATR of the close |
| zz_state_1h, zz_state_4h, zz_state_1D | causal ZigZag (K = 3) state of 1h, 4h and 1D bars (4h and 1D aggregated from the same 1h file), known at the end of the hour |

## Why these and an honest warning
- The S/R, volume and swing studies found:
  - about 2× location overlap of swings with S/R;
  - VAP relates to break / turn behaviour;
  - the next higher timeframe's state adds +0.5 to +0.8 ATR to the swing.
- **Warning stated now:** those studies looked at 2021–26 AND 2018–19 price data. So even a PASS here is only a CANDIDATE. The forward log is the real judge.

## Gates (as in Step 25)
- **G0:**
  - rows identical to Step 24 (main and 2018–19);
  - the missing share of every added feature in the test rows is < 10 %.
- **G2:** paired AUC difference (new − base, month-block CI) has CI low > 0.
- **G3:**
  - a: Calmar > 0.92 (the R24 research value);
  - b: trade CI low > 0;
  - c: CAGR > 0 at 0.40 % cost.
- **G4:** frozen 2018–19 AUC > base 2018–19 AUC, AND CI low > 0.50.
- **Decision:**
  - PASS_SRV_ADDS, if G2 holds and all of G3 and G4 hold;
  - SKILL_ADD_ONLY, if only G2 holds;
  - FAIL_SRV_ADDS_NOTHING, if G2 fails.
