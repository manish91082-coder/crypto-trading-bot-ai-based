# ATLAS-TF code notes (written during the build, after the protocol lock 2026-10-28 06:50 UTC)

The protocol (`ATLAS_PROTOCOL_PREREGISTERED.md`, 92683aad…) is unchanged. These notes record build bugs and clarifications made while extracting. **No result of any study was re-run or changed.** Each clarification is conservative: it can only stop a row from looking better than its study showed. None can raise a row to E1/E2 that the study did not support.

1. **TURN T1: no `ACC_COVER`.**
   - §5 listed TURN T1 among the symmetric-payoff studies by mistake. T1's trade is asymmetric: enter at the bounce, target = turn completion, stop = new extreme, so break-even p* = f + c/θ.
   - Its hit and p* are shown, but `ACC_COVER` is left empty.
2. **UNFIT rows with net > 0 but no month-block CI → E4, not E5.**
   - Several unfitted grids (ladder probe, A1 at the trade level, ladder sessions) have no month-block CI.
   - Read literally, §6 sent their positive rows to E5 ("net ≤ 0"), which states a falsehood.
   - E4 ("positive, unproven") is the honest reading. Such rows still cannot reach E2 without the month-block CI.
3. **Modifier rows.** A risk, entry or exit change applied to an existing system is measured by what its study tested: the change against its own base.
   - **What `net` means here:**
     - the Calmar change (method − base) on the row's period;
     - `dcagr` keeps the CAGR change;
     - the study's own verdict is shown next to it.
   - **Rows:** R1 E1a / E1b / E2 / E3 / E4 / N1a / N1b / E11 (base F7 RS), Step 28 vol sizing (base fixed 50%), F7 (base F2 LS), N2 R1 / N3 X1 / N3 X2 / T20 / ECO-T4 (base N1, period P3), master-audit loss rule L1 (base G1).
   - **Spot timing S1–S6:** `net` = Sharpe(rule) − Sharpe(BTC hold), the study's own G1 yardstick. Otherwise a long-only rule in a bull holdout looks "positive" without beating holding.
4. **Honest period roles.**
   - ECO-W2, "1D alone" and "N1 alone" were chosen on dev 2021-01..2025-09. Their OOS number is P3 (report-only), with dev as `net_sel`.
   - N1's OOS number is its pre-declared 2018-19 gate (G7), with P3 as x1.
   - A first draft had used dev as OOS; this was corrected before any report text.
5. **Missing unseen periods.**
   - Review found that the R24 1h portfolio had been promoted to E1 because its row lacked the 2018-19 result of the same sleeve.
   - Step 27's decision table holds that result: H1 2018-19 CAGR −48.28%, H4 −50.76%, D1 −42.93%. It is now x1 for the 4H and 1h portfolio rows, and three Step 27 rows were added.
   - After this fix **no row is E1**.
   - The F2 row had listed its 2025 / 2026 calendar returns as extra OOS. They are inside its own test window, so they were removed.
6. **Bug (fixed before any reading).** The BTC-entry filter `startswith("F1")` also dropped F11 (funding) and F12 (AI): 30 configs. It now compares the family token exactly. Rows: 924 → 954.
7. **TF names** are normalised: 1D → 1d, 1W → 1w, TFX 1m → `1s-1m`.
8. **Chance table addition:** `share_oos_gross_pos`, the share of a grid's OOS configs whose mean **gross** (before fee) is > 0. Under "no directional information" it is about 50%. It is added because §8's net share alone mixes skill with fee size.
9. **R units.** Rows in R units (ladder probe, A1, A4 maker) get FCR = gross_R / cost_R. `FCR092` is not defined for them.
10. **PORT rows.**
    - Where a study gives a per-trade CI (`trade_ci_low_pct`), it is used as `ci_lo`. Otherwise `ci_lo` is empty, so such rows cannot be E1.
    - For N-series rows the claims hold Calmar only, so the Calmar difference is used (note 3).
11. **TFX `gmed`.** The median gross per trade (`gross_median`, a TFX file column) is carried for display. Trend-long cells have a high mean but a negative median, so the mean alone misleads. It is not used in tiers.
12. **Coverage additions (before any report text).**
    - V7 found 6 included studies without rows: manual_day_study, research_sr_volume, research_swing_vs_sr, research_swing_anatomy, research_s2_bear_training, research_s3_futures_features. Adapters were added: `a_extra`.
    - Swing anatomy and the fee map appear in the physics table only, per §4 / §9. Physics rows carry their study name for V7.
13. **Report numbers.**
    - `src/research/tf_atlas_tables.py` and `tf_atlas_report.py` write every table cell and narrative number from the atlas files, together with a claim (881 claims). Verifier V6 re-reads each claim value and checks that its text is in the report.
    - Hand-written ranges (grid shares, best fee-coverage, inventory counts) are also claims: kinds `chance_agg`, `inventory` and `sources`.
14. **Mutation test** (`mutation_test_output.txt`): one raw value changed (R24 portfolio net 0.6869 → 0.9999) and one tier changed (spot DCA E5 → E2). The verifier failed V2a, V3 and V6, with exit 1. The file was then restored from its backup, and the final run passed 10/10.
