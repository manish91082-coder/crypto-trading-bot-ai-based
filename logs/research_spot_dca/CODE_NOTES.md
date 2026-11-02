# Spot DCA study: code notes (interpretations written BEFORE any result is computed)

1. **Random-control adds (2026-10-24, before results).**
   - The protocol says the controls keep "the same adds and exits (an add is triggered by price only, with no grade condition)".
   - P's add rule is itself price-only: close ≤ 0.85 × the last buy, plus reversal. Its 5%-vs-2% size uses the grade-A price conditions.
   - So the control uses **exactly P's add rule, including its size rule**. The only difference from P is WHICH coin each new entry buys.
2. **Q3 carry capital (before results).**
   - B1's daily return on capital assumes a fully collateralised 1× short: capital = 2 × notional (spot + an equal margin).
   - So the return on capital is half the return on notional.
   - The B1 margin table shows whether less margin would have survived.
3. **B1 switch cost (before results).**
   - The protocol reads "each switch costs 4 legs × 0.05%". It is applied literally: 0.20% of notional per state change (in → out or out → in).
   - This is conservative: a one-way switch really trades 2 legs.
4. **B2 hedge P&L (before results).**
   - The hedge does not change P's own sizing (P sizes from its unhedged equity). Hedged equity = P equity + the cumulative hedge P&L.
   - The short's margin is assumed to come from P's idle cash. The report shows the hedge notional vs the idle cash.
5. **Missing bars inside a series.**
   - A day with no bar for a coin means no fill, no TP check and no decision for that coin. The position is marked at its last close.
   - "Delisted" means the file ends before 2026-09-30. The position is sold at the last close, on the last bar day.
