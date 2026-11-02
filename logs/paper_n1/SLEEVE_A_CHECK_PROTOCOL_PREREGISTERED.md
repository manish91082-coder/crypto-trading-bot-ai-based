# PAPER-N1 sleeve A live-vs-backtest consistency check: pre-registered protocol (2026-10-24)

Status: written and SHA-locked BEFORE any number of this check is computed.

## Why this check exists (honest selection note)

- This check was triggered by an observed live result, which makes it a post-hoc **consistency check**, not an edge test.
  - Ledger observed on 2026-10-24: sleeve A closed 72 trades, 2 wins, between 2026-10-21 04:00 and 2026-10-24 04:00 UTC.
- Whatever the result, **no live parameter, rule or code changes from this check alone.**
- The only possible outputs are:
  - "consistent";
  - "not consistent" → a separate investigation, which needs its own protocol.

## Data (SHA256 recorded by the script)

- **Live:** `data/paper_n1/ledger.jsonl`, a VM snapshot copied to `logs/paper_n1/sleeve_a_check/ledger_snapshot.jsonl`.
  - Records with T ≤ 2026-10-24 04:00:00 only.
- **Backtest:** `data/derived/n1/trades_K1.parquet`, sleeve == "A" (long only; CORE10; families 0–3; TF 4h/8h/12h/1D).
  - This is the ledger whose entries and exits the paper engine reproduced in the verified replay (`logs/paper_n1/verify_replay_stdout.txt`: P2 entry price match 1.0000, P3 exit time agreement 1.0000).
- **Market prices for the backtest:** `data/derived/n1/bars1h/<coin>.parquet` (1h open at a 4h boundary = 4h open).
- **Market prices for the live window:** the same source the paper engine uses: Binance spot `/api/v3/klines` 4h opens.

## Definitions

- **Live window** L = (2026-10-21 04:00, 2026-10-24 04:00] UTC, 72 h.
  - A live sleeve-A close belongs to L if its ledger record T is in L.
- **Trade return:** r = exit_px / entry_px − 1 (sleeve A is long; no fees, no funding).
  - Live: `px` / `entry` of the close action.
  - Backtest: `X` / `entry`.
  - **Win:** r > 0.
- **Backtest exit time** = entry_time + hold × TF hours (hold is in TF bars).
- **Backtest windows:** non-overlapping 72 h windows (s, s + 72 h] with s = 2020-03-01 04:00 + k·72 h, while s + 72 h ≤ 2025-09-01 00:00.
  - A trade belongs to a window if its exit time is in it.
  - **Eligible window:** at least 20 closed sleeve-A trades.
- **Market move** M of a window = equal-weight mean over the 10 CORE10 coins of open(end) / open(start) − 1 (4h opens). M_live is computed the same way from the live source.
- **Comparable set:** the eligible windows nearest to M_live by |M − M_live|.
  - Size: the nearest 20% of eligible windows, and at least 30.
  - Ties are broken by window start time.

## Tests

- **T1 (descriptive):** all sleeve-A backtest trades: win rate, mean r, median r.
- **T2 (the decision):** inside the comparable set:
  - p_wr = share of windows whose win rate ≤ the live win rate;
  - p_ret = share of windows whose mean r ≤ the live mean r.
  - **Consistent** if p_wr ≥ 0.05 AND p_ret ≥ 0.05; otherwise **not consistent**.
  - The same two shares over all eligible windows are reported as information only.
- **T3 (fidelity of the live records; a separate verifier)** checks every live sleeve-A close in L and the open it closes:
  - (a) entry px == the spot 4h open at the entry time and exit px == the spot 4h open at the close time (relative diff ≤ 1e-9);
  - (b) the signal state recomputed with `tf_edge_map.conditions` on independently fetched spot klines is 1 at the open cycle and 0 at the close cycle.
  - Gate: 100% of the checks pass. Any failure means "live records suspect" and overrides T2.
- **T4 (descriptive):** the live closes split by how their position was opened (`init` at the first cycle vs `signal`).

## Outputs

- `logs/paper_n1/sleeve_a_check/SLEEVE_A_CHECK_REPORT.json` (+ SHA file).
- The verifier's stdout.
- A Hindi summary appended to `logs/paper_n1/CODE_NOTES.md`.
