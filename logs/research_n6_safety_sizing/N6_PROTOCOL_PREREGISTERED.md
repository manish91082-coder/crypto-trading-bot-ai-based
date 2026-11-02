# N6: live-safety rules (trial T19) and AI sizing (trial T20) on the current best portfolio, pre-registered 2026-10-20, before any N6 number is computed

**Parents.**
- N1 `20ffc364…` (T15 PASS, FINAL K1 = no stops)
- N3 `2776e1df…` (T17 PASS: X2 routing + X3 funding guard)
- N5 `da95e8a1…` (T18 FAIL: the AI had skill, AUC 0.547 for E, but skipping trades cut portfolio Calmar)

**User decision (2026-10-20).** The user asked Claude to decide the next steps. Claude chose to spend the last 2 trials on:
- (T19) safety rules needed before any live use;
- (T20) AI sizing instead of AI skipping.

After N6, **20 of 20 trials are used**.

**Base.** N1 K1 + X2 + X3 (the N3 FINAL), dev Calmar 3.648.

**Disclosed.** The ensemble model E and the idea of sizing were chosen after seeing the N5 results. The random-sizing control and the DSR with the full trial count are the guards against this.

Research only. No orders, no money.

## T19: safety (cost-of-safety test, not an alpha test)
Variants:
- **S1, catastrophe stop.**
  - A fixed price stop at entry × (1 − 0.35) for longs and entry × (1 + 0.35) for shorts, on every A/B/C sub-position (perp or spot).
  - It is scanned on 1h bars with N1's fill rule (stop, or the worse open on a gap).
  - Rationale: at 1× a perp short is liquidated near +99%. A 35% stop caps a single position's loss well before that, and stays far outside normal trend noise.
- **S2, per-coin entry cap.**
  - A new A/B/C entry is scaled down so that the coin's absolute net notional stays ≤ 0.20 × E_m.
  - The net notional is Σ over open positions in that coin (A, B, C and D legs) of side × w × close[a] / entry, plus the new side × w.
  - If nothing fits, the entry is skipped. Entries are processed in N1's heat order (hour, sleeve, coin, TF, family).
  - The cap applies at entry only; positions are not trimmed later. The realised maximum is reported.
- **S3** = S1 + S2.

**Acceptance (each variant):**
- dev Calmar ≥ 0.90 × base;
- P1 Calmar ≥ 0.90 × base and P2 Calmar ≥ 0.90 × base;
- **and** a lower maximum single-coin net exposure (dev, hourly, computed like `posthoc_n1_exposure.py`) than the base.

**Choice.**
- S3 if acceptable;
- else whichever of S1 / S2 is acceptable with the higher dev Calmar;
- else none.

P3 is reported. The chosen safety rule becomes part of the base for T20 **and** of the forward paper recorder.

## T20: AI sizing (model E from N5, out-of-sample predictions already stored in `N5_predictions.parquet`)
**Multiplier for an A/B/C trade entering in month M (from 2021-01):**
- med, sd = median and std of ALL stored out-of-sample p_E of trades that entered before the start of M. At least 3 earlier test months are needed, else m = 1.
- m_raw = clip(1 + (p − med) / (2·sd), 0.5, 1.5).
- m = m_raw / mean(m_raw computed with the same med and sd over those earlier predictions). This keeps the average exposure near 1.
- Trades before 2021-01 and D legs use m = 1.

Weights = base weight × m, applied before the T19 cap, if the cap is adopted.

**Gates (all):**
- Dev Calmar > base Calmar (base = N3 FINAL + the T19 choice);
- **and** > the 95th percentile of 100 random-sizing runs, in which the same multipliers are permuted within each entry month (seed 20261028 + i);
- Calmar > base in P1 (2021-01 … 2023-12) and in P2;
- DSR ≥ 0.95, with N = 14 + 5 + 7 + 2 + 4 + 3 + 3 + 1 = 39 and the SR variance over every configuration so far.

P3 is reported.

## Verifier `src/audits/verify_n6.py` (own code)
1. 200 random S1 stop outcomes from the raw 5m data.
2. The S2 cap weights of 300 random entries recomputed with own sequential code.
3. The T20 multipliers of 300 random trades recomputed from the prediction file.
4. Gate booleans from the result files.
5. SHAs and registry T19 / T20.

Any change after the lock goes into `CODE_CHANGES_AFTER_LOCK.md`.
