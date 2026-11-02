# F6: futures TESTNET executor for the long-short short book: operations test (pre-registered)

- Code: `src/execution/futures_testnet_f6.py`
- Verifier: `src/audits/verify_f6_testnet.py`

**Purpose:** operations only. Do orders, stops, reconciliation and the kill switch work on Binance's no-money futures environments? It is NOT a performance test; 2–3 days prove nothing about profit.

## Hard safety rules (in code, asserted)
1. **Base URLs.** Only the official non-money hosts, verified on 2026-10-15 from three sources (the Binance SDK constants in `@binance/common`, ccxt 4.5.85 `urls.test` / `urls.demo`, and a live ping):
   - `testnet` = https://testnet.binancefuture.com
   - `demo` = https://demo-fapi.binance.com

   There is NO mainnet mode. The code refuses any other host.
2. **Keys.** From environment variables set by the user only:
   - BINANCE_FUT_TESTNET_KEY / _SECRET, or
   - BINANCE_FUT_DEMO_KEY / _SECRET.

   Claude never types, stores or prints a key.
3. **One-way position mode only.** If the account is in hedge mode, the run stops and asks the user. The code does not change account settings.
4. **Every symbol:** isolated margin, leverage 1, set before the first order.
5. **Shorts:** MARKET SELL to open; MARKET BUY reduceOnly to close.
6. **Stops.** Every open short gets a protective STOP_MARKET BUY, reduceOnly, at fill × 1.50 (the F7 rule). It is placed through `POST /fapi/v1/algoOrder` (algoType=CONDITIONAL, triggerPrice, workingType=CONTRACT_PRICE).
   - Since 2025-12-09 Binance rejects conditional orders on `/fapi/v1/order` (error -4120). Sources: the Binance changelog and the official SDK.
7. **Limits:**
   - at most 40 orders per run;
   - one order's notional ≤ 25 % of a sleeve's testnet capital;
   - at most 15 open shorts.
8. **Kill switch K1:**
   - If the account equity is ≤ 65 % of its recorded peak, then: cover everything, cancel every algo order, and write `HALT`.
   - Later runs refuse to trade until the user deletes `HALT`.
   - A `--drill-kill` run tests it on purpose.
9. **plan mode** (no keys): reads the same inputs and prints the rounded orders it WOULD send. Nothing is sent.

## What it executes
- **Source:** the F4 paper log's LS_RS line. The decision of the as-of day is read from `logs/forward_ls_f4/paper/orders_{asof}.json`; its SHA256 must equal the F4 ledger line.
- **Sleeves:** D1, H4 and H1 are kept separately in the state file. Each has its own testnet capital `CAP_SLEEVE` (default 1,000 USDT, set by the user). In one-way mode the exchange position is the sum of the sleeves.
- **Target per sleeve:** the paper short book after the pending decision (the open shorts − covers + new shorts).
- **Size of a new short:** 10 % × CAP_SLEEVE × (paper sleeve equity / 10,000). The quantity is rounded down to the step size. An order below the exchange minimum notional, or for a coin not listed on the environment, is skipped and logged with its reason.
- **Each run:**
  1. Sync: a sleeve short whose stop algo order is no longer open is checked with `GET /fapi/v1/algoOrder`. If it was triggered, it is closed in the state.
  2. Close what is not in the target.
  3. Open what is missing.
  4. Place stops.
  5. Reconcile.
  6. Ledger line.

## Operations checks (the test passes only if all hold on each of ≥ 2 consecutive runs)
| Check | Condition |
|---|---|
| O1 | Every intended action has an exchange acknowledgement or a logged skip reason |
| O2 | Every open sleeve short has exactly one open STOP_MARKET algo order. Its quantity equals the sleeve quantity, and its trigger equals fill × 1.50 (tick-rounded), re-read from the API. |
| O3 | Reconciliation: the exchange position amount per symbol = −(sum of the sleeve quantities in the state), within one step size |
| O4 | One `--drill-kill` run leaves zero positions and zero open algo orders (re-read from the API) |

**Reported:** the fill price vs the paper reference (the perp open of the decision fill bar), in bps; and the run duration.

**Decision:** only "operations ready / not ready". Nothing about money.
