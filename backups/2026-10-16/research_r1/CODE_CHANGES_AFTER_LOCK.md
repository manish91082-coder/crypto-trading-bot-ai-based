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
