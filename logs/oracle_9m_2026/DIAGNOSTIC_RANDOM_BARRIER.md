# Diagnostic, not locked: why the random control loses more than v1 (run 2026-10-26 after Part B)

## Real 2026 BTC data
- **Setup:** seed 0. The 465 V1-A trades, each moved to a random 15m entry bar of the same day, with the same side, the same R % (mean 0.87%), a 2R target and an end-of-day exit (`oracle_9m.simulate`).
- **Exits:** SL 264 (mean gross −0.822%), TP 57 (+1.560%), EOD 144 (+0.166%).
- **Mean gross:** −0.224% per trade (long −0.241%, short −0.206%).
- **Real V1-A, for comparison:** mean gross −0.085%. Exits: SL 262, TP 85, EOD 118.

## Synthetic driftless check
- **Path:** a log random walk with 20 sub-steps per 5m bar, σ 0.0007 per sub-step, 288 bars.
- **Trades:** 3,000 trades with the same simulate function, R 0.87%, 2R target, random entry, alternating sides.
- **Mean gross:** +0.068% (se 0.022).

## Reading
- The simulate function has no negative bias.
- The −0.22% on real data is a property of the 2026 BTC paths: after a ~0.9% adverse move the price often comes back, and the 2R target is reached less often than in a random walk.
- This is a hypothesis for Part C (Amendment 1), not a result.

## Diagnostic 2: the mirror trade (in-sample 2026, not locked)

**Run:** 2026-10-26, after the user's question, 200 seeds.

**Setup:**
- The same random entries as the random control of V1-A: 465 trades per seed, at a random 15m bar of the same day, with the same R %.
- **Original trade:** the V1-A side, SL at 1R, TP at 2R.
- **Mirror trade:** the opposite side, TP at 1R, SL at 2R.
- The SL is checked first inside a 5m bar, so the mirror is not an exact negative of the original.

**Results:**

| | Original | Mirror |
|---|---|---|
| Gross per trade | −0.2611% | +0.2610% |

- **Mirror net:** +0.169% per trade at the futures taker cost of 0.092% round trip.
- **Mirror net sum:** mean +78.6% over the 9 months; positive in 200 of 200 seeds (min +43.7%, max +129.4%).

**Caveats (why this is NOT a result):**
1. The idea was formed after looking at 2026, so it is in-sample.
2. The random trades of a seed may overlap in time.
3. R % was borrowed from the v1 sweep stops.
4. The pay-off is inverted (small wins, large losses), so it has fat-tail risk.
5. It must be pre-registered with fixed rules and tested once on the sealed 2020–2025 years.

## Diagnostic 3: CORRECTION. Diagnostics 1 and 2 were a lookahead artifact of the random-control design (found 2026-10-26 after Part C)

**What Part C showed.** In Part C, C3 tested the mirror idea cleanly: scheduled entries in 4 h windows, every direction rule known at the entry time.
- The lead FUT|RAND|R08|G12 made −0.100% net per trade, i.e. about 0 gross.
- So the +0.169% of Diagnostic 2 did not reappear.

**Cause.**
- The random control (protocol §4, Part B) kept each v1 trade's side, but drew the entry time anywhere in the day.
- That side came from a sweep that happened later in the day, at a new day low for longs or a new day high for shorts.
- A random long placed before that sweep was therefore placed on a day known to fall afterwards. This is information from the future.

**Test.** 20 seeds, V1-A trades, the same simulate function, split by whether the random entry was before or after the v1 sweep time.

| Random entry | n | Mean gross | se |
|---|---|---|---|
| Before the sweep | 3,194 | −0.715% | 0.014 |
| After the sweep | 6,106 | −0.008% | 0.012 |

**Consequences**
1. Diagnostics 1 and 2 are **withdrawn**. There is no "mirror edge".
2. The Part B random-control figures (rc_share 0.000, rc_mean) are **invalid**. The control was biased against random.
   - The claim "v1 entry timing was better than random" is withdrawn.
   - The Part B verdict (all variants fail) does not depend on it: gates 1–3 failed on their own.
3. Future random controls must draw only side rules or entry times that use no information from later in the day.
