# Code notes: implementation choices the protocol did not spell out (written before any Part B result was seen)

1. **Exit time** (used by "a new signal only if its entry bar opens at or after the previous exit time"):
   - SL / TP touched inside 5m bar k → the end of that bar (open_k + 5 min);
   - a gap fill at the open of bar k → open_k;
   - end of day → 24:00.

2. **A correction to the protocol's parenthetical.** Protocol §4 says a long and a short qualifying on the same sweep bar is "impossible by construction". That is wrong.
   - One 15m bar can wick below one level and above another, and be a new day low and a new day high at once (an outside bar).
   - The rule itself ("→ skip") is applied as written: if both sides have a complete signal (sweep + new extreme + confirmation) from the same sweep bar, neither is taken.

3. **Random control.** The random trades of one seed are drawn independently and may overlap in time. The draws:
   - one draw per real trade, in the stored trade order, from `numpy.default_rng(seed)`;
   - the entry is a 15m bar open other than the day's first bar, at or after 08:00 when Q1 applies;
   - the same side, the same R % and the same exit logic as the real trade.

4. **Levels** (prior-day and 7-day) come from the 5m data aggregated to UTC days. The verifier checks this aggregate equals the 1d file (K1c).

5. **MAE / MFE.** MAE % can be negative when the price never went against the entry before the exit.

6. **Part E.** The selection gave 40 ISO weeks; the protocol's "~39" was an estimate. The list is in `manual/selected_days.txt`.
