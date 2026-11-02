# Amendment 1 to ORACLE_9M_PROTOCOL (SHA 2c68bbc4…): Part C method lists, ranking rules, and the Part D selection rule and gates. Locked 2026-10-26

## Background
- **Written after Part A / B.** Part B failed (`V1_RESULTS.json`).
- **Two in-sample diagnostics were already seen.** They are not locked and are recorded in `DIAGNOSTIC_RANDOM_BARRIER.md`:
  1. Random-time trades with a ~0.87% stop and a 2R target lose −0.26% gross per trade on 2026.
  2. The mirror trade (opposite side, TP 1R, SL 2R) made +0.169% net per trade.
- **Part C is therefore partly informed by 2026.** Every Part C number is in-sample. The only evidence that counts is Part D, on the sealed 2020–2025.
- **Order changed, recorded honestly.** Part E (the 40 manual days) moves after Part D. It cannot change anything locked here.
- **Code:**
  - main `src/research/oracle_9m_c.py`;
  - verifier `src/audits/verify_oracle_9m_c.py` (independent, plain loops).
- **Data, days and costs** as in the protocol: 272 statistic days (2026-02-13 excluded), costs from `deploy/fees.json`.

## C1. Direction methods (one call per day, or per event; target = the sign of the return from the decision time τ to the day's 23:55 close)

| Id | τ (UTC) | Call |
|---|---|---|
| DIR_LONG | 00:00 | always long |
| DIR_PD_FOLLOW | 00:00 | sign of the prior day's return |
| DIR_PD_FADE | 00:00 | opposite of DIR_PD_FOLLOW |
| DIR_CLOSEPOS | 00:00 | long if the prior close position in its range > 0.5, else short |
| DIR_7D_MID | 00:00 | long if the prior close > (d7h + d7l) / 2, else short |
| DIR_H1_FOLLOW | 01:00 | sign of the 00:00 open → 00:55 close move |
| DIR_ASIA_FOLLOW | 08:00 | sign of the 00:00 open → 07:55 close move |
| DIR_ASIA_FADE | 08:00 | opposite of DIR_ASIA_FOLLOW |
| DIR_SWEEP | close of the confirm bar | first event of the day in `sweep_events` with `new_extreme` and `confirmed`: bull → long, bear → short. Days without one are not counted |

**Rules**
- A zero move gives no call, and the day is not counted.
- **Hit:** the sign of the call equals the sign of (close_23:55 − price at τ). The price at τ is the open of the 5m bar at τ; for DIR_SWEEP, the confirm bar's close.

**Reported per method**
- the number of calls, hit rate and Wilson 95%;
- the binomial two-sided p vs 50%;
- mean signed return to the close %;
- for the 00:00 methods, the difference vs DIR_LONG's hit rate.

**Ranking:** by the Wilson lower bound.

## C2. Entry triggers (quality of the entry moment)

**Measure.** From the entry price, which comes first in the signal direction: **+1.0%** (favourable) or **−1.0%** (adverse), within 4 h (48 5m bars, starting with the entry bar)?
- If both are touched in one 5m bar, it counts as adverse.
- If neither is touched, the result is "none".

**Break-even.** A symmetric ±1% trade with a 0.092% cost breaks even at p* = (1 + 0.092) / 2 = 0.546. The share is p = fav / (fav + adv).

| Id | Trigger | Direction | Entry |
|---|---|---|---|
| ENT_SLOT_FADE | every 4h slot 00, 04, 08, 12, 16, 20 | opposite of the sign of the previous 4h (the open of the slot 4h earlier → the close of the 5m bar before the slot) | the 5m open at the slot |
| ENT_SLOT_FOLLOW | same | the sign of the previous 4h | the 5m open at the slot |
| ENT_SWEEP_CONF | every `sweep_events` row with `new_extreme` and `confirmed` (one per bar and side) | bull → long | the open of the 15m bar after the confirm bar |
| ENT_SWEEP_ALL | every sweep bar (one per bar and side) | bull → long | the open of the next 15m bar |
| ENT_H1_BREAK | the first 5m close after 01:00 beyond the 00:00 … 00:55 high or low | the direction of the break | the next 5m open |
| ENT_H1_BREAK_FADE | same | opposite | the next 5m open |
| ENT_EXT_FADE | after 08:00, the first 5m bar whose close makes a new day low (high) | long (short) | the next 5m open; once per side per day |
| ENT_RANDOM | 6 random 5m bars per day, seed 0 | a coin flip, seed 0 | the bar's open |

