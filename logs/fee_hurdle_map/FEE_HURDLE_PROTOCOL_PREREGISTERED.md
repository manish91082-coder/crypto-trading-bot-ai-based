# Fee-hurdle map: how big is the BTC move per holding time, and what direction accuracy beats the cost? Locked 2026-10-27

**Purpose (user, 2026-10-27):** "the market does go up; find how direction, entry and exit can work."

Before any new rule search, this map measures **where** a rule can win at all. It is descriptive: no rule is fitted and no trade is simulated.

- **Code:** `src/research/fee_hurdle_map.py`.
- **Verifier:** `src/audits/verify_fee_hurdle_map.py` (separate code: csv/gzip/zipfile and plain loops).
- **Outputs:** `logs/fee_hurdle_map/`.
- **Report (Hindi):** `RESEARCH_FEE_HURDLE_MAP_27_OCT_2026.md`.

## 1. Data

- **5m bars:** `data/universe_hf/5m/BTCUSDT_5m_full.csv.gz` (spot BTCUSDT, UTC), 2020-01-01 … 2026-09-30.
- **1s bars, for horizons under 5m:** `data/external/binance_1s/spot_1s/BTCUSDT-1s-2026-0{1..5}.zip`, i.e. 2026-01 … 2026-05 only.
  - **The 1s HOLD months 2026-06 … 2026-09 of the micro-momentum study stay unopened.**
- **Costs from `deploy/fees.json`, as round trips:**
  - futures taker 2 × `rules.paper_futures_taker_per_side` = 0.092%;
  - spot 2 × `rules.paper_spot_per_side` = 0.17%;
  - maker 2 × (`futures_usdm.bnb_maker` + `impact_per_side`) = 0.056%.

## 2. Measurement

### Horizons
- **From 1s:** 10 s, 30 s, 1 m.
- **From 5m:** 5 m, 15 m, 30 m, 1 h, 4 h, 1 d, 3 d, 7 d, 14 d, 28 d.

### Returns
- **Non-overlapping:** the close-price grid is sampled every h, anchored at the first timestamp of the data (00:00 UTC). r = P(t+h)/P(t) − 1.
- **1s data:** each month is sampled separately (no sample crosses a month).
- **5m data:** samples with a missing endpoint bar are dropped and counted.

### Per horizon
- n;
- mean r;
- **E|r|**, the mean absolute return;
- median |r|;
- the share of |r| > each round-trip cost.

### Two derived numbers per horizon and cost RT
1. **Perfect-foresight net:** E|r| − RT. This is the average result per trade if the direction is always right and one trade is made per period. If it is ≤ 0, no direction rule can win at that horizon with one trade per period.
2. **Break-even accuracy:** p* = 0.5 + RT / (2 · E|r|).
   - **Model:** a right call earns |r|, a wrong call loses |r|, and the size is independent of being right. Then E[gross] = (2p − 1) · E|r|.
   - p* > 1 means impossible on average.
   - The independence assumption is stated in the report next to every p*.

### Stability
- For 1 h, 1 d and 7 d, E|r| and p* (futures) are also reported per calendar year, 2020 … 2026 (2026 = Jan–Sep).

## 3. Verifier checks

- **H1.** Protocol SHA and input SHAs.
- **H2.** For every horizon it recomputes n, E|r| and the share of |r| > 0.092% with its own loops, from the raw files (tolerance 1e-9 relative).
- **H3.** p* and the perfect-foresight net are recomputed from H2 and the fees.json values.
- **H4.** Output SHAs.
