# PAPER-N1: code changes after the protocol lock

| Version | `paper_n1_portfolio.py` SHA | Used |
|---|---|---|
| v1 | fa7de42540c5… | VM forward cycles from 2026-10-21 (the original locked code) |
| v2 (amendment 1, 496d291a…) | 650fb08f81b8… | from the 2026-10-22 deploy |

## 1. Amendment 1 (2026-10-22)

**Changes:** catch-up of missed 4 h boundaries (cap 12), D close at the last mark when the price is missing, funding on the mark value, two-phase state / ledger write. A second cron line 15 min after the first.

**Tests:**
- `src/audits/test_producer_amend1.py` 4a755181f5d6…: P1–P3 + F1, 4/4 PASS.
  - The first P3 draft used a coin missing from the perp map, which raised a test-only KeyError. It now uses DOGE.
- **Replay 2025-06-01 … 2025-08-01**, old vs new code on the same laptop data:
  - 366 cycles; **all 7,312 actions identical**;
  - funding 35.2485 → 40.3342 USDT;
  - final equity 11,752.7629 → 11,747.6738.
  - The −5.0891 equity difference = −5.0857 funding − 0.0035. The residual comes from the July month-start E_m being 2.5 ppm lower (checked: June E_m and notionals identical; the July notional ratio is 0.9999974–0.9999975).

**Verifier.** `verify_paper_live.py` ce470311c392…: L3 accepts several code SHAs only when each is listed here.

## 2. Amendment 2 (2026-10-24): delisted and delisting coins

| Version | `paper_n1_portfolio.py` SHA | Used |
|---|---|---|
| v3 draft | 0e10d999fcc8… | never deployed: C3 found an inactive coin still requested in the liquid count |
| **v3 (amendment 2, 56dbbe1f…, + addendum 1, 922d6f95…)** | **621238aff5fa…** | from the 2026-10-24 deploy |

**Changes:**
- A daily exchangeInfo check builds two lists:
  - inactive = spot not TRADING;
  - perp_out = perp missing, not TRADING, or deliveryDate < 2100.
- Inactive coins are not requested at all, including in sleeve C's liquid count. Their positions are closed at the last mark.
- perp_out coins get no opens; their perp positions are closed at the open; their spot positions are kept.
- The rule is off in replay.
- Every record carries `delisting`.

**Checks:**
- **C1 replay** 2025-06-01 … 2025-08-01: v2 vs v3. 366 cycles; all 7,312 actions identical; equity difference 0.0; only `delisting` differs. Done for the draft and again for the final code (`amend2_C1_replay_result.txt`).
- **C2:** `src/audits/test_paper_amend2.py` b41b56ee5bf8…, 4/4 PASS (`test_paper_amend2_stdout.txt`).
  - **Negative control:** with the rule disabled, C2a and C2b FAIL.
  - The strengthened C2a FAILED on the draft 0e10d999… and PASSES on 621238af….
- **C3 VM sandbox:** the cycle 2026-10-24 08:00 was re-run from the 04:00 state taken from the Drive bundle (ledger = live prefix).
  - `data_errors` [] vs live [SXP 400].
  - Lists: 27 inactive + 2 perp_out, equal to an independent exchangeInfo read; no held coin in them.
  - Actions equal except 9 new C opens, whose notional is 23/22 larger (addendum 1: nliq no longer counts an untradeable coin).
  - Equity +0.0024, which is the fee.

**Live verification (2026-10-24 12:11 UTC, first cycle on 621238af…):**
- cron exit 0; the 12:26 retry skipped idempotently (exit 0).
- Record T 12:00: `data_errors` [] (the previous cycle on the old code had [SXP 400]).
- Requests 720 vs 827.
- `delisting` {day 2026-10-24, 27 inactive, perp_out [FTTUSDT, RAYUSDT]}; 0 delist closes, since no held coin is listed.
- `verify_paper_live.py`: L1–L5 5/5 PASS. L3 lists the code SHAs 621238af / 650fb08f / fa7de425, all recorded here.
## 2026-10-25: sleeve A forward investigation (protocol `SLEEVE_A_FORWARD_PROTOCOL_PREREGISTERED.md` 531cd10cab8d…, locked 04:33:37 UTC)

**Code (written after the lock):**
- aab5aade4ec0  sleeve_a_forward.py
- ed8c4e7927a1  verify_sleeve_a_forward.py
- 563b41c2da4f  verify_sleeve_a_check.py
- aaf9571d16db  crontab_sleevea.txt
- `verify_sleeve_a_check.py` only gained the optional `<L0> <L1>` arguments for `fidelity`; its default window is unchanged.

**Known-answer pre-flight on the VM (04:39 UTC):**
- A temporary copy pointed at W1 (F0 = 2026-10-21 04:00) with its output in /tmp. It reproduced the recorded check exactly:
  - n 72, wins 2;
  - M_live −0.036398377095961255;
  - comparable 100, p_wr 0.0, p_ret 0.2 → not consistent.
- T3 fidelity 2/2 PASS; verifier Q1–Q3 3/3 PASS.
- A second run left F1.json byte-unchanged (idempotent). The temporary copies were deleted.

**Information only (post-hoc, never a decision input):**
- W1 without the 30 `init` closes: 42 closes, 2 wins.
- Win rate 4.8%, mean r −2.82%; p_wr 0.02, p_ret 0.18.

**Crontab:** `deploy/crontab_sleevea.txt` = the current crontab + 2 lines: 10:05 IST daily, job SleeveA_Forward, then its verifier.
- The first forward window F1 ends 2026-10-27 04:00 UTC and is evaluated on 2026-10-27 at 10:05 IST.
## 2026-10-25: fee unification (logs/fees/FEE_AMENDMENT_PREREGISTERED.md (2d9d1485…))

- `src/execution/paper_n1_portfolio.py` **d5f0f82f115f…**:
  - FEE (perp) 0.00054 → **0.00046** (BNB taker 0.036% + impact 0.010%);
  - FEE_SPOT 0.00085 is unchanged (BNB 0.075% + impact 0.010%);
  - an assert ties both to `deploy/fees.json`.
- New opens use the new fee. Open positions close with the fee stored when they opened. No ledger line is rewritten.