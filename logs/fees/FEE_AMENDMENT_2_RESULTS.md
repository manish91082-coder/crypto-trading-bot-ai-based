# Fee amendment 2: test results and deployment (2026-10-25)

## Pre-deploy tests

VM `/tmp/p1d` mirror: new `src` + `deploy`; `data` / `logs` read through symlinks; writes went to sandboxes.

| Test | Result |
|---|---|
| **K3a** | Old fee reproduces the logged as-of 2026-10-24 files: F4 max diff 1.82e-12, 16B max diff 1.82e-12. The harness is right. |
| **K3b** | New fee C1 (F4 LO == 16B paper): max diff 0.00 |
| **K3c** | As-of 2026-10-24, M_AI3, old → new: LS_RS 10,424.23 → 10,437.39; LO / 16B 9,888.24 → 9,897.57 |
| **K1** | `preflight_f4.py` PASS: 2 sandbox days, chain OK, C1 True |
| **K2** | `preflight_shadow_e11.py` PASS |
| **K4** | First run in the mirror: V1 failed, because the new code SHA was not yet in the VM's 16B CODE_CHANGES. That is correct verifier behaviour. After the records were copied, it ran on the real files and passed (see below). |

**Size of the level jump.** K3c is the size of the first-day jump: about +13 USDT on 10,000 for LS_RS and +9 for LO / 16B after 10 days.

## Deployment (VM, 2026-10-25 14:20 UTC)

- **Backups:** `backups/fee_amend2_20261025/`.
  - The F4 CODE_CHANGES copy was skipped by `cp` (same file name as the 16B one). The file is append-only, so its earlier text is inside the new file.
- **Live files (VM == laptop):**
  - `forward_multi_16b.py` 5c91d473d0fc…;
  - `forward_ls_f4.py` aeb1a80c8ac4…;
  - `verify_forward_multi_16b.py` 1404383272ce…;
  - the D3 reference `logs/research_1d_true_fee/equity_MAIN_AI_R1_RS.csv` dfb464db9c96….
- **Verifiers on the real ledgers after deploy:**
  - 16B: V1 PASS (code documented), V4 PASS;
  - F4: V1–V5 PASS (C1 10/10 days);
  - E11: V1–V3 PASS.
- **Live import:** F4 C_LONG 0.00085, C_SHORT 0.00046; 16B COST 0.00085.
- **First runs with the new fee:** 2026-10-26, 16B at 07:30 IST and F4 at 07:45 IST (as-of 2026-10-25).
