# ECO: changes after the protocol lock (15a3c837…)

## 1. `src/research/eco_e1_e2.py`: CODE_NOTES path (2026-10-22, before the official run)

- **What happened:** the scratch smoke run crashed while writing the claims. `notes_sha` read `CODE_NOTES.md` from the output folder, which is the scratch override, instead of `logs/eco`.
- **Fix:** read it from the lock folder.
- **Effect:** none on the numbers. The smoke had reproduced E-1 exactly and stopped before E-2 printed anything, so no E-2 number was seen before the official run.
- **Also added before the official run:** the N1 FINAL curves of the N6 windows are saved, so verifier V1 can recompute them independently.

## 2. Account scale k: measured every cycle, applied per month (protocol §3 said "measured each cycle")

- **What changes:** k is measured every cycle in demo mode and logged as `k_now`. The value applied to targets, k_m, is fixed at the first cycle of the month, together with E_m.
- **Why:** if k changed every cycle, every symbol would get small rebalancing trades every hour, purely because the demo wallet moves. The resulting churn would be a cost the protocol never intended.
- **Where it applies:** this matters only in demo, where the wallet ≠ 10,000. On a 10,000 USDT account k = 1.

## 3. Live weights for the adopted ECO-W2 (inverse volatility, protocol §5)

**Rule.** At the first cycle of each month: a_1D = clip((1/σ_1D) / (1/σ_1D + 1/σ_N1), 0.2, 0.8), a_N1 = 1 − a_1D. Here σ is the std of the last 126 daily returns available before the month.

**Return history:**
1. **Backtest returns.** These are exactly the E-2 inputs:
   - 1D: `equity_MAIN_AI_RS.csv` M_AI3, 2021-01-02 … 2026-09-30.
   - N1: the N1 FINAL dev and P3 runs, with returns taken per run.

   They are frozen in `deploy/eco_history_daily_returns.csv`, whose SHA is in the config. (Path corrected 2026-10-22; the first text said `data/eco/…`.)
2. **Forward paper returns, appended after the backtest.**
   - 1D: the F4 ledger column `LS_RS` (the M_AI3 mix) between consecutive as-of days.
   - N1: the PAPER-N1 ledger equity at the last cycle of each UTC day.
   - Days without forward data are skipped, not filled. The F4 paper starts 2026-10-15 and N1 starts 2026-10-21, so the gaps 10-01 … 10-14 (1D) and 10-01 … 10-20 (N1) are simply absent.

**Month of 2026-10.** The weight uses the backtest only (all 126 days ≤ 2026-09-30). This is the same rule E-2 applied.

## 4. Amendment 1 integration (2026-10-22; amendment `ECO_AMENDMENT_1_PREREGISTERED.md` 0a448a79…)

**`eco_core.py`:**
- `desired_stops`, `diff_stops`, `book_triggered`, `round_tick`: amendment §2 / §3, with the details in CODE_NOTES 3.
- `inv_vol_weight`, `forward_returns`: CODE_CHANGES 3.
- `allocate_funding` uses the signed share (before E-3; mock test U6).

**`eco_orchestrator.py`:**
- Stop status at cycle start, before the targets. Stop sync after the fills.
- Guard-fired symbols are frozen.
- Ledger fields: `targets_net`, `exch_before`, `price` (for verifier V3), `stops`, `k_now`.
- Options: `--host`, `--k-from` (the shadow, §4.3).
- Demo mode needs the cut-over state.

**New `eco_cutover.py`:** amendment §4.2.

**Config** (`deploy/build_eco_config.py`):
- `guard_on`, `guard_D` (from `A1_outage_guard.json`: 0.50);
- `profit_lock` = false, because ECO-T4 failed;
- `amendment_1_sha256`.

**Tests:** `test_eco_core.py` now has 25 checks.
- New: S1–S6 for the stops, X1–X2 for the cut-over.
- **X2 was rewritten before it was first relied on.** Its first draft had an equity condition that was always true. It now asserts attribution P&L == account P&L since the cut-over.

**`claims_eco_e2.json`:** its `notes_sha` refers to CODE_NOTES as it was at E-2 time, note 1 only. Notes 2 and 3 were appended later; the file is append-only.

## 5. Live config versions and live verifier L2 (2026-10-22)

