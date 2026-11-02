# ATLAS-TF-2026-10-28: every verified study since project start, arranged by timeframe and ranked (pre-registered)

Written 2026-10-28, before any atlas number is extracted. No study is re-run. No backtest, fit or parameter choice is made. The atlas only **reads stored result files** of locked studies and arranges, ratios and ranks them.

## 1. Question (user, 2026-10-28)
For each timeframe (5m, 15m, 1h, 4h, 1d, 1w, 1M, …), which formula / method fits, and by how much? Direction, entry and exit are ranked separately, from all R&D since the start of the project.

## 2. Inclusion rule (fixed now)
A study is a source only if all of the following hold:
- its folder in `logs/` holds a locked protocol (a `*PROTOCOL*` file plus a SHA file);
- its numbers come from a pipeline-written result file (CSV, JSON or claims), not from report prose.

Its verifier evidence is recorded as one of:
- **STORED:** the verifier output is in the folder;
- **AUDIT16:** re-run in `logs/audit_full_16oct`;
- **REPORT:** PASS is stated only in the study report.

Each row of the atlas carries this flag.

**Excluded, with the reason in `study_inventory.csv`:**
- operations, download, live, paper and forward folders (forward data is too young, and is tracked in `CONSOLIDATED_ACTION_PLAN_28_OCT_2026.md`);
- folders without a protocol (old pre-rebuild system, `swing_study_1d`, `strategy_1d_step6_4_survivorship`, `strategy_1d_step7_ai`, whose protocol is not in `logs/`);
- `research_gemini_review` (an external, untrusted notebook);
- stopped runs (`strategy_1d_step11_ai`);
- pure registries or feature stores (`r2_4h_a0`, `r2_4h_a2`);
- `performance_summary` (a summary of other backtests; it would double-count).
- `archive/` is never read.

## 3. Timeframe (TF) bucket of a row
- **TF** = the decision / signal bar of the method. Buckets: `1s-1m`, `5m`, `15m`, `30m`, `1h`, `4h`, `8h`, `12h`, `1d`, `3d`, `1w`, `1M`, plus `event` (Renko, volume, dollar or imbalance bars: no clock) and `intraday-turn` (TURN T0–T2, defined by turn size θ, not by a bar).
- **Horizon- or lookback-defined studies** map to the nearest bucket:
  - 5m-bar counts: 12 → 1h, 48 → 4h, 288 → 1d, 864 → 3d, 2016 → 1w;
  - NP 24h → 1d;
  - BTC-entry F7 (σ24) → 1d; F11 (8h funding) → 8h; F12 (30-min decisions) → 30m;
  - micro-momentum → `1s-1m`.
- **Baselines** (always long / short, random) are not ranked. They are shown as the physics layer.

## 4. Components
| Code | Meaning |
|---|---|
| **DIR** | Rules that decide the side (and their own timing). Entry-exit rule grids belong here |
| **ENTRY** | When or how to enter, given a direction (triggers, confirmation lag, probes, maker fills, early-turn features, S/R touches) |
| **EXIT** | Exit method comparisons (barrier vs reversal vs time, stops, profit lock, exit brain, exit grids) |
| **SELECT** | Which coin, relative to the others (cross-sectional AI and ranks) |
| **RISK** | Drawdown control and sizing |
| **PHYS** | Market facts per TF (move vs fee, random entry, persistence). Never ranked; it is the yardstick |

## 5. Standard fields
All in fractions per trade unless named `_pct`.
- **`gross`:** mean return per trade before trading cost.
  - If a file gives only net and a fixed cost c, then gross = net + c. Funding stays inside, as in that study; this is noted on the row.
- **`cost`:** that study's own round-trip cost.
- **`FCR` (fee-coverage ratio)** = gross / cost: the share of the fee the method's average move pays. 100% = break-even before funding.
- **`FCR092`** = gross / 0.00092, the `deploy/fees.json` futures-taker round trip. It makes BTC/major-coin studies comparable. For alt-coin AI studies the true cost is higher, so `FCR` is the honest one there.
- **`hit` and `p_star`:** the hit rate and the break-even hit rate where a study gives them.
  - **`ACC_COVER`** = (hit − 0.5) / (p_star − 0.5), only when p_star is the symmetric-payoff break-even of that study (root cause R3, oracle C2, TURN T1).
