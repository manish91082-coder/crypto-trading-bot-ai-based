# ECO: code notes (interpretations fixed BEFORE the corresponding result was computed)

## Note 1 (2026-10-21, before E-1 / E-2 ran): combination accounting

§5 says "daily portfolio return = Σ a_s,m × r_s,day, a fixed for the month", with sub-accounts rebalanced at each month start. The live executor (§2) sizes every strategy as a_s × E_m × f_s, where f_s is the paper exposure ÷ paper equity and E_m is the month-start eco equity. Its daily P&L is therefore ≈ E_m × Σ a_s × r_s,day.

**Implementation** (identical to the formula, measured against E_m):
- E_d = E_{d−1} + E_m × Σ a_s,m × r_s,d.
- E_m is reset at each month start.
- r_s,d = V_s,d / V_s,d−1 − 1 from each strategy's own daily equity.

**Daily values.**
- 1D (M_AI3): the file row d is the equity at the close of day d. On 2021-01-01 it is 10,000 with no positions, since the first decision fills on the next bar.
- N1: the hourly curve is taken at the last hour of day d.
- So both are "end of day d".
- A window starting 2021-01-01 uses base 10,000. A later window uses the 1D row of the day before the start as its base.

**Reference "N1 FINAL alone".** The N1 engine's own curve, sampled daily as above. As a consistency check, the combination code is also run with a = (0, 1) and reported.

**Daily sampling.** All Calmar / MTM-DD numbers in E-2 come from daily values, for both strategies and the combination, so the comparison is like for like. The E-1 reproduction gate uses the engine's own hourly statistics, as in the N6 claims.

## Note 2 (2026-10-22, AFTER the amendment-1 §2 count was seen; a design detail §2 did not fix): outage guard trigger price

- **Result of §2 (`A1_outage_guard.json`).** D = 0.50 by the pre-registered rule (share 4.16e-5 ≤ 1e-4).
- **Problem the events show.** The listed events include the 2025-10-10 21:00 UTC flash crash, with last-price wicks of −50 … −62% within one hour on many coins (ADA −61.8%, ALGO −50.6%, 1INCH −52.8%, …). A guard triggered on the contract (last) price would have sold the longs at the bottom of that wick.
- **Decision.** The guard uses `workingType = MARK_PRICE`. The Binance mark price is built from a multi-exchange index plus a funding basis, and is designed to resist single-venue wicks.
- **Status of this decision.** It was taken after seeing the events, so it is labelled post-check. It does not touch any backtest number. The guard is not part of any simulated result.
- **Unchanged.** The 1D-short stops (§3) keep CONTRACT_PRICE, as in F6 and F7.

## Note 3 (2026-10-22, before any stop code ran): exchange-stop details amendment 1 §2/§3 leaves open

**Endpoints.** Only those already proven by F6 on the demo host are used:
- `POST /fapi/v1/algoOrder` (CONDITIONAL STOP_MARKET, quantity, triggerPrice, workingType, reduceOnly);
- `GET /fapi/v1/openAlgoOrders`;
- `GET /fapi/v1/algoOrder?algoId`;
- `DELETE /fapi/v1/algoOrder?algoId`;
- `DELETE /fapi/v1/algoOpenOrders?symbol`.

**Guard.** `closePosition` was never exercised by F6, so the guard is a `reduceOnly` STOP_MARKET for quantity |net| (floored to the step). It is re-placed whenever |net| changes by at least one step, the side flips, or the mark moves > 10% from its reference.

**MARK_PRICE.** This `workingType` is not yet proven on the demo host. The first demo cycle's response is the proof; a rejection is logged as "guard not placed" and becomes a cut-over check.

**Triggered exchange stops.** The status is read at the START of a cycle, before targets.
- **1D-short component stop:** booked as a fill of +|q| for that component at the trigger price. The true fill is in the account; the difference shows in TC as slippage. The component is suppressed.
- **Guard:** every component on that symbol is booked to 0 at the trigger price. The symbol is then **frozen until the user resets it** (`st["guard_fired"]`): no automatic re-entry after a ≥ 50% move.

**Plan mode.** Stops are computed, diffed and logged ("would place / cancel") under plan ids. No trigger is simulated in plan mode; the hourly virtual check covers the 1D shorts there.

## Note 4 (2026-10-22, amendment 2 coding; details §1–§8 leave open, and one deviation)

**Deviation from amendment 2 §4 text (TRIGGERED without a fill).**
- §4 says TRIGGERED / FINISHED → book `actualQty`, and drop the stop when `actualQty` is 0.
- The Binance docs define TRIGGERED as "placed in the matching engine", which is not yet necessarily filled. Dropping a TRIGGERED stop without a fill could lose a fill that arrives seconds later.
- **The code:** TRIGGERED with `actualQty > 0` → booked; TRIGGERED without a fill → **kept** and decided next cycle (like TRIGGERING); FINISHED without a fill → dropped.
- This is stricter on the side of not losing a fill. It is listed in CODE_CHANGES 6.

**Kill switch booking.**
- At the kill, the ledger books its OWN quantity of each symbol (−held) at the exchange fill price.
- A different exchange quantity (mismatch) is closed on the exchange but not attributed; the difference is noted.
- A ledger position the exchange no longer shows is closed in the ledger at the mark (fee 0, noted).
- After the kill, ledger and exchange are both flat.

**Order ids.** `eco<yymmddHHMM>n<i>`: unique per order, deterministic per cycle.
- The old `ms % 1e10 + len(fills)` gave the same id to the order after an unconfirmed one in the same millisecond. Test A2-7 found it.
- On Binance the order query also carries the symbol, so the old ids would not have mixed two symbols there. The mock (cid only) was stricter.

**Caps with eco equity ≤ 0.** All non-frozen targets are 0. Percent caps on a negative equity would flip the signs. A2-4's first draft found it: a 5× test book fell to an eco equity of −1,135 USDT. That is not realistic at our sizes, but it is possible after a gap.

**Funding.** It is booked BEFORE the orders on the held components, with the amount computed on their net.
- The first coding of §6 booked it after the orders, with the pre-order amount.
- That split the amount over the wrong (post-order) components, and dropped it when the net became 0.
- The E-3 replay regression caught it: R1 rose from 8e-10 to 1.9e-02. It was fixed before any deploy.

**Kill-cycle record.** The record now carries `halted`. Before, only the following cycles did; test A2-18 found it.

**Unconfirmed market order.**
- The journal keeps it, and the symbol gets no second order while the exchange reports the order as NEW (`PENDING`).
- A recovered PARTIALLY_FILLED is booked as its executed part. A later fill of the rest would show as a reconcile mismatch, which freezes the symbol and raises an alert.