| Config | SHA | Used by |
|---|---|---|
| v1 | 4d4b784ae5c9… | The first VM plan cycles, 2026-10-21 19:03 and 19:20 UTC |
| v2 | f32f3f3a1e11… | From the amendment-1 deploy onward. Adds `guard_on`, `guard_D` = 0.5, `profit_lock` = false, `amendment_1_sha256` |

**Live verifier L2 rule:**
- the last cycle uses the config on disk;
- every config SHA in the ledger is listed here;
- the protocol SHA is constant.

An unlisted config change still FAILS.

## 6. Amendment 2 (2026-10-22; amendment `ECO_AMENDMENT_2_PREREGISTERED.md` 312a2c49…): safety and accounting fixes

**Source:** audit `AUDIT_ECOSYSTEM_QUALITY_COVERAGE_22_OCT_2026.md`, parts 1–3. No strategy input changes. Details are in CODE_NOTES 4, which also records one deliberate deviation: TRIGGERED without a fill is kept, not dropped.

**Code versions in the ledger** (live verifier L11 requires every one to be listed here):

| Version | orchestrator | core | exchange | Used |
|---|---|---|---|---|
| v1 | 72166c20627a… | 150afc2f036c… | 74a5e4fe36fb… | VM plan cycles 2026-10-21 19:03, 19:20 UTC |
| v2 (amendment 1) | 2bb60508d81a… | 38394803f173… | 74a5e4fe36fb… | VM plan cycles from 2026-10-21 20:06 UTC |
| v3 (amendment 2) | 4813d88112ea… | 95bccb3b02e7… | a29e8ecd200d… | laptop tests; VM after the user's go |

**New files:**
- `eco_reset.py` a4a7ca0552fa…
- `eco_alerts.py` 591d41525d9d…

**Changed files:**
- `eco_cutover.py` 5621eaea6f97…
- `verify_eco_live.py` 4a4a42254690…
- `test_eco_core.py` c19b86bc169b…

**Proposed crontab:** `deploy/crontab_proposed_A2.txt` 32e2b29c26c6… adds ECO_Alerts. Not deployed.

**Tests (laptop, 2026-10-22):** `test_eco_core.py` has 43 checks (25 old + A2-1…A2-18).
- A2-16, A2-17 and A2-18 were added beyond the amendment's list after the re-audit found R-5, R-6 and R-4.
- T8 needs the public endpoints. The laptop network timed out (curl 000), so T8 is run on the VM.

**Mock change.** `MockEnv.stop_status` / `fire` now answer like the real Query Algo Order: (status, actualQty, actualPrice), with FINISHED after a fill.

**Replay regression** (E-3 replay, two runs, new code):
- R1 8.32e-10;
- R3 / R5 0;
- R6 identical;
- R4 9/9;
- R2 1.204%, the known E-3 FAIL, unchanged.

**Bugs found while coding, all fixed before any deploy** (audit part 3 §19):
- order-id collision;
- caps at equity ≤ 0;
- funding split after the orders (R1 1.88e-02 in the regression → fixed);
- `halted` missing from the kill-cycle record;
- a second order while one is still working;
- a ledger-only position at a kill;
- no journal recovery while halted;
- a plan order without a current price.

## 7. 2026-10-22: alerts cover the new jobs; deploy crontab

- `eco_alerts.py`: a29… → **cc970b7f3bf4…**. The job-failure check also reads EMO_Meter, EMO_Verify and LogShip; nothing else changed. A2-18 still PASS.
- `deploy/crontab.txt` **f1e227909bc1…** (first written with CRLF, SHA 25f8eb9f33ec…, by a Windows write; installed like that for < 1 min at 12:49 UTC, when no cron minute fell, then stripped to LF and re-installed; checked: 0 CR, 29 old lines kept + 6 new): the previous VM crontab plus ECO_Alerts (:52 IST hourly, 07:27 IST) and the EMO meter jobs. It replaces the proposed file of entry 6. The backup of the old crontab is `deploy/crontab_backup_before_A2_20261022.txt`.

## 8. 2026-10-23: record of the current crontab (record gap closed)

