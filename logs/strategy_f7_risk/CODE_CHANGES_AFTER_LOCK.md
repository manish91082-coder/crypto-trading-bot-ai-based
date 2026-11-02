# F7: interpretation notes and changes after the protocol lock

## 1. Gap-liquidation formula (written BEFORE any F7 run; no result seen)
- **Protocol wording:** R1 says "if the bar OPEN ≥ entry × (2 − 0.005), the position is liquidated (gap through the stop, F2 rule, margin lost)".
- **The F2 engine's rule:** after the verified funding fix (F2 CODE_CHANGES), the engine uses the general isolated-margin rule `margin + units × (entry − price) ≤ 0.005 × units × price`. Without funding this is exactly price ≥ entry × (1 + 1)/(1.005) ≈ entry × 1.990. With funding, the margin moves.
- **What the code does:** the F7 code applies that same F2 margin rule to the bar OPEN, so the "F2 rule" named in the protocol is followed.
- **How much it matters:** the difference vs the literal entry × 1.995 is under 0.5 % of price. It only matters for opens between ×1.990 and ×1.995, and both are far above the ×1.50 stop.
- **Recorded before running** so that it cannot be a post-result choice.

## 2. Verifier fixes (after the run; engine, claims and results unchanged)
- **(a) Unpacking error.** `funding_sum` unpacked 3 values from the per-symbol cache after a 4th field (the hour lookup used to speed up the bar re-build) was added. A crash only; fixed.
- **(b) V4 cooldown check counted the stopped trade itself.**
  - D1 ADAUSDT was shorted at the 2025-03-02 open and stopped in the same daily bar (ADA rose > 50 % intraday that day). Its own entry time equals its exit time, so the "re-shorted within 30 days" filter matched the trade itself.
  - The next ADA short is 2025-04-11 (40 days later), so the cooldown held.
  - **Fix:** the check now excludes the stopped trade's own row.