- **`auc` / `auc_lo`:** skill and its lower CI bound (Bonferroni where the study used it).
- **`role` of the period a number comes from:**
  - **SEL:** used to choose the rule;
  - **OOS:** not used to choose: validation, holdout, unseen coins, pre-2020, or HOLD;
  - **UNFIT:** a standard-parameter grid with no fitting, all periods;
  - **P3:** 2025-10 … 2026-09, report-only.
- **`ctrl`:** whether the row beats its own random / shuffled / sign-null control (True / False / NA), as the study defined it.

## 6. Evidence tier (mechanical; the verifier recomputes it from the fields)
| Tier | Rule |
|---|---|
| **E1** | Study verdict PASS / adopted, **and** OOS net > 0 with OOS CI-low > 0, **and** ctrl True, **and** every OOS / P3 period reported for that row is net > 0 |
| **E2** | Not E1, and net > 0 on a period with role OOS (or UNFIT with month-block CI-low > 0) |
| **E3** | Not E1/E2, and a statistically real effect: auc_lo > 0.5, or ctrl True, or an IC / null test passed at the study's own level |
| **E4** | Not E1–E3, and net > 0 only on SEL data (hypothesis) |
| **E5** | Everything else: no skill vs control, and net ≤ 0 |

## 7. Ranking (inside each TF × component)
1. **Tier** E1 → E5.
2. **Inside a tier:**
   - trade rows by OOS `FCR092` (or `FCR` when a study's cost is not 0.00092);
   - skill rows by `auc_lo`;
   - accuracy rows by `ACC_COVER`;
   - portfolio rows by OOS Calmar.

   Rows of different metric types are listed in separate sub-tables, never sorted against each other.
3. **Ties:** larger n first.

## 8. Chance check (multiple testing)
For each grid study and TF, report:
- the share of rows with OOS net > 0;
- the best FCR092;
- the number of configs.

A grid where the share is near or below what pure noise gives is read as "no edge", even if its best row looks good.

## 9. Derived aggregates allowed (all recomputed by the verifier)
- **Bench exit comparison:** per TF, the mean H gross of X1, X2 and X3 over the same signal set.
- **TFX:** long and short rows are kept separate.
- **PHYS per TF:** E|r|, p* (fee map), random-entry net (root cause R2), P(G|G) (green candle), VR / AC1 (TURN T4), and the realizable follow of confirmed swings (swing anatomy).

## 10. Verifier (`src/audits/verify_tf_atlas.py`, written after this lock, stdlib + pandas only, no import of the builder)
- **V1:** every source file's SHA equals `atlas_sources.csv`.
- **V2:** for every atlas row, the raw value(s) are re-read from the source file and locator, independently, and gross / FCR / FCR092 / ACC_COVER are recomputed (1e-9).
- **V3:** every tier is recomputed from the row fields (§6).
- **V4:** ranks are recomputed (§7).
- **V5:** chance-check table recomputed (§8).
- **V6:** every claim number in the Hindi report is found in `atlas_rows.csv` or `atlas_chance.csv` (claims file).
- **V7:** coverage: every included study in `study_inventory.csv` has at least one atlas row.
- **Mutation test:** one wrong value and one wrong tier must make the verifier fail.

## 11. Output
- **Data files:** `atlas_rows.csv` (all rows), `atlas_ranked.csv`, `atlas_chance.csv`, `atlas_phys.csv`, `atlas_sources.csv`.
- **Hindi report:** `TF_ATLAS_RANKING_28_OCT_2026.md` in the project root, with per-TF sections listing DIR / ENTRY / EXIT / SELECT / RISK rankings.
- **Evidence:** `claims.json`, `verify_output.txt` and `REPORT_SHA256.txt`.

## 12. Honesty rules
- **Same data, many studies.** Many studies re-use 2020–2026 BTC or the same coins. A row's OOS role is only what its own study declared. The report says plainly that the 2025–26 holdout has been opened several times.
- **No forced winner.** If no row in a TF reaches E1/E2, the report says so. Nothing is promoted.
