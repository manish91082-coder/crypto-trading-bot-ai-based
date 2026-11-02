# GEMV: ground check of the Gemini notebook's fill / label model (pre-registered 2026-10-20, before any result)

## Question
The Gemini notebook (`full_ai_crypto_bot_trading_gemini_19_oct_26.ipynb`, Step 11.R2 cell) reports "+9.06%, PF 1.94, all 7 gates passed". Its trade P&L comes from the label function `evaluate_real_candle_path` plus a "GTX maker pullback" entry:
- **Long:** entry = max(low[i+1], close[i] − 0.18·R) if low[i+1] ≤ close[i], else close[i].
- **Short:** mirror.
- The path is evaluated from bar i+1, including that same bar's high and low.

Hypothesis:
- This assumes a fill at, or better than, the next bar's extreme.
- It also credits targets that bar i+1 may have reached before the fill.

We measure how much this inflates R on our verified data, over years instead of the notebook's ~41 days.

We do **not** run the notebook. It is untrusted downloaded code, and its Drive cleanup moves and trashes files across the user's whole Drive. The path logic is re-implemented from the code text, line for line.

## Data
- `data/universe_hf/5m` (SHA-verified), resampled to 1h (left-closed, UTC).
- Core10 coins.
- Bars from 2021-01-01 to 2026-09-30.

## Indicators (as in the notebook)
- ATR14 = EWM(alpha = 1/14) of the true range.
- natr = ATR / close, clipped to [0.002, 0.15].
- sl_pct = clip(1.15 · natr, 0.005, 0.022).
- R = close[i] · sl_pct.
- Horizon: 20 bars.
- Costs: c_maker_rt = 0.00051; c_sl_rt = 0.00085.

The path function is the notebook's:
- SL first;
- break-even at +0.70R → SL to +0.15R;
- TP1 35% at 1.2R (SL → +0.25R);
- TP2 35% at 2.3R (SL → +1.25R);
- TP3 at 3.6R;
- trail = extreme − 0.95R once favourable ≥ 1.35R;
- time exit at the last close minus maker friction.

## Fill models, for every bar i (long and short)
- **A (notebook, verbatim):** entry as above; path bars i+1 … i+20.
- **B (limit, realistic):**
  - limit = close[i] ∓ 0.18·R. Filled only if bar i+1 trades through it (low ≤ limit for longs, high ≥ limit for shorts), at the limit price.
  - Inside bar i+1 only the adverse side counts after the fill: stopped if low[i+1] ≤ limit − R (longs). Otherwise the path continues on bars i+2 … i+20.
  - Not filled = no trade.
- **C (taker at next open):** entry = open[i+1]; path bars i+1 … i+20. Taker-entry friction is added: (0.00045 − 0.00018) / sl_pct R.

## Report
Per model and side:
- n;
- fill rate (B);
- mean R, median R;
- the share of r > 0.10 (the notebook's label = 1).

Also:
- the mean R by year;
- the paired difference A − B on the bars that B filled (same bars).

The reading is descriptive. **"A inflates R"** if the paired mean A − B > 0 with a block-bootstrap (calendar month) 95% CI above 0.

## Verifier (`src/audits/verify_gemv.py`, own code)
- 200 random (coin, bar, side, model) rows recomputed with an own path implementation, within 1e-12.
- Aggregates recomputed from the row file.
- SHAs.
