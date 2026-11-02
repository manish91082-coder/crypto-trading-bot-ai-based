# Methods bench: changes and pre-run records

- **2026-10-26, before any Batch 1 number:** pre-run test of `fast_control` (CODE_NOTES 1) against the stored random controls of the 10 BTC-entry finals.
  - **First attempt: 0/10.** `fast_control` treated trades as closed intervals [t, x], while `random_control` uses half-open [t, x) (a trade may start at the previous exit bar).
  - **Fixed** to half-open.
  - **Second attempt: 10/10 identical** (p95 and median within 1e-12; `run_log.txt`).
- `src/research/methods_bench.py` at the start of the Batch 1 run: 46b16cd68525195c28e1315a7b0a9a8dc3c24db995c6d9d5acd684cd52b2bdaf.