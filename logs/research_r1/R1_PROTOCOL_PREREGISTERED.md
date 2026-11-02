# Round 1: improvements to the F7 long-short (E3, E1, E2, E4, N1, E11), pre-registered

Locked before any Round 1 result exists.
- Engine: `src/pipeline_1d/r1_engine.py` (a copy of the F7 engine with optional hooks; `f7_risk.py` is NOT edited, because F4 runs on it)
- Runner: `src/pipeline_1d/r1_run.py`
- Verifier: `src/audits/verify_r1_claims.py`
- Synthetic unit tests: `src/audits/test_r1_engine_synthetic.py`

Research only, no orders, no GitHub. Roadmap: `FINAL_ROADMAP_METHODS_16_OCT_2026.md`.

## Common design (identical to F7 unless stated)
- **Period, signals and costs:** MAIN 2021-01-01..2026-09-30; the same stored research predictions (D1 / R6 / R24); the same costs (spot 0.25 %, perp 0.10 % per fill).
- **Mechanics as F7:** sleeves $10k each, mix = mean of the three; perp scale gate; funding settles in the isolated margin.
- **F7 rule set RS on every short, and on the BTC hedge:** stop at entry × 1.50 checked every bar (gap → open × 1.01, else stop × 1.01); 30-day cooldown after a stop or liquidation.
- **Baseline:** F7 RS (claims `logs/strategy_f7_risk/claims.json`): final $88,400.87, max DD 21.37 %, Calmar 2.159, 2022 +36.54 %, 0 liquidations. Short side (all sleeves): PF 1.07, payoff 0.81. Long side: PF 1.22, payoff 1.57 (`logs/performance_summary/summary.json`).
- **G0 (engine = F7):** with every new option off, `r1_engine` must reproduce the F7 RS sleeve finals and the F7 OFF_LO / OFF_LS sleeve finals within $0.01. Else INVALID.
- **Definitions:**
  - "perp age" at time t = t − the first bar of the coin's perp in `data/futures_um` (the files start 2020-01; a pre-2020 perp therefore has age ≥ 366 days at every 2021+ decision);
  - σ60 = standard deviation of the last 60 daily close-to-close returns up to the decision day;
  - MAX7 = largest daily close-to-close spot return of the last 7 days up to the decision day (all known at the decision).
- **Controls:** each control runs 10 seeds (0..9). "Control median" = median over seeds.
- **Trials:** DSR is reported with N = 83 (F7) + the strategy runs below (E3b, E1a, E1b, E2, E4, N1a, N1b, E11 = 8) = **91**.

## E3: listing-age diagnostic (no adoption decision; tells whether the AI short skill is real)
- **E3a:** bucket every F7 RS short trade by perp age at entry: < 60 / 60–180 / 180–365 / ≥ 365 days. Report the P&L share, PF and count per bucket.
- **E3b AGE rule:** the F7 RS engine, long book unchanged, but the short book picks the 5 shortable members with the YOUNGEST perp (no AI).
- **E3c age-matched random:** for every AI bottom pick, a random shortable member from the same age bucket (seeds 0..9).
- **Reading rule (fixed now):** if E3b short P&L ≥ 80 % of F7 short P&L, OR the E3c median short P&L ≥ 80 % of F7 short P&L, then report: "AI short skill not shown beyond listing age". Otherwise: "AI short adds beyond listing age".

## E1: part of the short book as a BTC hedge
**Rule:**
- A BTCUSDT perp short with notional = w × 50 % × equity.
- The AI bottom-5 alt shorts get (1 − w) × 50 % × equity, split equally (w = 1 → no alt shorts).
- The hedge is opened at the first decision and re-set to its target at each decision only when its notional drifts more than 25 % from the target (cover, then re-short).
- Stop × 1.50 applies to the hedge too. After a hedge stop, it is re-opened at the next decision (no cooldown for the hedge).
- The hedge is separate from the AI books: a long spot BTC position may coexist with it.

**Variants:** E1a w = 0.5; E1b w = 1.0.

