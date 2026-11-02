# F4: long-short PAPER forward log (pre-registered)

Locked on 2026-10-15, before the first decision of PAPER_START is taken. The as-of day 2026-10-15 closes at 2026-10-16 00:00 UTC.
- Code: `src/execution/forward_ls_f4.py`
- Verifier: `src/audits/verify_f4_forward.py`

**NO ORDERS. No API keys. No account.** Only public Binance market-data endpoints are used. No GitHub.

## Signals (read only)
- The Step 16B forward files `logs/forward_multi_16b/predictions/{d1,h4_r6,h1_r24}_{date}.csv`: the same brains and scores as the spot paper log.
- F4 never writes into the 16B folder.
- Each file's SHA256 is recorded and must equal the hash in the 16B ledger line of that day.
- A missing day is carried from the previous day, the 16B rule (`load_scores`).

## Perpetual data (public, no key)
- **Sources:** `fapi.binance.com/fapi/v1/klines` (1h) and `/fapi/v1/fundingRate`.
- **Storage:** `data/forward_f4/perp/`.
- **Coins:** every coin in the 16B files.
- **Perp name:** from `logs/futures_um_download/perp_names.csv`. A coin not listed there is looked up in `/fapi/v1/exchangeInfo` (SYM, then 1000SYM, then 1000000SYM; status TRADING). A "1000" perp is divided by 1000.
- **Window:** from PAPER_START − 7 days to the as-of day 23:00 UTC.
- **Overlap check:** each run re-downloads the last 48 stored hours. Any change in a stored value is written to the run notes and the ledger; it is not silently replaced.
- **Forward scale gate:** a coin is shortable on a day only if the median of perp close / spot close over the common hours of the previous 7 days (≥ 24 hours) lies in [0.98, 1.02]. Spot comes from the 16B live 1h folder.

## Paper portfolio
- **PAPER_START** = 2026-10-15, the same as 16B.
- **Sleeves:** D1, H4 and H1, each $10,000. The mix (M_AI3) is the mean of the three. This is exactly the research and F7 setup:
  - top-5 long on spot, 50 % of equity, 0.25 % per fill;
  - bottom-5 short on the perp, 50 %, 1x isolated, 0.10 % per fill;
  - funding settles in the isolated margin;
  - rebalance as in research: D1 every 5 days, H4 at the 20:00 bar, H1 at the 23:00 bar.
- **Lines:**

  | Line | Engine and rules |
  |---|---|
  | **LS_RS** (primary) | `f7_risk.sim_ls` with the F7 rules: stop ×1.50 (+1 % slippage), 30-day cooldown |
  | LS_F2 (shadow) | No rules |
  | LO (check line) | invest_short = 0 |

- **Daily integrity check C1:** the LO line must equal the 16B paper sleeve equity of the same day within $0.01. The engine was verified to reproduce the research simulators (F2 G0, F7 G0). A mismatch is logged as **C1_FAIL**; the day's LS numbers are then marked untrusted.

## Ledger
- `logs/forward_ls_f4/ledger.csv`, hash-chained like 16B (prev_sha256, line_sha256).
- Each line records: the 16B file hashes, the perp-file hashes, the code hash, the protocol hash, the three lines' mix equity, C1, on_time (written ≤ as-of + 1 day 03:00 UTC) and notes.

## Schedule
Windows task `CryptoBot_F4_LSPaper`, daily at 08:30 and 09:00 IST, after the 16B task (07:30 and 08:00). A second run on a day that is already logged does nothing.

## Decision at day 90 (as-of 2027-01-12; judged after it is logged)
Gates D1–D3 must all hold for "LS may go to a small real-money pilot, the user's decision":

| Gate | Condition |
|---|---|
| D1 | ≥ 85 of 90 days logged on time; hash chain intact; C1 passed on every logged day |
| D2 | Max drawdown of the LS_RS mix over the 90 days ≤ 30 % |
| D3 | LS_RS 90-day return ≥ the 5th percentile of all rolling 90-day returns of the F7 backtest RS mix (`logs/strategy_f7_risk/equity_MAIN_AI_RS.csv`, M_AI3, 2021–26). This asks "is live consistent with the backtest?"; it cannot prove skill. |

- **Reported, no gate:** the number of stops; real stop slippage cannot be measured on paper (it is fixed at 1 % here). It is measured only in the F6 testnet and the pilot.
- If any gate fails: no real-money futures. The report states why.
- 90 days is too short to prove an edge statistically. This is stated now.