- Triggers whose entry would fall after 23:55 are dropped.
- The 4 h window may run past midnight. The data to 2026-09-30 23:55 bounds it, and the last day's windows are cut there.

**Reported per trigger**
- the counts fav / adv / none;
- p and its Wilson 95%;
- p − p*;
- mean signed 4 h return %;
- the median distance (%) from the same-side A1 perfect entry of that day, as |entry − A1 entry| / A1 entry.

**Ranking:** by the Wilson lower bound of p.

## C3. Whole rules: scheduled slot entries × direction × stop size × exit geometry (this includes the mirror lead)

**Entries:** the 6 slots per day, at the 5m open at 00:00, 04:00, …, 20:00.

**Exit window:** each trade lives inside its own 4 h window. Without a TP / SL exit, it closes at the close of the last 5m bar before the next slot. So there is no overlap; the 20:00 slot closes at 23:55.

**Direction**

| Id | Call |
|---|---|
| L | always long |
| S | always short |
| FADE | as in ENT_SLOT_FADE |
| FOLLOW | as in ENT_SLOT_FOLLOW |
| RAND | a coin flip per slot, `default_rng(0)`, drawn in slot order over the 2026 window |

A zero previous-4h move gives no trade for FADE / FOLLOW.

**R** (the stop unit, as a fraction of the entry price)

| Id | Value |
|---|---|
| R05 | 0.5% |
| R08 | 0.8% |
| R12 | 1.2% |
| RVOL | 0.33 × the prior day's range % |

**Geometry** (TP, SL) in units of R

| Id | TP | SL |
|---|---|---|
| G12 | 1 | 2 (the mirror lead) |
| G11 | 1 | 1 |
| G21 | 2 | 1 |
| G051 | 0.5 | 1 |
| G1N | 1 | none (time exit only) |

**Fills:** as in Part B. SL first; a gap fills at the open; TP at its price, or at the open if gapped beyond it.

**Cost:** FUT taker, 0.046% per side.

**Extra rows:** for direction L, every R × G is also reported at the SPOT cost (0.085% per side).

**Count:** 5 × 4 × 5 = **100 FUT configs** + 20 SPOT rows.

**Reported per config**
- trades, wins, win rate and Wilson 95%;
- mean net per trade;
- **mean net per day** (with zero for days without a trade), and its 95% CI from **weekly clusters** (ISO weeks):
  - SE = sqrt( n_w / (n_w − 1) × Σ_w (W_w − m·d_w)² ) / D;
  - W_w = the week's net sum, d_w = its day count, m = the mean per day, D = the total days;
- **lb95** = m − 1.96·SE, and **lb_bonf** = m − 3.48·SE (Bonferroni for 100 configs, two-sided α = 0.05);
- months positive of 9, worst month, max drawdown of the cumulative daily net;
- mean MFE captured: realised gross / MFE inside the trade, over trades with MFE > 0;
- the comparison with RAND at the same R × G: Δ total net.

**Exit-method ranking.** The 5 geometries are also ranked by their mean, over the 20 direction × R cells, of mean net per trade.

**Whole-rule ranking.** All 100 configs in one table, sorted by lb95.

## Daily / monthly entries (no day skipped)

| File | Contents |
|---|---|
| `c3_daily.parquet` | every config × every one of the 272 days, with a zero row when there is no trade |
| `c3_monthly.csv` | the monthly sums per config |
| `c3_trades.parquet` | every trade |
| `c1_calls.csv`, `c2_events.parquet` | every call and every event |

## Part D selection rule (fixed now, before Part C runs)

**Selected:**
1. Up to **3** C3 FUT configs with the highest lb95, among those with lb95 > 0 **and** ≥ 6 / 9 months positive.
2. Plus, always, the **pre-declared lead: RAND × R08 × G12**, the closest to the diagnostic. It is included whatever its Part C result.
3. Plus the top C1 direction method and the top C2 trigger. These are reported with their C1 / C2 metrics only, as context, not as rules.

**Part D data:** 2020-01-01 … 2025-12-31, excluding the 9 manual-study days of those years (`logs/manual_day_study/selected_days.txt`). Same code, same fills, same costs.

**Part D gates.** A config **passes** only if all of these hold:
1. lb95 of mean net per day > 0;
2. ≥ 60% of months positive;
3. ≥ 4 of the 6 calendar years with a positive sum;
4. total net > RAND at the same R × G. This one is not applied to the lead itself, which is RAND.
5. **Data check:** every 2020–2025 day has 288 5m bars. Days with missing bars are listed and excluded, and the count is reported.

**Amendment 2** will only record the selected configs and the SHA of the Part D code before it runs. It cannot change these gates.
