# A0 amendment 2 (2026-10-19): swing signals and swing features from REAL-TIME pivots (hindsight fix), before any A2/A3 result

This amends A0 (`4d49d411…`) and amendment 1 (`b89f0a82…`). It is locked before the corrected A1 run and before any A2 store exists. Up to now no feature table or model exists. A1 results so far are documented, and are corrected below without deleting them.

## What was found (code reading + measured)
- **The pivot source keeps only final pivots.** `swing_study_1d.zigzag_pivots` returns FINAL pivots: when price breaks the pivot that started the current leg without a reversal, that pivot is popped as "failed" (`events[...]["failed"] = True`).
  - `legs_all.parquet`, the ladder study (S5), S6 and A1's S-LAD/S-DTB were all built on this final list.
  - So a pivot that was confirmed in real time and later failed is ABSENT from them. The signals it would have produced live (most likely losers, because the stop sits beyond that pivot) are missing.
- **Measured** on 4h, K = 3, 10 coins, 2017–2026: 7,541 real-time confirmations, of which **102 (1.4%) later failed**. Per coin 0.8%–2.1%.
- **A second effect, found by the A2 replay smoke test.** `legs_for` emits a leg only when its END pivot exists. A replay from data truncated at T therefore cannot see the in-progress leg whose start pivot is already confirmed. This is a replay-construction issue, not a leak. It is handled below.

## Amended rules (replace the swing-signal and swing-feature sources; everything else unchanged)
1. **Real-time pivot timeline (per coin, 4h, K = 3).** Run `zigzag_pivots(..., events)` once on the full clipped 4h bars. Replay its event list in order:
   - a non-flip event pushes a pivot (pivot idx, kind, ref_price, confirm_idx);
   - a flip event pops the last pivot (the failure; failures always pop the last pivot).

   A pivot is known at end_time(confirm bar) = `end_times("4h", ts)[confirm_idx]`.
2. **Labels and state at each confirmation:**
   - label = HH/LH (for an H) or HL/LL (for an L) against the previous same-kind pivot in the CURRENT list;
   - state = UP / DOWN / CONTRACTION / EXPANSION from the labels of the last H and the last L in the current list (`ladder_sessions.state_of`).
3. **S-LAD.**
   - Long: at the confirmation of an L labelled HL while the last H label is HH.
   - Short: at the confirmation of an H labelled LH while the last L label is LL.
   - Entry, ATR (= ATR_14 at confirm_idx), stop (pivot ∓ 0.5 ATR) and exits are unchanged.
4. **S-DTB.** At the confirmation of pivot b:
   - b is within 0.5 × ATR_14[index of the pivot before b in the current list] of the previous same-kind pivot;
   - the label is HL (long) or LH (short).
   - Everything else is unchanged.
5. **A1 is re-run for S-LAD and S-DTB with these signals.** This is a CORRECTION of trials T01 and T04, not new trials; it is recorded in the trial registry as `A1-CORRECTION`. S-BRK and S-TRD are bar-based and unchanged.
   - **Check:** every corrected signal at a pivot that never failed must equal an existing A1 signal, and vice versa. The difference must consist exactly of the signals at later-failed pivots.
6. **A2 swing features come from the same real-time list at T** (the latest pivot whose confirm end_time ≤ T):
   - `c_*` = the `legs_for` factor block evaluated at that pivot's confirm_idx on the full bars (all causal);
   - `last_leg_move_atr`, `last_leg_bars` from the last two pivots in the list (|p₋₁ − p₋₂| / ATR_14[idx₋₂], idx₋₁ − idx₋₂);
   - `ladder_k`, `retr_last` from the list's labels and states.
7. **A2 replay** rebuilds the same quantities from data truncated at T, using the ORIGINAL `legs_for` on the truncated bars. A synthetic final pivot is appended at the last truncated bar, so that the in-progress leg (start pivot confirmed) gets its row. Only the leg's `c_*` (taken at its start pivot's confirm bar) is used from that row.
