# Releases: which code version runs where (laptop + VM)

**How to read this file:**
- The **latest release** is the last entry. `deploy/release_manifest.json` holds its full file list with SHA-256, and `deploy/releases/<id>.json` keeps every release.
- **Check a copy:** on the VM, `venv/bin/python deploy/version_check.py`; on the laptop, `python deploy/version_check.py`. The result is `[VERSION OK] … release <id>`, or `[VERSION DRIFT]` with the files that differ.
  - The VM check also covers the VM-only files and `crontab -l`.
  - Laptop-only research code is listed as "extra" and does not count against the laptop.
- **Make a release** (laptop only): `python deploy/make_release.py --id R-YYYY.MM.DD-n [--add PATH …] [--remove PATH …]`. A release id is used once.

**Rules:**
- **What a manifest covers:** code, config and locked protocol files.
- **Records are not in the manifest.** CODE_CHANGES files, ledgers and state are append-only and change after a release; their SHA at release time is written in the entry here.
- **Every VM deploy:**
  - pre-check that the VM equals the previous release;
  - back up the files to be replaced to `backups/release_<id>/`;
  - copy, then run `version_check.py` on both sides;
  - append the record entry in the same step.
- **Rollback:** copy `backups/release_<id>/` back, then copy the previous `deploy/releases/<parent>.json` to `deploy/release_manifest.json`.

---

## R-2026.10.28-1: baseline (state found, nothing changed)

- **When:** 2026-10-28 08:2x UTC, from a read-only hash run on the VM.
  - The listing is in `logs/releases/R-2026.10.28-1_vm_hash_listing.csv`; the script is `logs/releases/code_hash.py`.
  - Manifest made 08:37:37Z; manifest SHA ef4d9ef44bae….
- **Content:**
  - 177 files of src/ + deploy/, identical on the laptop and the VM (0 differ);
  - 6 VM-only files: the old `BUNDLE_MANIFEST.csv` of 2026-10-16, 4 old crontab backups, and `crontab.txt.pending` (= crontab.txt, diff empty);
  - crontab 13443469f4ec… (`crontab -l` = `deploy/crontab.txt`).
- **Laptop-only:** 108 research / audit files (not run on the VM; no VM file imports them, checked with grep).
- **Live versions inside:**
  - log-ship v7 (shipper aca75629…, verifier 3ab83c85…);
  - eco_alerts 416a03d1…;
  - eco_config v4 579bece9…;
  - fees.json b76c0495….

## R-2026.10.28-2: ECO amendment 3 (DDX drawdown alarm + job coverage) and the release tooling

- **Parent:** R-2026.10.28-1.
- **Why:** item A1 of `CONSOLIDATED_ACTION_PLAN_28_OCT_2026.md`, plus versioning (the user, 2026-10-28).
- **Changed:**
  - `src/eco/eco_alerts.py` 416a03d1… → 0171447c…, which adds the yellow / red drawdown alarm (warning only) and job-failure alerts for all 29 crontab jobs.
- **New:**
  - `deploy/eco_dd_alarm.json` 682e397b…;
  - `src/audits/test_eco_dd_alarm.py`, `src/audits/verify_eco_dd_alarm.py`;
  - `deploy/version_check.py`, `deploy/make_release.py`;
  - on the VM: `logs/drawdown_ddx/alarm_thresholds.csv`, `DDX_PROTOCOL_PREREGISTERED.md`, `PROTOCOL_SHA256.txt`, `logs/eco/ECO_AMENDMENT_3_PREREGISTERED.md` + `_SHA256.txt`.
- **Not changed:** strategy, orders, kill switch, crontab (13443469f4ec…), fees.
- **Records written with this release:**
  - `logs/eco/CODE_CHANGES_AFTER_LOCK.md` entry 13;
  - `logs/log_ship/CODE_CHANGES_AFTER_LOCK.md` entry 9 (A2: the v7 deploy record, no code change).
- **Deploy and verification:** see entry 13 of the ECO record and the lines below, written after the deploy.
- **Deployed 2026-10-28 09:11:31 UTC** (staged tar 316d3244…, 24 files; guarded script, laptop copy in the session scratchpad).
  - **Pre-check:** the VM equalled R1, 183/183 files. The old record SHAs were as expected: ECO 05b96cb0…, log-ship 5ea59abe….
  - **Backup:** `backups/release_R-2026.10.28-2/`. It holds `src/eco/eco_alerts.py` 416a03d1… and both CODE_CHANGES files.
  - **Install:** 24 files, 0 SHA mismatches.
- **VM checks, 09:11–09:12 UTC:**
  - `version_check.py`: VERSION OK, 187 + 6 + crontab, extra 0.
  - `verify_eco_dd_alarm.py` on the live ledgers: 5/5 PASS. dd since 10-26: eco 1.208%, eco_demo 1.237%, eco_shadow 1.238%; all normal.
  - `test_eco_dd_alarm.py`: 11/12. D12 FAIL was **a check bug in the test**: it looked for "[PASS] A2-18", but `test_eco_core.py` prints "[A2-18 PASS]". `test_eco_core.py` itself gave exit 0, TOTAL 43, FAIL 0, A2-18 PASS (`logs/eco/amendment3_evidence/test_vm_run1.txt`). The fix is R-2026.10.28-3.

## R-2026.10.28-3: test check fix + release tools (no live-code change)

- **Parent:** R-2026.10.28-2.
- **Changed:** `src/audits/test_eco_dd_alarm.py` 12ad90b7… → 35cfac21…. D12 now looks for "[A2-18 PASS]".
  - This bug was also present in the laptop run 2. There D12 failed anyway, because T8 had no network.
- **New:**
  - `deploy/apply_release.py` (VM: time guard, pre-check = parent release, backup, atomic install, version check);
  - `deploy/pack_release.py` (laptop: tar of the changed files + records).
  - `src/audits/verify_gate_calendar.py` (claims check of `FORWARD_GATE_CALENDAR.md`, A3: 23/23 PASS, mutation caught).
- **Not changed:** eco_alerts, config, crontab, strategy.
- **Applied 2026-10-28 09:34:13 UTC** with `deploy/apply_release.py`, run from the staged dir with `--root`, because it was new.
  - Staged tar 5ea15184…, 20 files.
  - Pre-check = R-2026.10.28-2, 0 problems; backup `backups/release_R-2026.10.28-3/` (9 files); 0 SHA mismatches.
  - `version_check` on the VM: **VERSION OK R-2026.10.28-3**, 190 files + 6 vm_only + crontab, extra 0.
- **On the VM afterwards:** `test_eco_dd_alarm.py` **12/12 PASS**; `verify_gate_calendar.py` 23/23 PASS.
- **Latest release on the laptop and the VM: R-2026.10.28-3.**
