# Master bench amendment 1 (2026-10-26): no shortcuts. Written and locked before any Batch 1 number is computed

**Amends:** `MASTER_BENCH_PROTOCOL_PREREGISTERED.md` (0ee7aff8…). Everything else is unchanged.

**Why (user, 2026-10-26).** Every daily, monthly and yearly entry must be complete. No data and no test may be skipped, and nothing done by shortcut. Every possible testing method is to be used.

## Changes

1. **Periods.** D, V and H stay as they are. A **FULL** run (2020-01-01 … 2026-09-30, continuous) is added for every configuration.
   - It gives one unbroken daily equity series from the first day to the last.
   - Every calendar day appears, including days without trades (n = 0, equity carried).
   - Days inside the exchange data gaps are kept: no trade can start inside a gap, and the equity is carried.
2. **Reports for both cost models:** futures taker and spot. Each covers every configuration × exit × period (D, V, H, FULL):
   - **daily:** date, trades closed, net sum, equity;
   - **monthly:** return, trades;
   - **yearly:** return, trades.
3. **Random-entry control (G3) for every configuration**, not just the top 20:
   - **X1 / X2:** as before (same n, direction mix and barrier).
   - **X3:** random entry bars with the same n and direction mix. Each random trade's holding length is drawn without replacement from the configuration's own H holding lengths, and it exits at the close after that many bars. 200 seeds.
4. **Extra testing methods**, primary cost, run on H and FULL for every configuration:
   - **R-stress:** 2 × the round-trip cost (0.184%);
   - **R-delay:** the entry one 5m bar later (the signal shifted by 1 bar), to test execution delay;
   - **R-year:** mean net per calendar year 2020 … 2026, from the FULL run; the share of positive years is reported.
5. **The ranking adds two measures:** R-stress mean (a higher rank is better) and the R-delay sign agreement. The rank score is now the mean over 8 measures.
6. **Edge label adds G6:** the R-stress H mean > 0 **and** the R-delay H mean > 0.

## Verifier additions

- **W4:** applies to every period, including FULL, and to both costs.
- **W6:** the random control is re-checked for 3 configurations, one each of X1, X2 and X3.
- **W7:** the R-stress and R-delay numbers of 3 random configurations are recomputed.
