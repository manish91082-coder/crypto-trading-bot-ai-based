# A1: rule-signal edge map on 4h, no AI (sub-protocol of A0 `4d49d411…`), pre-registered 2026-10-19

This sub-protocol only narrows A0 §3–§4. It is locked before any A1 result is computed, and every change after the lock goes into `CODE_CHANGES_AFTER_LOCK.md`.

**Trials:** 4 (S-LAD, S-BRK, S-TRD, S-DTB). Each is written to `logs/r2_4h_a0/trial_registry.csv` before it is run.

## Data
- 4h bars resampled from `data/universe_hf/5m/<coin>_5m_full.csv.gz`, using the same code as S6 (`probe_scalein.bars`).
- The 10 research coins.
- Swing points from `legs_all.parquet` (SHA `bbe7a4fd…`, K = 3, tf = 4h), using `ladder_sessions.points`.
- Real funding from `data/futures_um`.
- **Entries:** from 2020-02-01 to 2026-09-30.
  - **Development window:** 2020-02..2025-09 (P1 + P2).
  - **P3:** reported only.
- **Perp availability:** a trade that enters before the coin's first funding timestamp is excluded, as in the audit.

## Precise signal definitions (the A0 wording, made exact)
- **ATR for S-BRK and S-TRD:** ATR(14) is the simple 14-bar mean of the true range on 4h bars. The value at bar i uses bars ≤ i.
- **S-LAD:** exactly `probe_scalein.signals(legs, coin, "4h")`.
  - Entry is the open of the bar starting at known_time.
  - ATR is the next leg's atr_confirm.
  - The stop is the pivot ∓ 0.5 ATR.
- **S-DTB:** a swing point b of type L whose price is within 0.5 × atr_start(b) of the previous L point a, **and** whose label is HL. This is the "double bottom whose second low is a higher low".
  - Long entry at known_time(b).
  - The mirror case is a short: type H, within 0.5 ATR of the previous H, label LH.
  - ATR and stop are as in S-LAD (the next leg's atr_confirm; pivot ∓ 0.5 ATR).
  - This is the A5 pattern of the ladder study, restricted to the same-direction label.
- **S-BRK:** at the close of bar i, a long if close[i] > max(high[i−20..i−1]), a short if close[i] < min(low[i−20..i−1]).
  - Entry is the open of bar i+1.
  - The stop is entry ∓ 2 × ATR[i].
- **S-TRD:** EMA(50) of the close, with alpha = 2/51 and adjust = False.
  - A long at the close of bar i if close[i−1] ≤ EMA[i−1] and close[i] > EMA[i] and EMA[i] > EMA[i−6].
  - A short is the mirror.
  - Entry is the open of bar i+1; the stop is entry ∓ 2 × ATR[i].
- **One open trade per coin, signal and side:**
  - a new signal is ignored while the previous trade of the same signal, coin and side is still open (entry bar ≤ t ≤ exit bar);
  - S-LAD and S-DTB keep all their signals, as S6 did.

## Exit and costs
**Exit.** The `probe_scalein.simulate` engine, variant V0 only:
- trailing stop = the max of the earlier highs − 3 ATR;
- a gap fill at the open;
- a time stop at bar 59 (60 bars).

**Fees in R.** fee_R = s × (entry_px + exit_px) / R, where s is the per-side cost:

| Scenario | s |
|---|---|
| **base** | **0.00054** |
| 1.5× | 0.00081 |
| 2× | 0.00108 |
| optimistic | 0.00045 |
| no BNB | 0.00059 |

**Real funding R.** Computed exactly as in the master audit B1, over the open interval (entry_time, entry_time + (exit_idx + 1) × 4h).

**Net R** = gross R − fee_R − funding_R.

## Q1 gate (per signal × side, development window, base cost)
- mean gross R ≥ 2 × (mean fee_R + max(mean funding_R, 0)). Funding received is not counted as help;
- **and** mean net R > 0 in P1 **and** in P2.

**Also reported:**
- n; mean, median and p05 net R;
- win rate;
- the bootstrap 95% CI of the mean net R (coin-year blocks, 2,000 draws, seed 20261019);
- every cost scenario; P3.

**Outcome.**
- The signal-sides that pass go to A3.
- If none pass, the A-phase stops with a report (A0 §3).

## Verifier (own code) `src/audits/verify_r2_a1.py`
1. Re-derives the S-BRK and S-TRD signals on 4h bars for 3 coins with its own loop. The signal sets must be equal.
2. Re-simulates 200 random trades (all 4 signals) with its own loop. Gross R must match to 1e-9, and fee and funding R to 1e-9.
3. Recomputes the gate table from the trades file.
4. Checks the claims JSON and the protocol, A0 and data SHAs.
5. The S-LAD trades must reproduce S6's 4h V0 gross R exactly, trade by trade.
