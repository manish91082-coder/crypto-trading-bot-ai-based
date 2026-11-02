# F4: changes after the protocol lock

## 1. Daily pending-orders file (2026-10-15 ~16:00 UTC, BEFORE the first scheduled run; no forward result exists)
- **Why:** the F6 testnet executor needs the decision taken at the close of each as-of day, i.e. what to open / close at the next open. The paper equity and positions files only show the book up to the close.
- **Engine change (`f7_risk.py`):**
  - `sim_ls` now also RETURNS `pending`. It holds the last bar's decision lists (sell / buy / cover / short), the open book before the end-of-test close (long units; short units, entry, stop) and the cooldown map.
  - No computation changed. Re-check: the F7 RS D1 sleeve re-run gives $103,663.98 and 66 stops, equal to `strategy_f7_risk/claims.json`.
- **Logger change (`forward_ls_f4.py`):** writes `paper/orders_{asof}.json` (per line and sleeve: pending + close equity) and records `orders_sha256` in the ledger line.
- **Verifier change:** V1 also checks the orders-file hash.
- **Gates, lines, rules and schedule are unchanged.**

## 2. 2026-10-16 ~00:20 IST: BUG FIX before the first scheduled run (found by the audit's sandbox pre-flight)
- **Bug:** `L16.asof == ...` in `main()`. `.asof` is the pandas DataFrame METHOD `asof`, not the column. The comparison was always False, so the first scheduled run (as-of 2026-10-15, 08:30 IST) would have FAILED with "16B has not logged …".
- **Fix:** `L16["asof"]`. The same bug in `verify_f4_forward.py` (`L.asof.iloc[-1]`) and in `futures_testnet_f6.py` (`r.asof` on a Series) is fixed the same way.
- **Also added:** `main(asof=None)`. The optional argument is used ONLY by the sandbox pre-flight (`src/audits/preflight_f4.py`); the scheduled run passes nothing.
- **Pre-flight evidence:**
  - Two sandbox days (as-of 2026-10-13 / 10-14; temp folder, live data, 16B test signals, day 1 shifted) ran without error.
  - Chain OK; C1 True on both days (LO = 16B paper); orders file written.
  - `verify_f4_forward.py` on the sandbox: V1–V5 PASS.
- **Unchanged:** nothing in `logs/forward_ls_f4` was written by the pre-flight, and no gate, line or rule changed.

## 3. 2026-10-16: wait for 16B; verifier handles an empty positions file
- **What happened:** the first scheduled run (10:20 IST, after a late wake) failed with "16B ledger missing", because 16B itself had failed (see 16B CODE_CHANGES 4–5).
- **Recovery:** both were re-run by hand at about 12:08 IST. The as-of 2026-10-15 line is LATE (`on_time=False`), C1 True. `verify_f4_forward.py`: V1–V5 PASS.
- **Fix:** `main()` now checks every 60 s, for up to 90 minutes, for the 16B ledger line of the as-of day.
- **Verifier:** V5 reads the PAPER_START positions file, which is empty because nothing is filled yet, as an empty table instead of crashing.

## 2026-10-16 (E2E integration test finding): verifier V1b added (verifier only; logger unchanged)
- Gap: V1 checked the ledger line hash and the equity file hash, but not that the ledger numbers LS_RS / LS_F2 / LO equal
  the last M_AI3 of the equity file. A line re-hashed after a changed number would have passed.
- V1b: |round(equity file M_AI3 last, 2) - ledger value| < 0.005 for all three lines, every day. First run on the real
  ledger: PASS. The E2E test D1b checks that a re-hashed changed number is now rejected.
- Verifier SHA: 412eea96d23e54aa9ea2ba79b45136b7b8aa8495fa570142b476d6e5137c0dbb  src/audits/verify_f4_forward.py

## 2026-10-16: E11 shadow line hook (user's yes; Round 1 E11 PASS)
- After writing its own ledger line, F4 calls `shadow_e11_f4.main(asof)` inside try/except, only when LOG is the real
  logs/forward_ls_f4 folder (never in a sandbox). A shadow failure is logged and never changes the F4 ledger, paper
  files or numbers. Nothing else in F4 changed. Shadow protocol: logs/forward_ls_f4/shadow_e11/E11_SHADOW_PROTOCOL.md
  (SHA 90deba31..., locked 2026-10-16T14:59:46Z); shadow code SHA 949012c65020dc8b5505b8a01d6f56a0592b99c1b3f9f04b013d9a77e270acb5.
