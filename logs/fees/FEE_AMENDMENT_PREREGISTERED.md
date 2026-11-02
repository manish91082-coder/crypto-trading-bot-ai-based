# Fee unification amendment (2026-10-25): one fee table for every live component

Locked before the code change.

**Amends:**
- ECO: `ECO_PROTOCOL_PREREGISTERED.md` + amendments 1 and 2 (config field `fee`).
- PAPER-N1: protocol + amendments 1 and 2 (code constants FEE, FEE_SPOT).
- PAPER-SPOT-S1: `PAPER_SPOT_S1_PROTOCOL_PREREGISTERED.md` (fee 0.10%).

Nothing else changes in any of them.

## Why (user, 2026-10-25)

- The fee assumptions differed between components and were changed several times. The user asked for the real Binance fee, paid in BNB, fixed once.
- The single source is now **`deploy/fees.json` v1**. Its evidence is in `logs/fees/FEES_RECORD.md`.

## Fee truth (`deploy/fees.json`)

| | Per side, paid in BNB | Base (no BNB) |
|---|---|---|
| Spot, buy or sell | **0.075%** | 0.100% |
| USDⓈ-M futures maker | **0.018%** | 0.020% |
| USDⓈ-M futures taker | **0.036%** | 0.040% |

- **Measured book impact:** 0.010% per fill (median, 333–1,000 USDT).
- **The demo futures account holds no BNB and has feeBurn off,** so it is charged the base taker 0.040%.

## Rules

1. **Paper recorders**, which fill at an open or mark price, book **fee (BNB) + impact** per side:
   - spot 0.085%;
   - futures taker 0.046%.
2. **ECO**, which books real fills whose price already contains the impact, books **the fee the exchange actually charges the account.**
   - Demo now: 0.040%.
   - A real account with BNB in the futures wallet and feeBurn on: 0.036%. That needs a config change at that time.

## Changes

| Component | Before | After | How |
|---|---|---|---|
| ECO `deploy/eco_config.json` `fee` | 0.00054 | **0.00040** | config v4, built by `build_eco_config.py` from `fees.json` |
| PAPER-N1 `FEE` (perp) | 0.00054 | **0.00046** | code constant + an assert that it equals `fees.json` |
| PAPER-N1 `FEE_SPOT` | 0.00085 | 0.00085 (unchanged; now asserted) | the same |
| PAPER-SPOT-S1 `FEE` | 0.00100 | **0.00085** | code constant + assert; its verifier reads it from `fees.json` |

## Effective time

- From the first cycle after deploy.
- Existing positions keep the fee they were opened with: PAPER-N1 stores the fee per position.
- No ledger history is rewritten.

## Not in this amendment (stage 2, needs its own protocol)

- **The 1D forward recorders (Step 16, 16B, F4, E11 shadow) still use C_LONG 0.25%, C_SHORT 0.10% and stop slippage 1%.**
- F4's C1 cross-check against 16B and ECO's 1D producer depend on those lines staying consistent, so they must change together, after a pre-registered 1D re-run with the true costs.

## Tests before deploy

- **ECO:** `test_eco_core.py` 43/43.
- **PAPER-N1:**
  - `python -m py_compile`;
  - the assert passes;
  - one sandbox live cycle into a scratch root with `--now` = the last real T;
  - `verify_paper_live.py` on the scratch copy.
- **PAPER-SPOT-S1:** the verifier S3 replay with the new fee on a sandbox run.
- **Every new code SHA and the config v4 SHA are listed in the components' CODE_CHANGES before deploy,** so the live verifiers' L2 / L3 / L11 / S1 checks stay PASS.
