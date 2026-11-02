# Methods bench: code notes (written before any Batch 1 result)

1. **The fast random control `fast_control`** gives the same numbers as `btc_entry_study.random_control`. Why the two agree:
   - Candidates are taken in the same seeded permutation order, and the direction draws are the same `rng.random()` stream.
   - The stream is drawn in one block (PCG64 gives the same sequence either way).
   - A candidate whose interval already overlaps an accepted trade is skipped. Because the accepted set only grows, a candidate that is blocked at some point stays blocked at every later point.
   - So pre-filtering against the occupancy at the start of each chunk, then checking the survivors one by one, accepts exactly the same trades as the bar-by-bar loop.
   - **Pre-run test:** before any Batch 1 result, `fast_control` must equal `random_control` for the 10 finals of the BTC entry study (their stored p95). See CODE_CHANGES.
2. **X3 control (amendment 1 §3).** The holding length of candidate j is holds[j mod m], where holds is a seeded permutation of the configuration's own H holding lengths (m of them). That is a draw without replacement, cycling.
   - It exits at the close of bar t + hold. The gross is dir × (close / next open − 1). Funding counts as in X3.
3. **The FULL period** runs over bars [0, last). Days in exchange data gaps appear in the daily report with n = 0 and the equity carried.
4. **R-delay:** the signal array shifted by one bar (the decision at bar t uses the signal of t − 1); everything else is the same.
