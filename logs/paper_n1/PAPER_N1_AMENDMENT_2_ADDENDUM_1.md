# PAPER-N1 amendment 2, addendum 1 (2026-10-24): one consequence of §2 that the scope line missed

**Refers to:** `PAPER_N1_AMENDMENT_2_PREREGISTERED.md` (56dbbe1f…). The amendment text stays as locked; this addendum records a fact found by its own check C3.

**Locked:** after C3 found the fact, and before the cloud update.

## What C3 found

1. **The first code version kept one request path for inactive coins.**
   - The first code (0e10d999…) still requested perp volume for inactive coins inside sleeve C's liquid-coin count (`nliq`).
   - In the sandbox cycle 2026-10-24 08:00, the `SXPUSDT` error remained.
   - This broke §2 ("not requested"). The unit test C2a did not catch it, because its fake source made no coin liquid.
   - The test was strengthened, with a liquid falling U2X coin so that the count runs. It FAILED on 0e10d999…, and the code was fixed (621238af…). It then PASSED.
2. **Consequence for the weights.**
   - With §2 applied to the liquid count, inactive coins are no longer counted in `nliq`.
   - Some inactive coins (spot not TRADING, so the system cannot trade them) still show perp volume above 50 M.
   - On 2026-10-24 08:00 one of them was counted: nliq 23 → 22. So a new sleeve-C open is 0.4 / (16 × 22) of E_m instead of 0.4 / (16 × 23).
     - That is 11.36 instead of 10.87 USDT, +4.5% per new C open.
   - The scope line "weights … unchanged" is therefore not exact.
   - Sleeve C's weight denominator now counts only coins the system can trade.
   - Signals, the universe list, venues, fees and every other weight are unchanged.

## C3 evidence (the sandbox cycle 08:00 vs the live cycle by the old code, same public data)

- `data_errors`: sandbox [] vs live [SXPUSDT 400].
- 14 vs 14 actions, the same keys, sides and prices.
  - The 9 new C opens differ only in notional, by the ratio 23/22 exactly.
- Equity differs by 0.0024: the fee on the larger notional, 9 × 0.494 × 0.00054.
- Lists: 27 inactive and 2 perp_out (FTTUSDT, RAYUSDT). They equal an independent exchangeInfo read. No held coin is in them.
