# ECO amendment 3 (2026-10-28): drawdown alarm (DDX) + alert coverage of every cron job. Warning only, no strategy change

**Amends:** `ECO_PROTOCOL_PREREGISTERED.md`, amendment 1 (0a448a79…) and amendment 2 (312a2c49…). Everything not named here stays the same.

**Source and approval:**
- Item A1 of `CONSOLIDATED_ACTION_PLAN_28_OCT_2026.md` (f1dcff92…), which takes its alarm rule from `logs/drawdown_ddx/DDX_PROTOCOL_PREREGISTERED.md` (12d2c5a2…, Part B "Forward alarm thresholds").
- The thresholds are `logs/drawdown_ddx/alarm_thresholds.csv` (b53e2c10…).
- User approval: 2026-10-28, "free hand … प्रॉपर चेक करके … क्लाउड पे … अपडेट कर देना".

**Scope.** Only `src/eco/eco_alerts.py` changes, plus one new data file `deploy/eco_dd_alarm.json`. It writes alert lines only.
- **Unchanged:** producers, signals, weights, caps, band, fee, guard D, stops, and the kill switch (`kill_K` 0.30 in `deploy/eco_config.json` 579bece9…).
- **No crontab change:** the existing ECO_Alerts lines already run for data/eco, data/eco_demo and data/eco_shadow.
- **Trial budget:** untouched.

## 1. Drawdown alarm (DDX Part B, as locked there)

**Inputs:**
- `deploy/eco_dd_alarm.json` holds `start_utc` "2026-10-26T00:00:00", the four rows of `alarm_thresholds.csv` (H, yellow_dd, red_dd) copied exactly, and the source file's SHA-256.

**Equity series** for each root's `ledger.jsonl`:
- Use records with `mode` ≠ "reset" and a finite numeric `eco_equity`. Records without it, such as failed cycles, are skipped.
- **Base:** the last such record with T < start. If none exists, the first record with T ≥ start.
- **Series:** base, then every such record with T ≥ start, in ledger order.
- **Drawdown:** dd = max over the series of 1 − e_t / max_{s ≤ t} e_s. This is the running **max** drawdown since the start, as DDX defines it, so it does not clear when equity recovers.

**Age and band:**
- a = floor((now − start) / 1 day). Before the start, a < 0, and there is no alarm.
- H* = the smallest H in {30, 90, 180, 365} with H ≥ a, capped at 365.

**Condition:**
- dd > red(H*) → `dd_red`;
- else dd > yellow(H*) → `dd_yellow`;
- else nothing. Only one of the two can hold.
- Key = `H<H*>`. With the existing dedup, an alert is sent once per (kind, key); it is sent again after the condition clears, or when H* moves to a new band.

**Message:** dd, peak, current equity, a, H*, the threshold, and the words "warning only; no trade change; kill switch unchanged".

**Fail loud:**
- A missing or unreadable `eco_dd_alarm.json` → condition `dd_alarm_off`.
- A SHA in the file that does not match its own rows is not checkable on the VM; the independent verifier (§4) checks the rows against the CSV instead.

**Known bias, declared:**
- The live series is hourly, while the band is built from daily closes. An hourly series sees intraday troughs, so the live dd is ≥ the daily-close dd.
- The alarm can therefore fire somewhat earlier than the band's 95% / 99% meaning. For a warning this is the safe side.

**Every root** that eco_alerts runs on uses the same start and thresholds. For data/eco and data/eco_shadow (paper / shadow) this is information only.

**Printed line:** each run prints `dd <x> age <a> H* <H> yellow <y> red <r>`, whether or not an alarm is active. This goes to `ECO_Alerts.out` for later reading.

## 2. Job-failure coverage = every job of the installed crontab

- **Today:** the job list has 13 names (10 in the code, plus ECO_Demo_Verify, ECO_Shadow_Verify and ECO_Tracking). Jobs added since 25 Oct (SleeveA_Forward, PaperSpotS1(_Verify), FwdWatch(_Verify), MK1(_Verify), LiqCollector_Verify) and the older research jobs never alert.
- **New list:** the 29 `run_job.sh` names of `deploy/crontab.txt` 13443469f4ec…, written as a constant in the code:
  - 16B_ForwardMulti, ECO_Alerts, ECO_Demo, ECO_Demo_Verify, ECO_Plan, ECO_Shadow, ECO_Shadow_Verify, ECO_Tracking, ECO_Verify, EMO_Meter, EMO_Verify;
  - F4_LSPaper, FR2_Recorder, FwdWatch, FwdWatch_Verify, LiqCollector_Verify, LogShip, M10_DailyStatus, M4_OptionsCollector;
  - MK1, MK1_Verify, N3_EVTMonitor, PaperN1, PaperN1_Verify, PaperSpotS1, PaperSpotS1_Verify, SleeveA_Forward, Step16_ForwardDryRun, Step2_CostSnapshot.
- The rule is unchanged: the last row's exit code ≠ 0 → `job_fail_<job>` with the start time as key.

## 3. Tests (laptop first, then the VM). New file `src/audits/test_eco_dd_alarm.py`; synthetic ledgers in a temp dir

| Test | Input | Expected |
|---|---|---|
| D1 | dd 5% at a = 10 | no dd condition |
| D2 | dd 8% at a = 10 | `dd_yellow`, key H30 |
| D3 | dd 10% at a = 10 | `dd_red` only, key H30 |
| D4 | dd 10% at a = 45 | none (H* = 90: 11.1% / 14.7%) |
| D5 | 20% fall before start, flat after | none; base = the last pre-start equity |
| D6 | run twice, then deepen to red | second run 0 new; then `dd_red` new |
| D7 | reset records, records with eco_equity None, a failed cycle | ignored; dd as without them |
| D8 | config file missing | `dd_alarm_off` |
| D9 | a = 30, 31, 400 | H* = 30, 90, 365 |
| D10 | `deploy/eco_dd_alarm.json` vs `alarm_thresholds.csv` | rows equal exactly; SHA in the file = SHA of the CSV |
| D11 | cron dir: MK1 last exit 1, PaperSpotS1 last exit 0 | `job_fail_MK1` only |
| D12 | `test_eco_core.py` (regression, A2-18 included) | TOTAL … FAIL 0 |

## 4. Independent verifier `src/audits/verify_eco_dd_alarm.py`

- It does not import eco_alerts' dd code. It re-implements §1 with pandas (cummax) and reads the thresholds from the CSV.
- It compares the result with `eco_alerts.dd_status(...)` on given ledgers: dd within 1e-12, plus identical a, H*, level and base T.
- **Runs:**
  - on synthetic ledgers D1–D7;
  - on copies of the real VM ledgers data/eco, data/eco_demo and data/eco_shadow, read-only on the VM;
  - after deploy, on the live files on the VM, read-only.
- **Mutation test:** a copy of `eco_dd_alarm.json` with one yellow value changed must make the verifier FAIL.

## 5. Deploy (only if §3 and §4 pass)

1. **Pre-check:** the VM files to be replaced still have the SHAs of release baseline R-2026.10.28-1 (`deploy/RELEASES.md`).
2. **Backup:** the old files go to `backups/release_R-2026.10.28-2/`.
3. **Copy:** copy, then compare SHAs. Timing: outside UTC :18–:32, the minutes of the ECO cycle, alerts and log-ship.
4. **On the VM:** D1–D12 and the verifier (§4) on the live ledgers.
5. **The next cron ECO_Alerts runs:** exit 0, and the printed dd line exists for all three roots.
6. **Records:** CODE_CHANGES entry 13, appended. Rollback = copy the backup back; there is no state migration.
