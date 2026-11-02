# N3: execution layer (maker entry, spot/perp venue routing, funding guard) on the N1 portfolio (trial T17), pre-registered 2026-10-20, locked BEFORE any N1 result is known

**Parents.**
- N1 (`20ffc364…`, T15) simulator; N2 (`d019c201…`, T16).
- A0 §10 / A4 maker fill model.
- The GEMV lesson: a limit order fills only when price trades THROUGH it, never by hindsight. See `REVIEW_GEMINI_NOTEBOOK_AND_RESEARCH_20_OCT_2026.md` §4.
- Gemini items #2 (venue crossover) and #3 (funding guard).

Research only.

**Base.**
- If N2 PASSES, the base is N1 FINAL + the chosen N2 regime.
- Otherwise, if N1 PASSES, the base is N1 FINAL.
- If N1 FAILS, the base is K0 and N3 is a report only (no PASS claim).

## Honest limits
- This is a historical fill model on 5m bars. Queue position is unknown, so a strict trade-through rule is used, plus a harsher stress (X1s).
- Real maker fills can only be confirmed on the demo forward run (N6). Until then a historical X1 PASS is "provisional".

## Variants (configurations of T17)
**X1 maker entry (A, B, C).**
- At the TF entry bar start t, a post-only limit at the first 5m open of that bar (the N1 entry price), valid for the 12 five-minute bars starting at t.
- **Fill:** a long fills only if one of those bars has low < limit (strictly); a short only if high > limit. The fill is at the limit, with maker fee 0.018% (0.02% × 0.9 BNB) and no spread.
- **Not filled:** a taker at the close of the 12th bar, fee 0.054%.
- The stop LEVEL is unchanged (N1 entry ∓ 3 ATR). The position path, stop scan and funding are as in N1 from hour a; only the entry price and the entry fee change. This is an approximation of the ≤ 1 h fill delay, stated in the report.
- Exits stay taker (stops must be taker).

**X1s stress.** As X1, but a fill needs a trade-through of ≥ 0.05% beyond the limit (low ≤ limit × 0.9995 for a buy). This is a queue-position proxy. X1 can be adopted only if X1s also passes Q1–Q2.

**X2 venue routing (A, B longs only).**
- At entry, spot is used instead of the perp if trailing7 × k_hold > 0.00062:
  - trailing7 = the mean funding rate of the coin's funding records in the 7 days before entry;
  - k_hold = the expected number of funding events over the hold, i.e. the PIT median hold (in hours) of the same sleeve and TF over trades that EXITED before this entry (≥ 30 such trades, else perp), divided by 8;
  - 0.00062 = spot round trip 0.17% − perp round trip 0.108%.
- Spot leg: fee 0.085% per side, no funding.

**X3 funding guard (descriptive).**
- Count of A/B/C entries whose entry time lies in (f − 15 min, f) for a funding time f, with the last known rate adverse to the side and |rate| > 0.02%.
- N1 entries are at TF bar starts, which are on the hour, and funding times are on the hour. By construction the count is expected to be 0. If the count is > 0, the rule (delay the entry to f) is simulated as one more configuration.

## Measurements and gates
- **Report:**
  - fill rate;
  - mean net R of filled vs unfilled entries (adverse selection);
  - the implementation shortfall per entry vs an immediate taker at the TF open: side × (fill − open) / open + fee_used − 0.00054;
  - the share of long entries routed to spot;
  - the funding saved by X2.
- **Q1.** Dev Calmar > base dev Calmar.
- **Q2.** Calmar > base in P1 **and** in P2.
- **Q3 (X1 only).** The mean implementation shortfall < 0, with the calendar-month block-bootstrap 95% CI upper bound < 0 (2,000 draws, seed 20261026).
- **Q4 DSR ≥ 0.95.** N = 14 + 5 + the N1 configuration count + 2 (N2) + the N3 configuration count (3, or 4 with X3).
- **FINAL N3** = the base + every variant that passed. If both X1 and X2 pass, their combination is also run and reported. It is adopted only if it passes Q1–Q2 against the base.
- **P3** reported (seen).

## Outputs and verifier
- **Outputs.** `logs/research_n3_execution/`: `N3_results.csv`, `N3_fills.parquet` (per entry: limit, filled, fill price, shortfall), `N3_routing.csv`, `claims_n3.json`, `run_log.txt`.
- **Verifier.** `src/audits/verify_n3.py`, own code:
  1. 300 random entries: maker fill and price recomputed from the raw 5m data.
  2. 200 random X2 decisions: trailing funding and k_hold recomputed.
  3. Shortfall statistics and gates from the files.
  4. SHAs.

Any change after the lock goes into `CODE_CHANGES_AFTER_LOCK.md`.
