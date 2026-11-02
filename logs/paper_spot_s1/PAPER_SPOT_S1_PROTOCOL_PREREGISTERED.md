# PAPER-SPOT-S1: forward paper record of the spot sleeve rule S1 (BTC above its 200-day average). Pre-registered 2026-10-25

This protocol is locked with SHA256 before the recorder's first run. **Paper only: no orders, no keys, public data only.**

## Basis

- Research `RESEARCH_SPOT_SLEEVE_24_OCT_2026.md` (protocol 0fe62438…, results 4d2c422f…).
- In that research S1 passed G1 (Sharpe ≥ BTC hold and drawdown ≥ 10 points smaller, in dev and in holdout) and G3 (profit in every period).
- **It failed G2:** the random-timing percentile was 78.5%, below the required 90%. **S1 is therefore NOT a proven edge.**
- This record exists to:
  - (1) prove that the rule can be run live, exactly as tested;
  - (2) collect forward evidence.
- It cannot authorise real money by itself.

## Rule (fixed; identical to the research)

- **Symbol:** BTCUSDT, Binance spot.
- **Data:** daily klines from `https://api.binance.com/api/v3/klines?interval=1d` (UTC days).
- **Decision at the close of UTC day D:** `in = close_D > mean(close of the 200 days ending at D)`.
- **Fill at the open of day D + 1:**
  - in and flat → buy with all the cash: qty = cash × (1 − fee) / open;
  - out and holding → sell everything: cash = qty × open × (1 − fee);
  - otherwise nothing.
- **Fee** 0.10% per side, as in the research base case.
- **Capital** 1,000 USDT virtual, i.e. 10% of the 10,000 ecosystem capital. Cash earns 0.
- **Benchmark:** BTC bought with 1,000 at the first fill-day open (one fee), held.
- **First decision day:** D0 = 2026-10-25, so the first fill is the 2026-10-26 open.
- **Catch-up:** a run processes every decision day from the last recorded D + 1 up to yesterday, in order. A missed run therefore never skips a decision.

## Record

- `data/paper_spot_s1/ledger.jsonl`: one hash-chained line per decision day D. It holds:
  - D, close_D, sma200, the signal, the action, the fill price (open D+1), qty, cash, equity at the fill-day open, and the benchmark equity;
  - the SHA of the raw klines response saved under `data/paper_spot_s1/klines/`;
  - the code and protocol SHAs.
- `data/paper_spot_s1/state.json`.

## Verifier (`src/audits/verify_paper_spot_s1.py`, own code)

| Check | What it checks |
|---|---|
| S1 | hash chain; the protocol SHA is constant; every code SHA is listed in `logs/paper_spot_s1/CODE_CHANGES_AFTER_LOCK.md` |
| S2 | every record recomputed by plain loops from its saved klines file (file SHA, close_D, sma200, the signal, the fill open) |
| S3 | cash / qty / equity / benchmark replayed by a loop from 1,000 |
| S4 | no decision day missing between D0 and the last record |
| S5 | on the VM: close_D and the fill open of the last 5 records equal a fresh public fetch |

## Reviews

**Day 90 (2027-01-23) is a process gate, not a performance gate.**
- The verifier must be all PASS on every daily run, and there must be no missing day.
- Performance (equity vs the benchmark, number of trades, drawdown) is reported as **information only**.
- With about 4 trades a year, 90 days cannot measure an edge.

**Real money:**
- Never from this record alone.
- It needs a new protocol that first resolves the G2 gap (timing vs random timing) on evidence not yet seen. The forward record after ≥ 12 months may be that evidence.
