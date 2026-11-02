# EMO-1 closeout (2026-10-25): verdict FAIL from the dev report; holdout NOT opened; amendment for the sort fix NOT pursued

**Decision basis:** the locked protocol `EMO1_PROTOCOL_PREREGISTERED.md` (b777c510…) and the authoritative dev report `EMO1_DEV_REPORT.json` (e8f84fc42c8b…). No new number is computed here.

## 1. Why the verdict is already final

- **G3 is defined over BOTH windows.** The protocol's gate list says: "G3: Calmar of 0.8 × ECO + 0.2 × EMO > ECO alone, on both dev and holdout".
- **G3 already failed in dev.** The dev report has `"G3": false`: the mix Calmar 1.076 < ECO-W2 Calmar 2.420.
- **So no holdout result can make "all gates pass" true.** The protocol's "all must pass" can no longer be met, and EMO-1 is **FAIL** by the protocol itself.
- **Dev evidence beyond the gate:**
  - P net Sharpe −2.89, with a 95% block-bootstrap CI of −4.19 … −1.56 (wholly below 0).
  - CAGR −40.5%; max drawdown 77.5%.
  - DSR ≈ 0 at every SR variance.
  - G5 passed only because the shuffled control is even worse (median −12.2): the cost of trading every 4 h dominates.

## 2. Holdout (2025-01-01 … 2026-09-30): not opened

- Opening it cannot change the verdict (§1). It would only spend an unseen window.
- The data stays downloaded with its SHAs, and **no EMO-1 metric is computed on it**.
- Any future crowding idea that wants this window needs its own pre-registered protocol. EMO-1's results may not be tuned on it.

## 3. R1 (daily rebalance, dev Sharpe 0.37)

- R1 is a robustness run, not gated. Promoting it after seeing it would be a post-hoc trial.
- It is recorded as information only. Any follow-up needs a new protocol, counted as a new trial.

## 4. The pandas concat-sort amendment (EMO1 amendment 1 follow-up)

- **Not pursued.** Its only purpose was to future-proof re-runs of `emo1_study.py`, and EMO-1 is closed, so it would not be re-run.
- **If it is ever re-run:** pin pandas 3.0.5, the version the recorded runs used and which sorts as recorded. Then compare with a tolerance (run-to-run spread 1.43e-14 relative, see CODE_CHANGES 2026-10-24), not bit-exact.

## 5. What is NOT affected

- **EMO meter:** the live job `EMO_Meter` and its `EMO_Verify` are information only, under their own protocol (e7a20dc2…), and keep running.
- **ECO:** EMO-1 never entered ECO.
