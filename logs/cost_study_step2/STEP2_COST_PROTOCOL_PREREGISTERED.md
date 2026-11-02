# Step 2: real trading cost from the public Binance order book (pre-registered)

Locked before any snapshot is analysed. Code: `src/execution/cost_snapshot_step2.py`. Analysis: `src/research/cost_study_step2_analyse.py`.

**Scope:** NO ORDERS. No account, no testnet, no GitHub. Only `GET /api/v3/depth` (public).

## Why not the testnet
- The testnet order book is synthetic and thin, and it is not the market where real orders would fill. Its spread and slippage say nothing about mainnet.
- The mainnet public book gives real bid/ask/size for free.
- The testnet ETH position and its stop order stay untouched.

## Measurement
**Universe:** the symbols of the latest Step 16B day (D1 + R6 + R24 members) plus BTCUSDT, about 20–25 coins.

**One round** = for each coin, one depth snapshot (limit 1000). The raw JSON is gzip-saved and its SHA256 is logged.

**Per coin:**
- mid, half-spread (bps);
- USD depth within ±1 %;
- for notionals $100, $333, $1,000, $3,333, $10,000 and $30,000: the market-buy and market-sell cost vs mid (bps), by walking the real book.

**Schedule:**
- Windows task `CryptoBot_Step2_CostSnapshot`, 05:28 and 05:32 IST (23:58 and 00:02 UTC). This is around the 00:00 UTC rebalance, where all four brains fill.
- Off-schedule rounds (`--now`) are kept but tagged, and are reported separately.

## Cost model under test
- The research used **0.25 % per fill**.
- Real per-fill cost = exchange fee + half-spread + book impact for the order size.
- Fee from the official Binance page:
  - 0.100 %, or 0.075 % with BNB, for VIP 0;
  - two variants are reported.
- Order size in the 50 % setup with $10,000: each position ≈ $10,000 × 0.5 / 3 / 5 ≈ **$333**. $1,000 and above are reported for growth.

## Analysis (after ≥ 30 scheduled rounds, about 15 days; run once, then repeated monthly)
- Per coin and notional:
  - median and p90 of (half-spread + impact), buy and sell;
  - the share of rounds where the book was too thin (NaN).
- **Estimated per-fill cost** = fee + median (buy, sell) impact at $333; the same at $1,000, $3,333 and $10,000. Shown per coin and as the universe median and p90.
- **Verdict per notional (fixed now):**
  - **"0.25 % is conservative"** if the universe p90 per-fill cost (fee 0.100 %) is ≤ 0.25 %;
  - **"0.25 % is too low"** if the universe MEDIAN is > 0.25 %;
  - otherwise **"borderline"**.
  - If "too low", the research portfolios are re-costed at the measured value. The 0.40 % stress runs already exist for R6 / R24 / D1.
- **Limits stated now:**
  - The depth snapshot is not a fill. Hidden liquidity and latency are not seen.
  - The book can change within seconds around 00:00, so the 23:58 and 00:02 rounds are compared.
  - A real small-order test on mainnet is the user's decision and is not part of this step.
