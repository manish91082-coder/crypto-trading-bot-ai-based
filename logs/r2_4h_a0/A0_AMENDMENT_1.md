# A0 amendment 1 (2026-10-19): a look-ahead in the A0 §5 feature list, fixed before any A2/A3 result

This amends `A0_4H_PROTOCOL_PREREGISTERED.md` (`4d49d411…`). It is locked with SHA256 before any A2 feature table or A3 model exists. Up to this point only A1 had run, and A1 uses no feature.

## What was found (ground-level check by reading the code, then measured on the data)
- **How `legs_all` dates a leg.** In `legs_all.parquet`, a leg's `confirm_time` is the confirmation of its START pivot (`swing_anatomy_phase1.legs_for`: `confirm_i = a_["confirm_idx"]`, where `a_` is the start pivot). The leg's END pivot comes later.
- **What A0 §5 took.** It listed "`move_atr`, `bars`, `done_share_at_confirm` of the confirming leg". The confirming leg is leg j+1, whose `confirm_time` = the signal's known_time. All three depend on the END of leg j+1.
- **Measured** on 4h, K = 3, 7,419 legs: the confirming leg's end lies **after** the known_time in **73.0%** of cases (median 28 h later). The completed leg j, which ends at the signal pivot, ends ≤ the known_time in **100%** of cases.
- **Conclusion.** Those three features are look-ahead. The `c_*` columns of the confirming leg are taken at its `confirm_i` bar, the bar of the known time, and are not affected. Their causality is still re-tested empirically by the A2 replay.
- **Earlier work.** Swing AI Phase 2 used only `c_*` features plus `tf_code` (`swing_ai_phase2.py` FEATS), so no earlier result is affected.

## Amended A0 §5 feature list (replaces the leg part of §5; everything else in §5 is unchanged)
- **Signal-time leg:** the confirming leg = the leg whose `confirm_time` is the latest one ≤ the signal's available_at.
  - For S-LAD and S-DTB this is exactly leg j+1 (`confirm_time` = known_time).
  - For S-BRK and S-TRD it is an as-of (backward) join on the signal bar's close.
- **From it:** all `c_*` columns.
- **From the last COMPLETED leg** (leg j, the leg before the confirming leg; it ends at the latest known pivot): `move_atr`, `bars`.
- **Removed:** `done_share_at_confirm` (it has no completed-leg equivalent that is known in time).
- **Added `signal_type`** (S-LAD, S-BRK, S-TRD, S-DTB) as a categorical feature. A0 §5 omitted it. A pooled model across 4 signal kinds needs it, and it is known at signal time.
- **Unchanged:** the side, the ladder step count k, the retracement of the last pullback, the d−1 daily futures metrics, and the last funding rate.

## Consequence for A2
The A2 replay test must confirm all of this by rebuilding the legs from bars truncated at available_at. Any feature with a replay mismatch on ≥ 1% of sampled rows is dropped before A3, and the drop is recorded.
