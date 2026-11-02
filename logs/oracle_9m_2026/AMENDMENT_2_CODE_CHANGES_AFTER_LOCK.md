# Code changes after the Amendment 2 lock (SHA 4c46612c)

## 1. Binomial test overflow (2026-10-26)

**Problem.** The first Part D run stopped with an OverflowError in `binom_p`. For n ≈ 2,000 calls, the float product `pk * (1 + 1e-12)` cannot hold the size of the binomial coefficient.

**When it happened.** The crash came after the lead's trade / daily / monthly files were written, but before any summary or log line about them was printed. No Part D number was seen.

**Fix.** Exact integer comparison: `comb(n, i) <= pk`. Distinct binomial coefficients differ by at least 1, so for n ≤ 272 the results are the same as before.

**Check.** After a Part C re-run, the Part C outputs are byte-identical (OUTPUT_SHA256 diff empty).

**New SHA of `src/research/oracle_9m_c.py`:** see the line below, written by the run.
new oracle_9m_c.py SHA: 8e2527034f244379991f955229cb30763ef30736b496b9726f7d6b14710f1640