**Gates (each variant):**
- G1 max DD ≤ 21.37 %
- G2 final ≥ 0.80 × 88,400.87
- G3 2022 > 0
- G4 the worst short-side day (sum of short P&L marks) is not worse than F7's
- G5 final > control median (same w, alt shorts from shuffled AI ranks)

## E2: alt-short entry filters (freed notional goes to a BTC hedge)
**Rule:** a coin is shortable only if all three hold at the decision:
- (a) the mean of its last 9 funding rates ≥ −0.0003;
- (b) perp age ≥ 60 days;
- (c) its 30-day mean perp quote volume ≥ 25 % of the median of that value among the shortable members that day.

Each empty short slot (fewer than 5 pass) puts its 10 % notional into a BTCUSDT perp short (hedge mechanics as E1).

**Gates:**
- G1 short PF > 1.07 AND short payoff > 0.81
- G2 max DD ≤ 21.37 %
- G3 final ≥ 0.80 × F7
- G4 2022 > 0
- G5 short PF > control median (at each decision drop the same number of shorts at random; freed notional to BTC the same way)

## E4: inverse-volatility weights inside each leg + per-coin cap
**Rule:**
- For each leg, at each decision, weights over the target set (kept + new): w_i ∝ 1/σ60_i (spot σ for longs, perp σ for shorts).
- Each weight is capped at 30 %; the excess is redistributed pro rata, iterating until no weight exceeds the cap.
- A NEW position gets leg budget (50 % × equity) × w_i. Kept positions are not resized (as F7).

**Gates:**
- G1 max DD < 21.37 %
- G2 worst calendar-week mix return > F7's worst week
- G3 final ≥ 0.85 × F7
- G4 2022 > 0
- G5 max DD < control median (random Dirichlet(1) weights, same cap)

## N1: lottery (MAX) filter
⚠ **Disclosure:** on 2026-10-16 a descriptive look at Step 19 rows found monotonic underperformance of high-MAX7 coins (top quintile beat the median 41.5 % vs 52.6 % for the bottom quintile). Passing here is therefore WEAK evidence; the F4 shadow log is the judge.

**Variants:**
- **N1a:** at each decision, the members in the top 20 % of MAX7 among that decision's ranked members are not eligible for NEW long entries (the next ranks fill). Shorts unchanged.
- **N1b:** N1a + short candidates = the 10 lowest AI ranks among shortable members, reordered so that top-20 %-MAX7 coins come first (AI order kept within each group), taking the first 5.

**Gates (each variant):**
- G1 long-side PF > 1.22 AND long payoff > 1.57
- G2 max DD ≤ 21.37 %
- G3 final ≥ F7 (N1a) / final > F7 (N1b)
- G4 2022 > 0
- G5 long PF > control median (exclude the same number of long candidates at random)

## E11: long leg on USDT-M perps
**Rule:**
- A NEW long is opened on the coin's perp if it has a perp bar at the fill time and passes the F7 scale gate; otherwise on spot.
- Perp longs: cost 0.10 % per fill, 1x isolated, funding paid by the long (units × price × rate is deducted from its margin when the rate is positive, added when negative), liquidation by the F7 margin rule mirrored (margin + units × (price − entry) ≤ 0.005 × units × price, checked on the bar low).
- No stop on longs (F7 has none).

**Gates:**
- G1 final > F7
- G2 max DD ≤ 21.37 % + 2.0 pp
- G3 2022 > 0
- Reported: total long funding paid, and the share of longs on perp vs spot.

## Decision
- A variant whose gates ALL pass becomes a candidate F4 shadow line, with its own 90-day forward clock, on the user's yes.
- Nothing replaces F7 without forward evidence.
- E3 is a diagnostic only.
- If nothing passes, F7 stays (a valid result).

## Reported (no gates)
- Per-sleeve finals, per-year returns, liquidations, stops, cooldown blocks, funding, turnover.
- The number of filter-blocked shorts (E2) and MAX-blocked longs (N1).
- DSR (N = 91).