- A log audit on 2026-10-23 found that the crontab now installed on the VM, **`deploy/crontab.txt` f0292d86c2a7…** (36 lines, LF), had no SHA in any change record.
  - The last recorded SHA was f1e227909bc1… (entry 7).
  - The difference is the PaperN1 retry/catch-up line (`56 1,5,9,13,17,21 * * *`) added by PAPER-N1 amendment 1 (logs/paper_n1/CODE_CHANGES_AFTER_LOCK.md).
- Checked on the VM 2026-10-23 08:26 UTC: `crontab -l | cmp - deploy/crontab.txt` → same; 0 CR. Laptop file SHA is the same, f0292d86c2a7….
- No job changed; record only.

## 9. 2026-10-25: demo cut-over (amendment 1 §4). Written BEFORE the steps are run

**Gate §4.1 + amendment 2 §7, checked on the VM 2026-10-25 04:10–04:17 UTC (read-only):**
- 83/83 plan cycles ok.
- ECO_Verify exit 0 on 2026-10-23, 24 and 25 (3 days, all on the amendment-2 code).
- `test_eco_core.py` 43/43 PASS, including the cut-over mock tests X1 and X2.
- F6 positions == demo account (7 shorts, no mismatch); one-way mode.
- **Margin-type report:** `/fapi/v1/symbolConfig` shows all 7 adopted symbols (WLD, UNI, NEAR, SUI, FET, ONDO, QNT) ISOLATED, leverage 1. Per amendment 2 §7 the code does not change them.
- Wallet (totalMarginBalance) 5,153.55 → k ≈ 0.515.
- Margin estimate on the last plan targets: ~2,476 of 5,154 needed.

**User's go:** in chat on 2026-10-25 the user gave all permissions to plan and do the pending steps.

**Steps, in order:**
1. F6 `--mode plan`, recorded in `logs/eco/cutover_2026-10-25/`.
2. Back up the crontab and remove the two F6 lines (diff = only those lines).
3. Install config v3 = v2 + `demo_enabled: true`.
   - `deploy/build_eco_config.py` gets a `--demo` flag, so a rebuild reproduces v3.
   - The history CSV must stay byte-identical.
4. Run `eco_cutover.py --execute`.
5. First demo cycle by hand through `run_job.sh ECO_Demo`, then the shadow.
6. Run the live verifier on both roots.
7. Install the new crontab lines.

**Interpretations (amendment 1 §4.3 does not fix these details):**
- **I1. Shadow start.** `data/eco_shadow` starts from a byte copy of the adopted `data/eco_demo/state.json`, taken before the first demo cycle. Demo and shadow therefore start from the same book.
- **I2. One cron line, demo then shadow (`;`).** The shadow reads the demo's k and marks 1–2 minutes later, not at the same minute. A same-minute start could read k before the demo writes it.
- **I3. `data/eco` stays as it is.** The public-host plan instance keeps running as the plan record.
- **I4. Daily jobs.** Verifier and alerts run daily for both new roots. The `eco_alerts.py` job list gets ECO_Demo_Verify, ECO_Shadow_Verify and ECO_Tracking, so their failures alert too.
- **I5. Tracking check TC (§5) has no tool yet.** `src/eco/eco_tracking.py` + an independent verifier will be written from the fields of the first real demo records, and before the first full UTC day ends. Until then the two ledgers hold the raw numbers.
**Files for entry 9 (laptop, before the VM steps):**
- `deploy/eco_config.json` **v3 3d5b3ac9b8ee…**: v2 + `demo_enabled: true`, nothing else (key-by-key diff vs v2). Written by `build_eco_config.py --demo`, and `eco_history_daily_returns.csv` stayed byte-identical. CRLF like v2.
- `deploy/build_eco_config.py` 9deb2784ea88… (the `--demo` flag; laptop only).
- `src/eco/eco_alerts.py` 416a03d1cfda… (job list + ECO_Demo_Verify, ECO_Shadow_Verify, ECO_Tracking).
- `deploy/crontab_cutover_step2.txt` 9bf680ed324d…: the current crontab minus the two F6 lines.
- `deploy/crontab_cutover_final.txt` c66de3b39cab…: step 2 + 5 ECO demo lines.
**Entry 9 results (VM, 2026-10-25), with the evidence in `logs/eco/cutover_2026-10-25/`:**

