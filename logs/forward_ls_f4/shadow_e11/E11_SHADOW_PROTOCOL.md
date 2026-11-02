# E11 shadow line of the F4 paper log (pre-registered, 2026-10-16)

**Origin:** Round 1 E11 PASSED its gates (`REPORT_R1_E11_PERP_LONGS_16_OCT_2026.md`, claims_E11.json, verifier PASS).
R1 protocol line 102: a passing variant becomes a candidate F4 shadow line on the user's yes. **User said yes on 2026-10-16.**
Paper only: NO orders, no keys, no money. Tax and real-money questions are out of scope (user, 2026-10-16).

- Code: `src/execution/shadow_e11_f4.py` (called by `forward_ls_f4.py` after its own ledger line; failures never touch the F4 ledger)
- Engine: `src/pipeline_1d/r1_engine.py` (the Round 1 engine; with its hooks off it equals the F7 engine, G0 / T0)
- Verifier: `src/audits/verify_shadow_e11.py`

## Rule (identical to R1 E11)
- F7 RS rules: 50 % long / 50 % short, top-5 long / bottom-5 short, keep 10, short stop at entry x 1.50 (+1 % slippage), 30-day cooldown, 1x isolated.
- A NEW long is opened on the coin's USDT-M perp if the perp bar exists at the fill time AND the F4 daily scale gate passes for that coin and day; otherwise on spot.
- Perp longs: cost 0.10 % per fill; funding paid when positive and received when negative; liquidation rule mirrored on the bar low. No stop on longs.
- Inputs: exactly the inputs of the F4 line of the same as-of day (16B prediction files, the F4 perp kline / funding files whose combined hash must equal the F4 ledger line, the live spot folders). No own download.
- Recomputed from PAPER_START (2026-10-15) every day, as F4.

## Daily integrity check
- **C0:** the same engine with perp longs OFF must equal F4's LS_RS sleeves (D1, H4, H1) for every date within $0.01. A C0 failure marks that day's E11 numbers untrusted.

## Clock and evaluation (fixed now)
- Forward days counted from as-of 2026-10-15. Day 90 = as-of 2027-01-12 (same as F4).
- **At day 90, E11 is a real-money CANDIDATE only if ALL hold:**
  - E1: C0 true on every day that is counted;
  - E2: E11 final (M_AI3) >= LS_RS final of the same day;
  - E3: E11 max drawdown over the forward period <= LS_RS max drawdown + 2.0 percentage points;
  - E4: total long funding paid (closed perp longs) < the cost saved by perp fills (0.15 % x 2 per closed perp long, x its cost basis), i.e. the mechanism that produced the backtest gain is visible forward.
- Otherwise F7 RS (spot longs) stays. Nothing about money is decided by this log alone; the user decides.
- Reported, not gated: on-time share, number of perp vs spot longs, funding by month.
