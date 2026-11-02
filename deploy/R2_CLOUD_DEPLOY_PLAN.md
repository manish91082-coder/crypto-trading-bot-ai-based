# R2 cloud + Google Drive deployment plan (written 2026-10-19; NOT yet executed; for one combined session with the user)

**Rule:** nothing in the running 1D system is changed except `crontab`, which gets added lines. Every step has a check, and the next step starts only after that check PASSes.

## 0. Before starting (laptop)
- [ ] `logs/r2_4h_a0/REGRESSION_19_OCT_2026.txt` shows every verifier and test PASS (the master audit's 2 known rounding FAILs are expected).
- [ ] The SHA256s of the files to copy equal the SHA list in that regression file.

## 1. Copy the files (scp, no other change)
| Laptop | VM |
|---|---|
| `src/execution/forward_recorder_r2.py` | `/opt/cryptobot/src/execution/` |
| `src/audits/verify_forward_recorder_r2.py` | `/opt/cryptobot/src/audits/` |
| `logs/forward_recorder_r2/FR_PROTOCOL_PREREGISTERED.md`, `FR_PROTOCOL_SHA256.txt`, `CODE_CHANGES_AFTER_LOCK.md` | `/opt/cryptobot/logs/forward_recorder_r2/` |
| `deploy/ship_logs_drive.py` | `/opt/cryptobot/deploy/` |
| `src/audits/verify_log_ship.py` | `/opt/cryptobot/src/audits/` |
| `logs/log_ship/LOG_SHIP_PROTOCOL_PREREGISTERED.md`, `LOG_SHIP_PROTOCOL_SHA256.txt`, `CODE_CHANGES_AFTER_LOCK.md` | `/opt/cryptobot/logs/log_ship/` |

**Check:** `sha256sum` on the VM equals the laptop.

## 2. Forward recorder on the VM
1. **First real run** by hand: `venv/bin/python src/execution/forward_recorder_r2.py --root data/forward_r2`. The bootstrap takes about 10–40 min.
2. **Check:** `venv/bin/python src/audits/verify_forward_recorder_r2.py data/forward_r2 --replay 60` gives 9/9 PASS.
3. **Crontab:** add 6 lines at minute 37 of the IST hours 01, 05, 09, 13, 17 and 21 (7 min after each 4h close), using the existing `deploy/run_job.sh FR2_Recorder src/execution/forward_recorder_r2.py --root data/forward_r2`.
4. **Check:** `crontab -l` diff = only the new lines; the next scheduled run's verifier gives 9/9.

## 3. Google Drive (rclone v1.60.1 is already installed from the Ubuntu repo)
1. **The user authorises it themselves:**
   - in a laptop terminal: `gcloud compute ssh cryptobot-1d-mumbai --zone asia-south1-a -- -L 53682:localhost:53682`;
   - on the VM: `rclone config` → n → name `gdrive` → `drive` → empty client id/secret → scope `3` (drive.file) → empty service account → advanced n → auto config y;
   - open the printed `http://127.0.0.1:53682/...` link in the laptop browser and allow;
   - shared drive n → y → q.

   Claude never sees or prints the token.
2. **Check:** `rclone lsd gdrive:` runs without error.
3. **T6:** `venv/bin/python deploy/ship_logs_drive.py --remote gdrive:CryptoBot_1D_Cloud_VM`, then `venv/bin/python src/audits/verify_log_ship.py --remote gdrive:CryptoBot_1D_Cloud_VM --root /opt/cryptobot`, which must give W1–W4 PASS.
4. **Crontab:** add 1 line, `55 * * * * /opt/cryptobot/deploy/run_job.sh LogShip deploy/ship_logs_drive.py --remote gdrive:CryptoBot_1D_Cloud_VM`.
5. **Check:** after 2 hours, the ledger has 2 lines, the verifier gives 4/4, and the user sees the `CryptoBot_1D_Cloud_VM` folder in Drive.
6. **Update** `deploy/crontab.txt` on the laptop and the VM with the same lines.

## 4. After deployment
- M10 keeps reporting as before; the 1D jobs are unchanged.
- Daily: the recorder verifier and the log-ship verifier, in the daily cloud check (master step 0).
- **Known limits:**
  - the Drive token belongs to the user's account; if it is revoked, shipping stops, nothing is deleted, and the ledger shows rclone errors;
  - log shipping frees disk (`.out` files, old backups), not RAM.

## Note
- Adding the cron lines to `deploy/crontab.txt` changes its SHA. The master-audit verifier's A0 check (`1525e074…`, the 17-Oct version) will then FAIL by design. Record this as expected in the deploy log.
