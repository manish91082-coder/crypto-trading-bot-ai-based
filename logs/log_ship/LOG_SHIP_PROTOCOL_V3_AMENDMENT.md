# Log shipping protocol v3 amendment (2026-10-22): the ECO and PAPER-N1 folders join the hourly Drive bundle

**Amends:** `LOG_SHIP_PROTOCOL_PREREGISTERED.md` (965b924c…) and `LOG_SHIP_PROTOCOL_V2_AMENDMENT.md` (071f2fe7…). Everything not changed here stays the same:
- the hourly verified bundle and the shipped index;
- "never delete on Drive";
- the F1 / F2 freeing rules, the lock and the ledger.

This amendment is locked before the code changes.

## Why (checked on the VM, 2026-10-22 05:16 UTC)

**What is missing.** A search for files written in the last 24 h outside the v2 mirror set found the systems deployed after 2026-10-19, which had no copy on Drive:
- ECO: `data/eco`, `logs/eco`, `deploy/eco_config.json`, `deploy/eco_history_daily_returns.csv`;
- PAPER-N1: `data/paper_n1`, `logs/paper_n1`, `deploy/paper_n1_config.json`.

**What else showed up.** The only other recently written files were `data/forward/live_1d` and `live_1h`, 491 + 491 files per day. These stay **unshipped**, by the v1 decision: they are market caches, rewritten daily and re-downloadable.

**Space** (`rclone about`):
- Drive: 5 TiB total, 4.856 TiB free.
- VM disk: 27% used (13 of 48 GB).
- The ECO ledger grows about 4.7 KB per cycle (about 110 KB per day). It is append-only, but the v2 rule re-ships a changed file whole. At 30 days that is about 3.3 MB per hourly copy before gzip, which is negligible against the free space. This is reviewed at day 90.

## v3 changes

**1. Mirror set additions** (paths that do not exist yet are skipped, as v2 already does):

| Path | What it is |
|---|---|
| `data/eco`, `data/eco_demo`, `data/eco_shadow` | ECO plan / demo / shadow roots: ledger and state |
| `logs/eco` | Protocol, amendments, notes, claims, results |
| `data/paper_n1`, `data/paper_n1_test_cycle_20261021` | PAPER-N1 live ledger and state; the retired test-cycle root |
| `logs/paper_n1` | Protocol, notes, replay evidence |
| `deploy/eco_config.json`, `deploy/eco_history_daily_returns.csv`, `deploy/paper_n1_config.json` | Live configs |
| `deploy/crontab_backup_before_R2_20261019.txt`, `deploy/crontab_backup_before_PAPERN1_20261021.txt`, `deploy/crontab_backup_before_ECO_20261022.txt` | Crontab backups |

**2. Verifier W4 essential files.** Add:
- `data/eco/ledger.jsonl`, `data/eco/state.json`;
- `data/paper_n1/ledger.jsonl`, `data/paper_n1/state.json`.

**3. Freeing on the VM: unchanged** (F1 idle `.out` chunks, F2 `backups/<date>` older than 2 days).
- **Reason.** Every other growing file is read again: by the next run (state, ledgers), by the verifiers (ledger chains, SHA-cited raw files) or by the producers (market caches).
- Deleting them would break the live system.
- At the measured growth, the VM disk stays far from full: the largest growing folder, `data/forward_r2/raw`, adds about 22 MB per day.

## Tests

- **Laptop (rclone stub):**
  - T1–T5 as in v2, unchanged.
  - New **T6:** the fake root also holds the new paths. After a ship, every file under them is a bundle member with its md5, and the verifier W4 sees the four new essential files.
- **VM:**
  - copy with a SHA check;
  - wait for the next scheduled LogShip run;
  - check its manifest: it must list the new paths, with `verified=True`;
  - run `verify_log_ship.py` W1–W4.
