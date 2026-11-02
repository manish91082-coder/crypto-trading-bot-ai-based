# Round 1: clarifications and changes after the protocol lock
Protocol locked 2026-10-16T08:36:17Z. Every entry below was written BEFORE any Round 1 experiment run; no Round 1 result existed.

## 1. Clarifications of protocol gaps (found while writing the runner)
**(a) E1b control.**
- With w = 1.0 there are no alt shorts, so the "same w, alt shorts from shuffled AI ranks" control is identical to E1b itself.
- G5 is therefore NOT APPLICABLE to E1b. It is reported as "n/a". E1b passes on G1–G4 alone.

**(b) σ60 missing.**
- Some coins in a target set lack 60 daily returns (new coins).
- Their σ is set to the median σ of the other members of that target set that day. If every member is missing, equal weights are used.

**(c) "Worst short-side day" (E1 G4).**
- This is the worst calendar day of the short book's mark-to-market P&L: shorts + BTC hedge, entry fees, funding and the closing value included.
- It is summed over the three sleeves and divided by 3, the same scaling as the mix.
- To measure it, the engine got a per-bar accumulator, `short_pnl` (see 2c).

**(d) E2 control.**
- "Drop the same number of shorts at random" = at each decision, remove from the shortable list as many candidates as the E2 filter removed at that decision (per sleeve), chosen at random.
- The freed slots go to the BTC hedge in the same way.

**(e) N1 "top 20 % of MAX7".**
- A member is blocked when its MAX7 percentile rank among that decision's ranked members (`rank(pct=True)`) is > 0.80.
- The N1 control blocks the same number of members, at random, among the ranked members.

**(f) Shortable base list (E3b / E3c / E2 / N1b).** The hooks receive F7's shortable list (perp bar present + scale gate + cooldown) in AI bottom-first order.

**(g) Decision day.**
- All three sleeves decide at the close of calendar day d (D1: the day bar; H4: the 20:00 bar; H1: the 23:00 bar).
- Daily features (MAX7, σ60, perp age, funding mean, perp quote volume) use data up to and including day d. Funding events count up to the decision time d + 1 day 00:00 UTC.

## 2. Engine facts established by the synthetic tests (`src/audits/test_r1_engine_synthetic.py`, T0–T7 PASS)
**(a) Cash limit.**
- With 50 % long + 50 % short (+ hedge), the last fill of a decision can be limited by cash because of fees. This is the same behaviour as F7.
- The tests use invest_long 0.3 wherever a hand computation needs the full notional.

**(b) 1x isolated perp long.**
- The F7 margin rule mirrored for longs (margin + units × (low − entry) ≤ 0.005 × units × low) can never trigger at 1x while margin = units × entry. It can only trigger if funding payments erode the margin.
- Binance's isolated long liquidation price at 1x is likewise 0. Expect ~0 long liquidations in E11.

**(c) Added after the first synthetic run, before any experiment.**
- `short_pnl` (a per-bar mark-to-market P&L of shorts + hedge) was added to the engine.
- T0 (hooks off == F7, exactly) and G0 (F7 RS / OFF_LO / OFF_LS sleeve finals within $0.01) still hold.
- T7 checks that the per-bar sum equals the realized short + hedge trade P&L.

## 3. More clarifications (still before any run)
**(h) "Short PF / payoff" (E2 G1 and G5).** These use the AI alt-short trades only (side = "short"), as F7's 1.07 / 0.81 did. Hedge trades are reported separately ("hedge").

**(i) Funding for the E2 filter.** It is read from the raw published funding files (every rate). The engine's P&L funding table keeps only events with a known price (the F2 rule), so it is not the source for the filter mean.

**(j) Feature check.** `r1_run.py check` re-derives MAX7, spot σ60, funding mean-9, perp age and 30-day perp quote volume with plain loops for random samples, before any experiment runs.

## 4. Pre-run fixes (still no experiment run)
- **`r1_run.py g0`:** the first G0 run crashed while WRITING its JSON (numpy bool is not JSON-serializable) after the simulations had finished. Fix: cast to `bool`. G0 was re-run.
- **`r1_run.py check`:** PASS. MAX7 and σ60 were re-derived for 60 coin-days; funding mean-9, perp age and 30-day perp quote volume for 210 coin-dates (`check_stdout.txt`).
- **Verifier `verify_r1_claims.py`:**
  - a placeholder in the E4 σ check (`or True`) would have made that check always pass. It was removed before any run; the check is now strict (σ must match exactly where 60 days of history exist; rows without that history are counted and reported);
  - 20 weight sets are now re-derived independently.

## 5. Verifier strengthened before the first experiment result was seen (2026-10-16, while E3 was running)
- V2 now also re-applies G5 (the control gate) from the stored control lists with a plain median, and checks that
  `decision` == PASS iff every gate is true (or "n/a" for E1b G5), and that the gate set is exactly G1..G5.
- E3: F7 short P&L (from the F7 RS trade files), the E3b short P&L (from trades_E3b_AGE.csv) and the E3c median are
  re-derived and the reading rule is re-applied.
- No engine / runner / protocol change; the runner hash in the claims is unaffected.

## 6. 2026-10-16: E4 first run INVALID: the 30 % cap was silently exceeded (found by verifier V3)
- **Finding:** `verify_r1_claims.py E4` V3 failed: in 154 of 5,284 (sleeve, decision, side) weight sets the max weight
  was 0.333 (3 targets) or 0.5 (2 targets). With fewer than 4 targets a 30 % cap cannot sum to 1; `cap_weights` then
  fell back to equal weights, i.e. it broke the protocol rule "each weight is capped at 30 %". The same function serves
  the Dirichlet control.
- **Status of that run:** the result (final 61,379.10, DD 20.06 %, decision FAIL) is NOT a protocol-faithful E4 run.
  Kept for the record as `claims_E4_INVALID_cap_deviation.json` / `verify_E4_INVALID_stdout.txt`; it is not used.
- **Fix (literal reading of the protocol, written BEFORE the corrected run):** cap every weight at 30 %, redistribute the
  excess pro rata to uncapped weights while any exist; when all weights are capped, the remainder stays UNALLOCATED
  (cash). So weights sum to min(1, 0.30 × n). No renormalisation above the cap.
- **Order of work:** N1 was already running with the current runner, and the runner records its own hash at the end of
  a run, so the runner is edited only AFTER N1 finishes; then a synthetic test of the cap (n = 2, 3, 5) is added, then
  E11, then the corrected E4 (and its control) is run. The verifier keeps the strict check (sum <= 1, every w <= 0.30)
  plus sum == min(1, 0.3 n).
- **Applied after N1 finished (runner unchanged during every run so far):** `cap_weights` no longer renormalises; the
  only diff is the last two lines of that function (`break` comment, `return w` instead of `return w / w.sum()`).
  `cap_weights` is used ONLY by `h_e4` and `h_dirichlet` (E4 and its control), so the E3, E1, E2 and N1 results are
  unaffected by this change.
- runner-valid: 37aac71488443d19912b941e4567df649665ff4ba3c05a95f0a49c3d1d1430b8 for E3, E1, E2, N1
- New runner SHA: 0d898580a206c4fb14f760524c8beddf032f489b5ca1be103e8b9b47a6682a2f (used for E11 and the corrected E4).
- Synthetic test T8 (cap) added: FAILED on the old code ([1, 1] -> [0.5, 0.5]) and PASSES on the new code; T0..T7 still PASS.
