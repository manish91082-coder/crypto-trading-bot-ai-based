# Log shipping protocol v6 amendment (2026-10-25): the ECO demo cut-over and PAPER-SPOT-S1

**Amends:** v1–v5. Everything else is unchanged. Locked before the code change.

**Why.**
- **ECO demo cut-over** (`logs/eco/CODE_CHANGES_AFTER_LOCK.md` entry 9, 2026-10-25):
  - F6 is retired and its state file was renamed to `logs/futures_testnet_f6/state_demo_retired_2026-10-25.json`. The verifier's essential list still names the old `state_demo.json`, which no longer exists.
  - The ECO demo and shadow ledgers are now the system's live records. They are already mirrored since v3, but they are not essential yet.
- **PAPER-SPOT-S1** (`logs/paper_spot_s1/PAPER_SPOT_S1_PROTOCOL_PREREGISTERED.md`) writes new paths that are not mirrored yet.

**Mirror additions:**
- `data/paper_spot_s1`;
- `logs/paper_spot_s1`;
- `deploy/crontab_backup_before_cutover_20261025.txt`.

**Verifier W4 essential:**
- `logs/futures_testnet_f6/state_demo.json` → `logs/futures_testnet_f6/state_demo_retired_2026-10-25.json`;
- add `data/eco_demo/ledger.jsonl`, `data/eco_demo/state.json` and `data/eco_shadow/ledger.jsonl`.
- `data/paper_spot_s1/ledger.jsonl` is mirrored but **not** essential: it does not exist before the first run on 2026-10-26.

**W1:** it also checks the V6 lock.

**Test.** On the VM, T1–T7 run on copies of the real small log directories plus an extra root with the v3/v6 paths.
- T6 must show that the new paths ship with equal md5. For the test only, a stand-in `data/paper_spot_s1/ledger.jsonl` is used.
- The VM test needs `src/audits/rclone_stub.py` (test-only, copied from the laptop).
