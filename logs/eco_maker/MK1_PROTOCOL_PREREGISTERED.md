# MK1: would limit (maker) orders with a market fallback have been cheaper than ECO's market orders? Forward, on ECO DEMO's own orders. Locked 2026-10-26

## Why
- ECO DEMO sends **MARKET** orders (`src/eco/eco_exchange.py`, type="MARKET").
- The cost of a market order is the taker fee plus slippage. The first tracking day (2026-10-25) showed a slippage of 2.37 bps.
- A limit order at the decision mark pays the maker fee instead, but it may not fill. The study measures what the fill rate and the fallback cost would have been.
- **This changes nothing in ECO.** It is a measurement; a switch would need its own ECO amendment.

## Sample
- **Orders:** every order in `data/eco_demo/ledger.jsonl` records with ok = true, from the cut-over (2026-10-25 04:21 UTC) onward. This includes future records.
- **Per order:**
  - T = the cycle time (UTC);
  - perp, side = sign(qty), notional = |qty| × m;
  - m = `price[perp]` (the decision mark);
  - f = `px` (the actual demo fill price).
- **Price data:** 1m futures klines of each order's symbol (`data/futures/um/daily/klines/<SYM>/1m/`, data.binance.vision), checksum-verified, fetched once the day is published.

## Costs (all from `deploy/fees.json`), in bps
- **demo column:** taker = `demo_account_charged_taker` (4.0); maker = `futures_usdm.base_maker` (2.0), because the demo account holds no BNB.
- **real column:** taker = `bnb_taker` (3.6); maker = `bnb_maker` (1.8).

## Policies (cost of an order, bps, positive = worse, relative to the mark m)

**MKT (what happened):** side × (f / m − 1) × 1e4 + taker.

**LIM(W), W ∈ {5, 15} min (the primary is W = 15):**
- A buy (sell) limit at m.
- **Filled** if a 1m bar with open time in [T + 1 min, T + W) has low < m (high > m), i.e. a trade-through. The first minute is skipped because the order is sent a few seconds after T.
- **If filled:** the cost is the maker fee.
- **If not filled:** a market fallback at the close of the 1m bar opening at T + W − 1 min.
  - cost = side × (that close / m − 1) × 1e4 + side × (f / m − 1) × 1e4 + taker.
  - The second term charges the order's own observed slippage again, as an estimate of the fallback's slippage.

**Δ(W)** = LIM(W) − MKT. A negative Δ means the limit policy would have been cheaper.

## Reported (daily, cumulative)
- n orders, fill rate;
- the notional-weighted mean MKT, LIM and Δ for both columns;
- the weekly-cluster 95% CI of the notional-weighted mean Δ;
- the per-symbol fill rate.

## Decision (one time)
- **When:** after ≥ 300 orders.
- **The finding** "limit-with-fallback is cheaper" needs **both:**
  1. the notional-weighted mean Δ(15) < 0 in the real column;
  2. the weekly-cluster 95% upper bound of Δ(15) < 0.
- **If it holds:** draft an ECO amendment (a new protocol), which the user decides on.
- **Otherwise:** keep MARKET.
- No other decision is taken from MK1.

## Limits (stated now)
- A trade-through fill assumes our order would have been filled once the price traded beyond it. Queue position is ignored; for small orders this is a mild assumption.
- Fallback slippage is estimated by the order's own observed slippage.
- Delaying an order up to 15 min also changes the position path. That P&L effect is not part of the cost measure.
- It is a known omission; it is small at ECO's hourly-rebalance horizon, but not zero.

## Code
- `src/eco_maker/mk1.py`;
- verifier `src/audits/verify_mk1.py` (independent).
- **Output:** `data/eco_maker/` on the VM.
- **Schedule:** daily, after Binance publishes the 1m files.
