# PAPER-N1 code notes

1. **Replay run 1 (2026-10-21): naming bug in the replay harness.**
   - **Result of run 1:** P2 passed only at the edge (0.9502), and D leg sets agreed in 9/40 rebalances.
   - **Diagnosis:** 520 of the 604 missing C entries were SHIBUSDT and BONKUSDT. Their perps are 1000SHIBUSDT and 1000BONKUSDT, but the research files are named by the spot symbol (`SHIBUSDT_perp_1h.csv.gz`, `SHIBUSDT_funding.csv`). The replay source therefore found no perp volume, treated both coins as illiquid, and the D quintile size q dropped (12 legs instead of 14).
   - **Scope:** the live source queries Binance by the perp name, so the live path is not affected.
   - **Fix:** the replay source maps perp name → research name (`RCOIN`) for file lookups.
   - **Rerun:** the replay was rerun. Run 1's ledger and verifier output are kept as `replay_run1_naming_bug/` and `verify_replay_stdout_run1.txt`.

2. **Init per TF (2026-10-21, after the first VM test cycle).** The first VM cycle (04:00 UTC) opened only the 4h sub-signals that were already "on". The 8h, 12h and 1D sub-signals were not evaluated in that cycle, and the old rule allowed `init` only in the very first cycle. So they would have waited for a fresh flip, which contradicts the protocol ("sub-signals already on are opened").
   - **Fix:** `init` now applies at the first evaluation of each TF (`state.init_tfs`).
   - **Check:** a one-month replay (2025-03-01 … 2025-04-01) must give the same `signal` entries as the gated replay; only `init` entries may differ.
   - **On the VM:** the test cycle's directory is kept as `data/paper_n1_test_cycle_20261021`, and the recorder restarts fresh with the fixed code.

3. **Sleeve A live-vs-backtest consistency check (2026-10-24; protocol 880ed986…, locked before any result).**
   - Code: `src/audits/sleeve_a_check.py` 12539548…; independent verifier `src/audits/verify_sleeve_a_check.py` 39d975fb….
   - Report: `logs/paper_n1/sleeve_a_check/SLEEVE_A_CHECK_REPORT.json` 91296fca….
   - Inputs (SHA in the report):
     - live ledger snapshot f3fcd4ba… (VM, T ≤ 2026-10-24 04:00);
     - spot 4h opens fetched on the VM (bf2defeb…), because the laptop cannot reach api.binance.com;
     - backtest trades_K1 df4e3c05….
   - **Live (L = 21-10 04:00 … 24-10 04:00):**
     - 72 sleeve A closes, 2 wins (2.8%), mean trade return −2.75%, worst −8.43%, best +1.14%;
     - market move of CORE10 over L: −3.64%.
   - **Backtest T1:** 26,926 trades, win rate 35.7%, mean +3.75%, median −1.08%. It is a trend sleeve: many small losses and a few large wins.
   - **T2:** the 100 nearest comparable 72 h windows (market −5.5% … −1.8%):
     - median win rate 28.1%, median mean return −0.49%;
     - **p_wr = 0.00** (the lowest comparable win rate is 3.7%); p_ret = 0.20.
   - **Verdict, by the pre-registered rule: NOT CONSISTENT** (on the win rate). The size of the loss per trade is within the normal range for such a market.
   - **T3 (verifier on the VM, bars fetched independently):**
     - 72/72 entry and exit prices == spot 4h opens;
     - 72/72 signal states correct (1 at the open, 0 at the close).
     - The live records and the engine are correct; the result is not a data or code fault.
   - **T4 (descriptive only):** 30 of the 72 closes were `init` positions (opened mid-trend at the start; 0 wins), and 42 were fresh signals (2 wins, 4.8%). The backtest has no `init` trades. This is a hypothesis for the investigation, NOT a finding.
   - **Action:** per the protocol, no live change. A separate investigation, with its own protocol, is to test the init effect and the clustering of correlated exits.
   - Verifier outputs: `verify_recompute_stdout.txt` (V1–V3 PASS) and `verify_fidelity_stdout.txt` (T3a/T3b PASS).