- Checks before tomorrow's run: F4 sandbox preflight PASS with the hook (real shadow folder untouched); shadow sandbox
  preflight PASS (C0 True, verifier V1-V3 PASS, negative test: changed perp files refused); real as-of 2026-10-15 shadow
  line written (flat PAPER_START day) and verified; verify_f4_forward V1-V5 PASS.
- F4 code SHA: c0ede7a02bae8702cb5e27448c0de7d34654af4af5e9ab39e1a61f6ea66dc15a  src/execution/forward_ls_f4.py

## 2026-10-17: every trade written to a file (user request; output only)
- F4 now also writes paper/trades_<asof>.csv (every trade since PAPER_START: line, sleeve, side, symbol, entry / exit
  time, reason, cost, pnl, funding, prices); the E11 shadow writes shadow_e11/trades_<asof>.csv (with venue). Numbers,
  ledger columns and hashes are unchanged; the files are copied and SHA-recorded daily by the M10 backup manifest.
- Sandbox preflights PASS (F4 two days; shadow: C0 True, verifier V1-V3 PASS).
- F4 code SHA: d9ffb46016ec169f5f179af6d9e30d46fefc6c5b091de7e25aa8f76eb6250dd4; shadow code SHA: 1a5d91496f2af6946ced8d7e03fd32601dde4231840f7f037ac07acb4d013c0c

## 2026-10-17: run time moved to 07:45 / 08:15 IST (operational; first cloud day finding)
- The protocol states the run time "08:30 and 09:00 IST" AND the on-time rule "written <= as-of + 1 day 03:00 UTC"
  (= 08:30 IST). Both cannot hold: a run that STARTS at the deadline always finishes after it. On the first cloud day
  (as-of 2026-10-16) F4 started 03:00:01 UTC and wrote its line at 03:00:44 UTC -> on_time=False by 44 seconds.
  The same conflict existed on the Windows schedule; the as-of 2026-10-15 lateness was attributed only to the PC sleep,
  which was incomplete.
- The on-time RULE (the D1 gate) is unchanged; only the clock time moves: 07:45 IST (16B finishes about 07:31) with a
  retry at 08:15 IST. F4 already waits up to 90 minutes for the 16B line.
- Late days so far: as-of 2026-10-15 and 2026-10-16 (2 of the 5 allowed by D1 >= 85 of 90).

## Amendment 1 (2026-10-22, `F4_AMENDMENT_1_PREREGISTERED.md` 84dba18d…)

**Change.** `forward_ls_f4.py` d9ffb46016ec… → **91f46e59b3e9…** (the file is now saved with LF line endings). The skip check reads the ledger row (`already_logged`), not the equity file. An equity file without a ledger row logs a note and is recomputed.

**Bug caught by the unit test before deploy.** The first draft used `pd.read_csv(ledger).asof`, which is the DataFrame method. It is now `["asof"]` (the known pandas gotcha).

**Unit test.** F1 PASS (`src/audits/test_producer_amend1.py`).

**Forward check.** The next scheduled run (2026-10-23 02:15 UTC) must log as-of 2026-10-22 as usual.

## 2026-10-25: fee amendment 2 (`logs/fees/FEE_AMENDMENT_2_1D_RECORDERS_PREREGISTERED.md` a111c707…)

- `src/execution/forward_ls_f4.py` code SHA **aeb1a80c8ac4de994ae2ba11323c1eb20fda7ab39a98210af49283393d1f1dc6**: on import it sets `F2R.C_LONG` 0.0025 → **0.00085** and `F2R.C_SHORT` 0.0010 → **0.00046** from `deploy/fees.json`.
  - This covers every line (LS_RS, LS_F2, LO) and the E11 shadow, which imports this module.
  - Stop slippage stays at 1%. `f2_run.py` is not edited.
- **D3 reference (day 90)** → `logs/research_1d_true_fee/equity_MAIN_AI_R1_RS.csv` SHA dfb464db9c962da1bcaafe1582c6a0a9d45f2e81ed3ceae6d64a7be9435144c0 (F7 RS at the true fee; verifier 3/3 PASS). D1 and D2 are unchanged.
- **Effective:** as-of 2026-10-25 (run of 2026-10-26 07:45 IST); a one-time level jump, as in 16B.
- C1 keeps holding: the long fill is 0.00085 in both 16B and F4.
- **Test K3 harness:** `src/audits/k3_fee2_check.py` bc3cdc7335a4….