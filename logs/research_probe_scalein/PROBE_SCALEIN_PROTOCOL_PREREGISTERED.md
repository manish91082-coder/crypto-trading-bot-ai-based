# Ladder entries with a test (probe) entry and scale-in vs a full entry: pre-registered (2026-10-17)

This protocol is locked with SHA256 before any result is computed. It is a historical research simulation: no orders, no AI training, nothing deployed. Every change after the lock goes into `CODE_CHANGES_AFTER_LOCK.md`.

**Question (user):**
- Can a small "test" entry, or a paper probe, followed by adding size only when price moves our way, reduce losses on ladder (staircase) entries?
- How does that compare with taking the full size at once, after Binance costs (fees paid in BNB), with automatic stops and a trailing stop?

## Data
- **Swings:** `data/derived/swing_anatomy/legs_all.parquet`, SHA `bbe7a4fd…f0f`, K = 3, 10 coins.
- **Bars:** built from `data/universe_hf/5m/<coin>_5m_full.csv.gz` (UTC, left-closed) for the 5m, 15m, 1h, 4h and 1D timeframes.
- **Period:**
  - Signals with entry from 2020-02-01 to 2026-09-30.
  - Reported separately for P1 2020-02..2023-12, P2 2024-01..2025-09 and P3 2025-10..2026-09. P3 was already seen in earlier work.
- `archive/` is not used.

## Signals (structure only, no AI)
- **Long:** a swing low labelled HL while the latest swing high is HH (UP ladder).
- **Short:** a swing high labelled LH while the latest swing low is LL (DOWN ladder).
- **Known time:** the `confirm_time` of the next leg, which is the close of the confirming bar.
- **Entry:** at the OPEN of the bar that starts at the known time.
- **Size of one risk unit:** ATR = `atr_confirm` of that next leg.
- **Initial stop:**
  - long: swing low − 0.5 ATR;
  - short: swing high + 0.5 ATR.
- **R** = |entry − initial stop|. All results are in R per trade, the money risked by one full unit at the planned entry.

## Exits (identical for all variants; fixed and not optimised)
- **Trailing stop:**
  - long: stop = max(initial stop, highest high of bars before the current bar − 3 ATR);
  - short: the mirror image.
  - Checked every bar. Fill at the stop, or at the bar's open if the open gapped through the stop.
- **Time stop:** exit at the close of bar 60 after entry.
- **Bar order (conservative):** if a stop and an add trigger are both inside the same bar, the stop is taken first and no add happens.

## Variants (fixed, 4)
| Variant | Description |
|---|---|
| V0 FULL | 1.0 unit at entry |
| V1 PROBE + ADD | 0.25 at entry, plus 0.75 when price reaches entry ± 1 ATR in our favour |
| V2 PYRAMID | 0.25 at entry, + 0.25 at ±1 ATR, + 0.5 at ±2 ATR |
| V3 PAPER PROBE | no money at entry; 1.0 unit only when price reaches ±1 ATR in our favour |

- In V3, if the stop is hit before the trigger, the trade is skipped and counts as 0 R.
- Add fills are at max(open, trigger) for longs and min(open, trigger) for shorts.
- All units share the same stop and the same exits.

## Costs (fees paid in BNB, the user's default)
- **Perp, long and short:** 0.045% of notional per side. This is the 0.036% BNB taker fee plus about 0.009% spread and slippage (`FEE_SPREAD_BREAKEVEN_4H_17_OCT_2026.md`).
- **Funding:** 0.01% of notional per 8 hours held, charged to both sides as a conservative assumption.
- **Spot long (separate report):** 0.085% per side, no funding.
- **Stress:** 2 × all costs.

## Metrics, for each timeframe × side × variant
- trades;
- win rate;
- mean, median and 5th-percentile R;
- sum of R;
- mean gross R (before costs);
- mean cost in R;
- the share of trades where gross |gain| < cost;
- max drawdown of the cumulative R path (all coins merged, ordered by entry time).

**Differences (V1, V2, V3) − V0 in mean R:** 95% bootstrap CI, resampling coin-year blocks, 2,000 draws, seed 20261017.

## Pre-registered verdicts (per timeframe and side, base costs)
- A variant **"earns more"** if its mean-R difference CI lies above 0.
- It **"cuts losses"** if its 5th-percentile R is better than V0's **and** its mean-R difference CI does not lie fully below 0.
- It **"costs profit"** if its mean-R difference CI lies fully below 0.

**Overall verdict:**
- "Scale-in recommended" only if V1 or V2 earns more on ≥ 3 of the 5 timeframes for the same side, **and** the same holds under 2× costs.
- Otherwise "not proven", plus the trade-off (loss cut vs profit given up) shown per timeframe.

## Verifier (separate code)
`src/audits/verify_probe_scalein.py`:
1. Re-simulates 300 random trades (all variants, both sides, several timeframes) with its own loop from raw 5m bars, and must match to 1e-9 R.
2. Recomputes the summary means for 4h and 1D from the trades file.
3. Checks the claims JSON against the CSVs, and the protocol and data SHAs.

## Honest limits (fixed in advance)
- Rule-based signals only; no AI. This tests the scaling idea, not a final system.
- The exits are fixed placeholders.
- The funding figure is assumed, not real per-timestamp funding.
- 10 large coins only.
- Minimum order sizes are not modelled.
