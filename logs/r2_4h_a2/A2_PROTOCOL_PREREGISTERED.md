# A2: knowledge store, replay test and leak canary (sub-protocol of A0 `4d49d411…` + amendment 1 `b89f0a82…`), pre-registered 2026-10-19

This protocol is locked before any feature table is built. It only narrows A0 §8 and amended §5. No model is trained, and no trial is used: A2 is data plumbing and leak control, not a test of skill.

## Rows
- One row per A1 trade in `logs/r2_4h_a1/a1_trades.parquet` (SHA in `claims_a1.json`): all 4 signals × 2 sides, 9,721 rows.
- **Columns copied:** signal, coin, side, entry_time, perp_ok, period, net_base.
- **available_at** = entry_time. This is the open of the entry bar, which equals the close of the signal bar; the known_time of S-LAD/S-DTB equals the entry bar's start.
- **label** = 1 if net_base > 0, else 0.

## Features (A0 §5 as amended; nothing else)
| Id | Feature | Exact definition (all with time ≤ available_at = T) |
|---|---|---|
| F1 | `c_*` (every `c_` column of `legs_all`) | From the confirming leg: tf = 4h, K = 3, same coin, the leg with the largest `confirm_time` ≤ T |
| F2 | `last_leg_move_atr`, `last_leg_bars` | `move_atr` and `bars` of the completed leg: the leg directly before the confirming leg in start_time order. It must have end_time ≤ T; otherwise NaN, and the count is reported |
| F3 | `signal_type` (0..3 = S-LAD, S-BRK, S-TRD, S-DTB), `side` (+1 long, −1 short) | From the row |
| F4 | `ladder_k` | `ladder_sessions.points` over the coin's 4h K = 3 legs; the last point with known_time ≤ T; its state. If UP: the number of H points in the current consecutive UP run up to that point. If DOWN: the number of L points in the DOWN run. Otherwise 0 |
| F5 | `retr_last` | For that last known point p: move(p) / move(p − 1), using the points table's `move`. NaN if the previous move is 0 or missing |
| F6 | `oi_chg1`, `oi_chg7`, `top_ls_acc`, `top_ls_pos`, `global_ls`, `taker_ls_vol` | `data/futures_info/<coin>_metrics_daily.csv`, the row for day d−1 where d = T floored to the UTC day. `oi_chg1` = oi(d−1)/oi(d−2) − 1; `oi_chg7` = oi(d−1)/oi(d−8) − 1. NaN if a row is missing |
| F7 | `funding_last` | `data/futures_um/<coin>_funding.csv`: the last funding_rate with time ≤ T |
| CAN | `canary_next_ret` | **Deliberate leak:** close of bar entry+5 / open of the entry bar − 1. It is stored only for the canary test and never used by A3 |

## Store
- `data/derived/r2_a2/feature_store.parquet`, plus `feature_list.json` (the final feature names after any drops).
- SHA256 of both go in `claims_a2.json`.

## R1: replay test (the core check)
- **Sample:** 200 random rows, seed 20261019, with T ≥ 2020-06-01, so that 200 four-hour bars of history exist.
- **For each sampled row, independently of the store:**
  - **Leg rebuild.** Load the coin's 1h and 1d spliced data (`swing_anatomy_phase1.load_spliced`) and keep only bars whose close ≤ T. Rebuild 4h (agg of 1h), 1W and 1M (agg of 1d) and the native 1D. Run `clip_atr`, the HTF ZigZag states (1M, 1W, 1D), `base_factors`, `sr_nearest`, the 1h VAP input, the BTC 4h context (BTC data truncated at T in the same way) and the FnG table (dates < T's day). Then run `legs_for(coin, "4h", K = 3)` on the truncated data.
  - From the rebuilt legs, take the confirming leg and the completed leg (same rules as F1/F2). Rebuild F4/F5 with `points` on the rebuilt legs.
  - Rebuild F6/F7 from the files filtered to the dates and times allowed at T.
  - Rebuild CAN from bars truncated at T. This must be impossible: there is no bar entry+5, so the value is NaN, which counts as a mismatch.
- **Comparison:** float equality within 1e-9 relative (NaN == NaN), per feature.
- **Pre-registered decisions:**
  - A feature with a mismatch on ≥ 1% of sampled rows (≥ 2 of 200) is DROPPED from `feature_list.json`, and the drop is reported.
  - **The canary must mismatch on ≥ 99% of rows.** Otherwise A2 FAILS: the replay would be blind.

## R2: canary AUC (information only)
- The AUC of `canary_next_ret` alone against the label on the development window. This shows how strong the planted leak is.
- No model is fitted on the real features. That is A3, and A2 fits no model.

## R3: code rules
- The A2 code uses no `.asof(` call (project rule: `df["asof"]`). This is checked by grep.

## Verifier (own code) `src/audits/verify_r2_a2.py`
1. The row count and keys equal the A1 trades; available_at == entry_time; label == (net_base > 0).
2. For 300 random rows, F1, F2, F3, F6 and F7 are recomputed with its own code (direct joins on `legs_all` and the CSVs), and F4/F5 with `points`. They must be equal.
3. The replay CSV shows exactly the reported mismatch counts; the drops are applied in `feature_list.json`; the canary is flagged.
4. The claims and the A0, amendment, A2 protocol and data SHAs match.

## Honest limits
- `c_*` values come from `legs_all`, which was built once on the full history. The replay is exactly the test of whether that matters.
- F6 starts 2020-09. Earlier rows are NaN; HistGradientBoosting handles NaN natively.
