# TURN-2026 code notes (written before the first DISC run, 2026-10-27 ~12:30 UTC)

Conventions the protocol leaves open. Each is fixed here before any result.

1. **Returns and the null path.**
   - r_t = ln(C_t / C_{t−1}) on 1m perp closes. The null path is C*_t = C*_{t−1} exp(s_t r_t), with C*_0 = C_0.
   - **Intrabar values,** relative to the bar's own close: a = ln(H/C), b = ln(L/C), o = ln(O/C).
     - s = +1: H* = C* e^a, L* = C* e^b, O* = C* e^o.
     - s = −1: the bar is mirrored, H* = C* e^(−b), L* = C* e^(−a), O* = C* e^(−o).
   - Signs come from `np.random.default_rng(seed).choice([-1, 1])`, with seeds as the protocol states.
2. **ZigZag / T1 state machine.**
   - **Start:** direction 0. The first close ≥ min × (1 + θ) sets an up leg; the first close ≤ max × (1 − θ) sets a down leg.
   - **New extreme:** a strictly lower close in a down leg (strictly higher in an up leg). Equality does not reset.
   - **Event:** UP(f) fires when L × (1 + fθ) ≤ close < L × (1 + θ). If one close jumps straight past L × (1 + θ), no UP(f) event exists for that L. The turn is confirmed and the leg flips.
   - **Outcome:** pending UP events of the current L complete at the confirming close and fail at the next new low. DOWN is the mirror case.
3. **Fills (T1 economics, T2 trades).**
   - Entry is the open of the minute after the event close; exit is the open of the minute after the outcome close.
   - If that minute is outside the period, the event is dropped and counted.
4. **Break-even p\*** for the T2 trade rule is f + c / θ, with c = the taker round trip. It is printed for T1 as well.
5. **CIs at Bonferroni levels** (T2 screen, HOLD criterion 2) use the normal approximation: estimate ± z(1 − α/2) × bootstrap SD. The day-block bootstrap has 2,000 resamples, seed 7. A percentile CI at α = 0.05/300 is not stable with 2,000 resamples. Plain 95% CIs are percentile.
6. **T1 "random-take" control (HOLD).** T1 takes every event, so drawing events would be degenerate. The control is:
   - **draws:** 1,000 draws of the same number of entries at uniformly random HOLD 1m closes, with random direction (±1, 50/50);
   - **geometry:** each entry exits on the same rule, TP at +(1 − f)θ and SL at −fθ from the entry close (judged on closes), with the same fills;
   - **p:** the share of draws with mean net ≥ the real mean net.

   T2 uses random draws of the same number of HOLD events of that (θ, f).
7. **Kalman (P5).**
   - **Model:** local linear trend on log close; state [level, slope], F = [[1, 1], [0, 1]], H = [1, 0].
   - **Noise:** R = (MAD of the first 500 log-close diffs / 0.6745)², from the start of the series only; Q = diag(qR, qR).
   - **Start:** level = first log close, slope 0, P = diag(R, R).
   - **State:** sign of the filtered slope.
8. **CUSUM (P7).**
   - z_t = r_t / σ_{t−1}, where σ is the EWM std (span 100, adjust False) of past bar returns.
   - S⁺ = max(0, S⁺ + z − 0.5), S⁻ = max(0, S⁻ − z − 0.5).
   - S⁺ > h → state +1 and both reset; S⁻ > h → state −1 and both reset.
9. **Other indicator definitions.**
   - **Hull:** WMA(2 WMA(n/2) − WMA(n), round(sqrt n)).
   - **ZLEMA:** EMA_n(2c − c_{t−lag}), lag (n − 1)//2.
   - **RSI:** Wilder alpha 1/14; RSI = 50 → 0.
   - **Bollinger:** %b uses SMA20 ± 2 std (ddof 0).
   - **Heikin-Ashi:** HAo_0 = (o + c)/2.
   - **Fractals:** a 3-bar pivot, confirmed one bar later.
   - **SuperSmoother:** scipy `lfilter` with Ehlers' 2-pole coefficients.
   - **Linear-regression t:** OLS of log close on 0 … n − 1.
10. **5m tables.**
    - A row stamped T is usable at times ≥ T + 5 min. A TF bar or event at close time X uses the last row with T + 5 min ≤ X.
    - Funding is used from its stamp.
    - ETH spot 5m closes follow the same rule.
11. **HTF features F10–F12 and M1.**
    - HTF bars come from the loaded 1m series (UTC-anchored).
    - "Slope sign" = sign(EMA20_k − EMA20_{k−1}) of the last HTF bar closed at or before the decision time.
12. **T3 position rule.**
    - Position during bar t+1 = d_t. A trade opens at bar t+1's open and closes at the open of the bar where the position changes.
    - The last trade closes at the period's last close.
    - Accuracy uses the open-to-open return of bar t+1.
13. **HOLD warm-up.** Indicators and features may use data before 2026-06-01 (earlier, so causal). Only trades and events after HOLD starts count.
14. **Memory (2 GB free).** 1s files are read one month at a time; only per-event windows are kept.
15. **T2 AUC bootstrap:** day-block with 500 resamples per (θ, f, feature), seed 7, giving 300 bootstraps. The Bonferroni interval is AUC ± 3.76 × SD (CODE_NOTES 5); 500 resamples are enough for an SD. T1 CIs use 2,000.
16. **T4 seconds null:** sign flips are drawn per month series (seed s × 100 + month position), and month boundaries are not crossed. There are 100 paths, as in the protocol.
17. **Timestamps:** all times are forced to datetime64[ns] before integer arithmetic (pandas 3 may default to µs).
18. **First DISC run, 17:40–18:02 UTC: crashed in `spot_features`.**
    - **What happened:** when the event's L lies in the previous month, the 1s window start went negative and the slice was empty.
    - **State at the crash:** T0 and T1 had already printed their numbers (shown in `run_log.txt`). T2 had produced no output, and T3/T4 had not started.
    - **Fix:** the window start is clamped to the month's first second.
    - **Consequence:** for such events F19 (spot close at L) stays NaN, because L's minute is outside the loaded month.
    - **Re-run:** the whole DISC stage is re-run from the start, so the T0/T1 numbers are recomputed. They are deterministic.
19. **Correction to note 18 (written after HOLD).**
    - The times "17:40–18:02 UTC" in note 18 are **IST** (local), not UTC: `run_log.txt` stamps local time. In UTC the first run was 12:10–12:32, after the protocol lock at 11:59:39.
    - The second DISC run was 12:42–13:39 UTC. HOLD was opened at 13:44:03 UTC (`HOLD_OPENED.txt`).
    - Note 18 is left unchanged so the record stays as written.
