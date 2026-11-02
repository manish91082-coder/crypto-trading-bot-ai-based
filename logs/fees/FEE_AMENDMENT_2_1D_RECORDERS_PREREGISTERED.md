# Fee amendment 2 (2026-10-25): the 1D forward recorders (16B, F4 with its E11 shadow) move to the true fee

Locked before the code change. It builds on fee amendment 1 (`FEE_AMENDMENT_PREREGISTERED.md`, 2d9d1485…) and `deploy/fees.json` v1.

**Amends:** `logs/forward_multi_16b/STEP16B_PROTOCOL_PREREGISTERED.md`, `logs/forward_ls_f4/F4_PROTOCOL_PREREGISTERED.md` (+ amendment 1), and the E11 shadow protocol.

## Basis

The re-run `logs/research_1d_true_fee/` (protocol b53f4d4a…, verifier 3/3 PASS):
- The F7 RS engine reproduced the locked F7 equity exactly (max diff 0.0).
- With the true fee, the F7 RS mix went 10,000 → 168,347 (CAGR 63.5%, max drawdown 20.5%), instead of 88,575 (CAGR 46.2%, max drawdown 21.4%).

## Changes

| Recorder | Before | After |
|---|---|---|
| 16B `COST` (spot fill, per side, all three sleeves) | 0.0025 | **0.00085** (`fees.json` `paper_spot_per_side`) |
| F4 spot long fill (`F2R.C_LONG`, every line: LS_RS, LS_F2, LO) | 0.0025 | **0.00085** |
| F4 perp short fill (`F2R.C_SHORT`) | 0.0010 | **0.00046** (`paper_futures_taker_per_side`) |
| E11 shadow | the same constants through `forward_ls_f4` | follows F4 automatically |

- **Stop slippage of 1%:** unchanged (not a fee; not yet measured).
- **Implementation:**
  - 16B: its constant, asserted against `fees.json`;
  - F4: right after `import f2_run as F2R`, F4 sets `F2R.C_LONG` / `F2R.C_SHORT` from `fees.json` (asserted). E11 imports `forward_ls_f4`, so it uses the same module object;
  - `f2_run.py` / `f7_run.py` (locked research) are not edited.

## Consequences (accepted and recorded)

1. **A one-time level jump on the first day with the new fee.** Both recorders recompute their paper lines from PAPER_START (2026-10-15) every day. The first as-of with the new fee therefore shows the whole path at the lower cost.
   - Ledger lines already written are not changed.
   - The jump is reported in the change record.
2. **C1** (F4 LO == 16B paper within $0.01) keeps holding, because both use 0.00085 for the long fill. **C0** (E11 vs F4 LS_RS) holds for the same reason.
3. **F4 gate D3 (day 90):** the reference becomes `logs/research_1d_true_fee/equity_MAIN_AI_R1_RS.csv` (SHA in the re-run results), so live and reference use the same costs. Gates D1 and D2 are unchanged.
4. **16B pass rule (AUC):** cost-free, unchanged.
5. **ECO:** it reads F4's positions and equity. Its weight history file (`deploy/eco_history_daily_returns.csv`) stays as frozen in its config (ECO amendment needed to change it). Not changed here.
6. **The 16B verifier V4** tests that the paper engine reproduces the Step 27 research sleeves, which used 0.25%. V4 now passes cost 0.0025 explicitly. The engine-identity test is unchanged in meaning.

## Effective time

The next scheduled runs: 16B at 07:30 IST and F4 at 07:45 IST on 2026-10-26 (as-of 2026-10-25).

## Tests before deploy (VM, in a /tmp project mirror: new `src` + `deploy`; `data` / `logs` read through symlinks; all writes redirected)

- **K1:** `preflight_f4.py` passes (2 days, chain, C1 True on day 2).
- **K2:** `preflight_shadow_e11.py` passes (C0 True).
- **K3:** on the real logged as-of 2026-10-24 with the real 16B prediction files, in memory, nothing written:
  - (a) the old-fee 16B paper and F4 lines equal the logged equity files of 2026-10-24 within $0.01 (proof that the harness is right);
  - (b) with the new fee, C1 holds within $0.01;
  - (c) the new-fee LS_RS / LO / 16B equities are reported next to the old ones.
- **K4:** `verify_forward_multi_16b.py V4` PASS with the explicit research cost.
