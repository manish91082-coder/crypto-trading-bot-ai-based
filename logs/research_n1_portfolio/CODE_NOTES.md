# N1 code notes: implementation choices where the protocol is silent (written BEFORE any N1 result)

Protocol: `N1_PROTOCOL_PREREGISTERED.md`, SHA `20ffc364…`.

1. **ATR14 seed.** The first bar's TR = high − low. Afterwards TR = max(H − L, |H − C₋₁|, |L − C₋₁|), with EWM α = 1/14, adjust = False.
2. **Hour mapping.**
   - Entry hour a = the 1h bar whose start equals the TF entry bar start.
   - The signal exit is at the open of hour b (the TF exit bar start).
   - The stop scan runs over hours a … b − 1. Missing 1h bars are not scanned.
   - The close is forward-filled over missing hours for marking.
3. **Funding.**
   - A funding record at time f counts for a trade when entry_time < f ≤ exit_time, as in TFX.
   - For a stop, exit_time = the start of the stop hour.
   - The funding P&L is booked in the hour of f (or the next hour when f is not on the hour).
4. **Random-entry pool (G1).** The pool is the bars of the same coin and TF in the same calendar year **and inside the same window as the original trade** (dev trades stay in dev). This keeps the count of dev entries equal; 2025 dev trades are otherwise relocatable into P3. The other pool conditions are:
   - the entry has a perp (entry_time ≥ the first funding record);
   - e ≥ 1 and e + hold < n;
   - for C, the entry day is liquid.

   The draw is uniform, with replacement.
5. **Heat cap (K2).**
   - Heat is measured in fractions of the sizing equity E_m.
   - A position is open for heat purposes while its exit hour > the new entry hour.
   - Simultaneous entries are processed in the order: hour, sleeve (A, B, C), coin, TF (4h, 8h, 12h, 1D), family.
   - If the no-stop overlay (K1) is also adopted, the risk proxy is the same 3-ATR distance.
   - Overlay multipliers (K3, K6) are applied before the heat scaling.
6. **Correlation and vol windows (K3, K6).**
   - Daily close-to-close returns of the 1D bars.
   - The window = the 60 days ending at the last complete day before the entry, i.e. day floor(entry) − 1, with min_periods = 40 (pairwise for the correlation).
   - Without enough data, the multiplier is 1.
7. **D sleeve.**
   - D4's code path is reproduced exactly: same eligibility, same `sort_values` call, and the D4 funding rule (0 funding when the period starts before the coin's first funding record).
   - Each D leg is a trade with no stop and no per-trade fee. The turnover cost 0.00054 × 0.2 × turnover is booked at the period's entry hour.
   - **Check:** the per-period unit P&L must equal 0.2 × the D4 `ret` (`D4_periods_1D.csv`) to 1e-12.
8. **G7 (2018–19).**
   - The C/D universe is every coin in `data/universe_pre2020/1h` except the stablecoins BUSD, PAX, TUSD, USDC, USDS and USDSB.
   - The A/B universe is the core10 coins that exist then.
   - Signals use the TFX `conditions` / `state_trades` on the pre-2020 1h bars resampled to the TF.
   - D long-leg turnover is costed at spot 0.085% and short-leg turnover at 0.054%.
9. **Reproduction asserts before any portfolio result.**
   - Without stops, every A/B/C trade's gross and funding must equal the TFX file's `gross` / `fund` to 1e-12. This proves the time mapping and the funding convention.
   - The D periods must reproduce D4.