- **Step 1 (04:17 UTC).** F6 `--mode plan`: 15 actions, record `20261025T041733_plan.json`.
- **Step 2 (04:20:57).** Backup `deploy/crontab_backup_before_cutover_20261025.txt` f0292d86c2a7… (== the recorded crontab). The diff is only the two F6 lines (`step2_crontab.diff`). Installed == `crontab_cutover_step2.txt`; F6 lines active: 0.
- **Step 4 (04:21:04).** `--execute` rc 0.
  - `DELETE algoOpenOrders` was code 200 on all 7 symbols.
  - Adopted 15 components; wallet 5,152.73.
  - F6 state → `state_demo_retired_2026-10-25.json`.
  - `data/eco_demo/state.json` SHA 3bfbe481ac4b…; I1 shadow copy byte-identical.
- **Step 5 (04:21 / 04:23).** Demo cycle rc 0, shadow rc 0.
  - Both at k_m 0.51528 (the shadow read the demo's k).
  - 23 orders each; 2 skipped inside the band (ASTER 7.12, ONDO 1.96 USDT).
  - **Exchange positions == ledger held_net on all 24 symbols.**
  - 34 open algo stops: 24 guards + 10 1D-short stops. WLD and NEAR 1D-short stops are virtual only, because the net is smaller than the 1D shorts (as designed).
  - Eco equity: demo 9,996.98, shadow 9,997.88.
  - `verify_eco_live.py`: data/eco_demo 11/11 PASS, data/eco_shadow 11/11 PASS.
- **Step 6 (04:24).**
  - **Error, caught by `crontab` itself:** the first final file had no newline at its end, and `crontab` refused it. Nothing was installed and the step-2 crontab stayed. But `deploy/crontab.txt` on the VM had already been overwritten with that file. Both were fixed within 30 s.
  - The final file now ends with a newline: **d047abdcc7d8…** (replaces c66de3b39cab…). The diff vs step 2 is only the 5 new lines (`step6_crontab.diff`).
  - Installed == final; `deploy/crontab.txt` = d047abdcc7d8… on the VM and the laptop; F6 lines 0.
- **Next scheduled demo cycle:** 05:20 UTC (10:50 IST), then hourly.
## 10. 2026-10-25: tracking-check tool TC (entry 9, I5). Written before the VM install

**Files:**
- `src/eco/eco_tracking.py` df6c387bba45… implements amendment 1 §5 as written:
  - d_day and d_cum use the last ok cycle of each finished UTC day.
  - The cut-over day is partial and not counted.
  - Gate after 14 full days: |d_day| ≤ 30 eco units on ≥ 12 days, and |d_cum| ≤ 100.
  - Report: slippage in bps vs the decision mark (notional-weighted, + = worse), rejected and unconfirmed orders, band skips, funding demo vs shadow.
  - Output: `logs/eco/tracking/`.
  - **Not implemented:** the info-only "shadow vs paper combination" item.
- `src/audits/verify_eco_tracking.py` 8427993264d8…: an independent recompute. K1 ledger SHAs; K2 diff, d_day, d_cum and day_ok; K3 execution stats; K4 gate.
- `src/audits/test_eco_tracking.py` d9f2f013f4b4…: synthetic known-answer cases, laptop 7/7 PASS.
  - A: 2 days over → PASS.
  - B: 3 days over → FAIL.
  - C: a missing shadow day.
  - D: only finished days count, no gate before 14 days.
  - E: a 0.01 change in the output is caught by the verifier K2.
  - The first draft of E was hollow: it accepted the word "FAIL" in "FAIL 0", and its tampering string never matched. It was rewritten before being relied on; rc 1 is now required.

**Crontab:** `deploy/crontab_tracking.txt` 46a47f9784eb… = d047abdcc7d8… + 1 comment line + 1 job line, at 07:35 IST daily: the tool, then the verifier, both under job ECO_Tracking. ECO_Tracking is in the alerts job list (entry 9).
## 11. 2026-10-25: the crontab after entries 9 and 10 (record continuity)

`deploy/crontab.txt` (VM == laptop) went through these SHAs, each a diff of added lines only, installed with `crontab` + `cmp`:

| SHA | What changed |
|---|---|
| 46a47f9784eb… | entry 10 |
| aaf9571d16db… | + the PAPER-N1 sleeve A forward job (record: `logs/paper_n1/CODE_CHANGES_AFTER_LOCK.md`, 2026-10-25) |
| **b04c384dd3c0…** | + the three PAPER-SPOT-S1 jobs (record: `logs/paper_spot_s1/CODE_CHANGES_AFTER_LOCK.md`) |

No ECO job line changed after entry 9.
## 12. 2026-10-25: fee unification (logs/fees/FEE_AMENDMENT_PREREGISTERED.md (2d9d1485…))

- `deploy/fees.json` v1 b76c04950e09… is the single fee table (evidence: `logs/fees/FEES_RECORD.md`).
- `deploy/eco_config.json` **v4 579bece93249…** = v3 + `fee` 0.00054 → **0.0004**, the fee the demo account actually charges: base taker 0.040%, no BNB in the futures wallet, feeBurn off.
  - Key-by-key diff vs v3: only `fee`. The history CSV is byte-identical.
- `deploy/build_eco_config.py` 48034b326a4e… reads `fee` from `fees.json` (laptop only).
- Effective from the first cycle after deploy, in data/eco, data/eco_demo and data/eco_shadow. Earlier records keep 0.00054.
## 13. 2026-10-28: amendment 3: DDX drawdown alarm + job coverage (warning only). Written BEFORE the deploy

**Amendment:** `logs/eco/ECO_AMENDMENT_3_PREREGISTERED.md` **a47eb03c2b7c…**, locked 2026-10-28T08:36:31Z, before any code was written. Item A1 of the consolidated plan; the user gave a free hand on 2026-10-28.

**Files:**
- `src/eco/eco_alerts.py` 416a03d1cfda… → **0171447c1ceb…**:
  - `dd_status()` and the `dd_yellow` / `dd_red` / `dd_alarm_off` conditions;
  - `JOBS` = the 29 crontab job names;
  - `load_ledger()`;
  - the printed `dd …` line.
  - The other conditions, dedup, Telegram and the file outputs are unchanged.
- `deploy/eco_dd_alarm.json` **682e397bed4b…** (new): generated by a script from `logs/drawdown_ddx/alarm_thresholds.csv` b53e2c1095a4…, not typed by hand.
- `src/audits/test_eco_dd_alarm.py` **12ad90b74ec2…** (new): D1–D12.
- `src/audits/verify_eco_dd_alarm.py` **9d9fe3ed5fe4…** (new): independent, pandas cummax. V1 config, V2 300 random ledgers, V3 real ledgers.
- Also copied to the VM, needed by D10 / V1: `logs/drawdown_ddx/alarm_thresholds.csv`, `DDX_PROTOCOL_PREREGISTERED.md` 12d2c5a2…, `PROTOCOL_SHA256.txt`.

**Laptop results** (evidence in `logs/eco/amendment3_evidence/`):
- **Test run 1:** 5 FAIL (`test_laptop_run1.txt`).
  - D1–D4 were a test-construction error. The synthetic fall began 4 h before the start, so, correctly per §1, part of it was not counted, and dd < the intended 5 / 8 / 10%.
  - The helper was fixed (flat until the start). **No code change.**
  - D12 is the network failure described next.
- **Run 2:** 11/12 PASS (`test_laptop_run2.txt`).
  - The only FAIL is D12. `test_eco_core.py` was 42/43 because T8, a public Binance endpoint, timed out (WinError 10060).
  - The laptop cannot reach `fapi.binance.com` (curl 000, timeout). A2-18 (alerts) PASS.
  - D12 is re-run on the VM.
- **Verifier run 1:** V1 FAIL (`verify_laptop_run1_pandas_float.txt`).
  - The verifier's `pd.read_csv` default float parser drops the last digit (0.07361788062729441 → 0.0736178806272944). The config holds the exact values.
  - The verifier now uses `float_precision="round_trip"`. A verifier fix, not a code or config change.
- **Run 2:** V1 + V2 PASS. V2: 300 random ledgers, 0 mismatches; levels seen none 11 / normal 89 / yellow 14 / red 186.
- **Mutation:** one yellow value set to 0.05 in a copy → V1 FAIL + V2 FAIL (10 mismatches), exit 1 (`mutation_test_output.txt`).
- **Real ledgers** (copies taken from the VM 2026-10-28 08:47 UTC; now = 08:45): V3 PASS for all three (`verify_laptop_real_ledgers.txt`).

  | Ledger | dd since 2026-10-26 | Base | Level |
  |---|---|---|---|
  | data/eco | 1.2079% | 10-25 23:20 | normal |
  | data/eco_demo | 1.2369% | 10-25 23:20 | normal |
  | data/eco_shadow | 1.2380% | 10-25 23:20 | normal |

  - All are at a = 2, H* = 30, yellow 7.36%, red 9.35%.
  - Why it differs from the "max DD 1.775%" of the snapshots: that figure is measured from the cut-over 10-25 04:21, so it includes the 10-25 peak. The DDX rule starts at 10-26.

**Corrections to the locked amendment text (no effect on the rule):**
- §2 says "Today: the job list has 13 names (10 in the code, plus ECO_Demo_Verify, ECO_Shadow_Verify and ECO_Tracking)". In fact the code list had **10** names, and those three were already among them.
  - Not covered before: 19 jobs.
  - Covered now: all 29 (D11 checks the code list = the crontab names).

**Pre-deploy facts (VM read 2026-10-28 08:50 UTC):**
- All 29 jobs have last exit 0, so no job_fail alert is expected at the first run.
- `.env` has no ECO_TELEGRAM keys, so alerts are file-only (logs/eco/alerts*/alerts.jsonl, shipped to Drive hourly).

**Deploy plan:** release R-2026.10.28-2 (`deploy/RELEASES.md`), amendment 3 §5.

### 13b. Deploy result (written after the deploy)

**Deployed 2026-10-28 09:11:31 UTC** as release R-2026.10.28-2 (`deploy/RELEASES.md`):
- **Pre-check:** the VM equalled the baseline R-2026.10.28-1, 183/183 files.
- **Backup:** `backups/release_R-2026.10.28-2/`, holding eco_alerts.py 416a03d1… and both CODE_CHANGES files.
- **Install:** 24 files, 0 SHA mismatches.

**VM checks:**
- `version_check.py`: VERSION OK, 187 + 6 vm_only + crontab, extra 0.
- `verify_eco_dd_alarm.py` on the live ledgers (09:12 UTC): 5/5 PASS.
- `test_eco_dd_alarm.py` (`amendment3_evidence/test_vm_run1.txt`): D1–D11 PASS. `test_eco_core.py` gave exit 0, TOTAL 43, FAIL 0, A2-18 PASS, and T8 passed on the VM.
  - D12 was reported FAIL by a bug in the test's own check: it searched for "[PASS] A2-18", but the line is "[A2-18 PASS]".
  - Fixed in `test_eco_dd_alarm.py` 35cfac21…, release R-2026.10.28-3. The re-run result is below.

**First cron runs with the new code** (cron_status/ECO_Alerts.csv / .out):

| Run (UTC) | Root | Exit | dd since 10-26 | Level |
|---|---|---|---|---|
| 09:22:01 | data/eco | 0 | 0.012079 | normal |
| 09:28:01 | eco_demo | 0 | 0.012369 | normal |
| 09:28:02 | eco_shadow | 0 | 0.012380 | normal |

- All three show a = 2, H* = 30, yellow 0.073618, red 0.093532.
- 0 conditions active, 0 new alerts; alerts_state.json `[]`.
- The ECO_Demo cycle at 09:20 exited 0.

### 13c. Release R-2026.10.28-3 (test check fix), applied 2026-10-28 09:34:13 UTC

- **Applied with:** `deploy/apply_release.py`. Pre-check = R-2026.10.28-2, 0 problems; backup `backups/release_R-2026.10.28-3/` (9 files); 20 installed, 0 SHA mismatches; VERSION OK (190 + 6 + crontab, extra 0).
- **`test_eco_dd_alarm.py` on the VM** (`amendment3_evidence/test_vm_run2.txt`): **12/12 PASS**. D12: `test_eco_core.py` exit 0, 43/43, A2-18 PASS.
- **`verify_gate_calendar.py` on the VM:** 23/23 PASS.
- Amendment 3 is complete. The live code is unchanged since R-2026.10.28-2 (`eco_alerts.py` 0171447c…).
