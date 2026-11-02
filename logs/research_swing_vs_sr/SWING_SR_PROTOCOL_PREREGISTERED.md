# Swings (ZigZag) vs Support/Resistance + Volume: where do they agree, and does S/R + volume confirm a swing? (pre-registered)

Written and SHA256-locked before any result is computed. Code: `src/research/swing_vs_sr_study.py`.
This is a measurement study only. No trading rule is fitted. No GitHub action.

## User's question
- We know where the swings happened (ZigZag), and we know where the S/R levels and the volume are.
- How much do the two agree?
- Does an S/R level with volume CONFIRM a swing turn?

## What swing data honestly exists
- **1D:** the verified Step 2 swing study (`logs/swing_study_1d/swing_legs_1d.csv`): ZigZag-ATR, K ∈ {2, 3, 4}, 10 coins (config SYMBOLS), 2020–2026.
- **4H:** only the pre-rebuild system's files exist (archived, unverified method, full ledger for BTC only). Not used.
- **1h:** never computed.
- **Therefore:** 1h and 4h swings are computed NOW with the SAME verified function `swing_study_1d.zigzag_pivots`. Integrity gate G0 proves that this function reproduces the stored 1D swings exactly.

## Data
- **Coins:** the swing-study coins BTC, ETH, BNB, SOL, XRP, ADA, DOGE, DOT, LTC, LINK.
- **1d bars:** `swing_study_1d.load_1d` (exactly as the swing study: data/raw, with the 99 % bad-wick clip).
- **1h bars:** `data/universe_all/1h`, with the same 99 % bad-wick clip.
- **4h bars:** aggregated from the clipped 1h bars (UTC).
- **ATR_14:** 14-bar mean true range of each timeframe.
- **Windows:** swings and events are counted from 2021-01-01 to 2026-09-30. Warm-up data from 2020-01.

## Swings
- `zigzag_pivots(df, K)` on each timeframe, K ∈ {2, 3, 4}. **PRIMARY: K = 3.**
- Final pivots are used: a swing low "L" or a swing high "H", at candle idx with price `price`.
- These are known only in hindsight. This study describes where swings happened; it does not trade them.

## S/R levels (as in the S/R studies)
- **Level:** a k = 3 fractal swing high/low on level timeframe TF_L ∈ {1h, 4h, 1d, 1w}, known from the start of bar i+4 of TF_L.
- **Active at a swing-timeframe bar p if:**
  - it was known before bar p;
  - no swing-timeframe CLOSE has crossed it since it became known (support: close < level; resistance: close > level).
- Only TF_L ≥ swing timeframe is used. Lower-timeframe levels are noise relative to a higher-timeframe swing.

## Part A: where did the swings turn?
For each final ZigZag pivot (L → support levels, H → resistance levels) at bar p with price x (ATR at bar p−1):
- **SR_hit(TF_L):** an ACTIVE same-side level of TF_L lies within 0.5 ATR of x. SR_any = hit for any allowed TF_L.
- **VAP:** the share of USDT 1h volume in the previous window that traded within ±0.25 ATR of x.
  - Window: 7 days for 1h swings, 30 days for 4h swings, 90 days for 1d swings.
  - VAP_high = VAP above the 2/3 quantile of the CONTROL VAP distribution (same timeframe and K).
- **CONTROL:** the same number of random bars of the same timeframe in the window (numpy seed 13). Price = the bar's low (for L) or high (for H), alternating L/H in the same proportions.
- **Reported:** P(SR_any), P(SR per TF_L), P(VAP_high), P(SR_any AND VAP_high) for swings vs control. Differences with 95 % month-block bootstrap CIs (2000 reps).
- **Swing size:** the move of the leg that starts at the pivot, in ATR. Pivots WITH vs WITHOUT SR_any AND VAP_high are compared (CI).

## Part B: does an S/R + volume touch confirm a swing turn?
**Events:** the first touch (bar j) of every same-timeframe k = 3 level (REAL), plus CONTROL levels (random non-swing bar highs/lows, as in the S/R study), on the swing timeframe.

**TURN:** a final ZigZag pivot of the matching kind (support → L, resistance → H) occurs at a bar in [j, j+2] with its price within 0.5 ATR of the level.

**Reported rates (K = 3):**
- REAL vs CONTROL;
- REAL with high VAP (top tercile within the family) vs low VAP;
- the median move_in_atr of the leg that follows when a TURN happens.

All with 95 % month-block CIs.

## Gates and interpretation (fixed)
- **G0 (must pass, else INVALID):** for all 10 coins and K ∈ {2, 3, 4}, the recomputed 1D pivots reproduce every leg start (date and price) in `swing_legs_1d.csv` exactly.
- A difference counts only if its 95 % CI excludes 0.
- **Agreement exists:** swings sit at an S/R level more often than control.
- **Confirmation value:** P(TURN | REAL high-VAP touch) > P(TURN | CONTROL touch).
- Nothing here becomes a trading rule. A useful result goes to the Step 29/30 pipeline (features into the R24 brain; a pre-registered test with costs and 2018–19 data).

## Verification
`src/audits/verify_swing_vs_sr.py`:
- re-derives 200 random swing pivots' SR_hit and VAP, and 200 Part-B events' TURN flags, with plain loops;
- recomputes the headline rates from the saved tables.
