# PAPER-N1 sleeve A: forward investigation after the "not consistent" check. Pre-registered 2026-10-25

This protocol is SHA-locked before any number of the forward windows is computed. The first forward window ends 2026-10-27 04:00 UTC.

## Why

- The consistency check (`SLEEVE_A_CHECK_PROTOCOL_PREREGISTERED.md` 880ed986…, report 91296fca…) found **"not consistent"**.
  - **Window W1** = (2026-10-21 04:00, 2026-10-24 04:00]: 72 live sleeve-A closes, 2 wins.
  - **Results:** win rate 2.8% vs a comparable-window median of 28.1%, p_wr = 0.00. Mean return was typical: p_ret = 0.20.
- Its fidelity test T3 passed 100%. The live records are correct: the prices are the real spot opens, and every signal state is right.
- So the open question is whether W1 was an extreme draw, or whether live sleeve A really behaves unlike its backtest.
- W1 was the window that triggered the question, so it cannot answer it. Only **new, unseen windows** can.

## Data

- **Live:** `data/paper_n1/ledger.jsonl` on the VM. It is hash-chained and checked daily by `verify_paper_live.py`; its SHA is recorded at each evaluation.
- **Backtest window table:** `logs/paper_n1/sleeve_a_check/all_windows.csv`, SHA **65d62d4ee8d1e56539b46cfbd3d50436a8918c93b35f2427ceac85b96bca03ed**.
  - It was produced by the check and recomputed by plain loops in its verifier (V2 PASS).
  - It is used read-only, and its SHA is asserted.
- **Market move:** Binance spot `/api/v3/klines` 4h opens at each window's start and end, for the 10 CORE10 coins. Fetched on the VM and saved with SHA, the same source as the check.

## Forward windows

- F_k = (2026-10-24 04:00 + (k − 1)·72 h, 2026-10-24 04:00 + k·72 h], for k = 1 … 6.
- A window is **evaluated** once the ledger has a record with T ≥ its end. It is evaluated only once, and its result file is never rewritten.
- **Live trades of a window:** sleeve-A close actions in ledger records with T in F_k, with r = px / entry − 1 (exactly as in the check).
- **Eligible:** at least 20 live closes, the same threshold as the backtest windows. With fewer, the window is reported as "too few trades" and does not count.

## Test per eligible window (unchanged from the check)

- M_live = the equal-weight mean of the CORE10 open(end) / open(start) − 1.
- **Comparable set:**
  - the eligible backtest windows sorted by (|M − M_live|, start);
  - the nearest max(30, ceil(0.2 × 499)) = 100.
- p_wr = the share of comparable windows with win rate ≤ the live win rate; p_ret = the same for mean r.
- **consistent** if p_wr ≥ 0.05 and p_ret ≥ 0.05; otherwise **not consistent**.
- **Fidelity per window:** the check's T3 (prices == spot 4h opens; signal state 1 at the open and 0 at the close) on every close of the window. Any failure marks the window **records suspect**.

## Decision: on the first 3 eligible forward windows

| Outcome on the first 3 eligible windows | Verdict | Action |
|---|---|---|
| ≥ 2 "not consistent", or any "records suspect" | **confirmed inconsistent** | An ECO / PAPER-N1 amendment is written, pre-registered and verified to take sleeve A out of the N1 producer, with its own gate before deploy. Nothing changes automatically. |
| ≤ 1 "not consistent" | **W1 was an extreme draw** | The investigation is closed and nothing changes. |

- **Why 2 of 3:** if sleeve A matches its backtest, one window fails with probability ≤ 0.10 (two 5% tails), so 2 or more of 3 fail with probability ≤ 3 × 0.10² ≈ 0.03.
- **If fewer than 3 of F1 … F6 are eligible:** the verdict is "insufficient", and it is reported with the windows seen.

## Information only (not part of the decision)

- The W1 test repeated without the 30 `init` closes, i.e. with signal-opened closes only. This is post-hoc, so it is never a decision input.

## Code

- **`src/audits/sleeve_a_forward.py`** (VM, daily cron): evaluates every ended window not yet evaluated, writes `logs/paper_n1/sleeve_a_forward/F<k>.json` and `summary.json`, and runs the fidelity test.
- **`src/audits/verify_sleeve_a_check.py fidelity <ledger> <L0> <L1>`:** the existing T3 code with the window passed in. The defaults keep W1.
- **`src/audits/verify_sleeve_a_forward.py`:** an independent recompute by plain loops of each evaluated window (live n, win rate, mean r, M_live, comparable set, p_wr, p_ret, verdict) and of the summary.
