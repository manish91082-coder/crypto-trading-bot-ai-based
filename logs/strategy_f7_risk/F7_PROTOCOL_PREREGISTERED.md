# F7: risk rules for the long-short book (pre-registered)

Locked before any F7 result is computed.
- Engine: `src/pipeline_1d/f7_risk.py` (a copy of the F2 engine with optional rules; the F2 engine is not edited)
- Runner: `src/pipeline_1d/f7_run.py` (writes only to `logs/strategy_f7_risk/`; F2 logs are never overwritten)
- Verifier: `src/audits/verify_f7_claims.py`

Research only: no orders, no account, no GitHub.

## Honest disclosure (data already seen)
The F2 short trades have already been inspected. Among them:

| Sleeve | Short trades | Liquidations | Trades losing > 50 % of margin | P&L of those trades | Total short P&L |
|---|---|---|---|---|---|
| D1 | 626 | 27 | 34 | −$154,815 | +$60,149 |
| H4 | 1,882 | 20 | 31 | −$131,681 | +$21,394 |
| H1 | 2,070 | 22 | 32 | −$198,015 | +$48,422 |

So F7 is NOT new evidence of skill. It is a risk-control layer that the live system needs anyway: a stop order on every short.
- The rule values below are fixed by risk logic, not by searching:
  - a 1x isolated short is liquidated near +99 %;
  - a stop at +50 % caps a position's loss at about half its margin, i.e. about 5 % of the sleeve at the 10 % position size.
- Only the forward log (F4) can judge it.

## Rule set RS (primary; all three together)
- **R1 Protective stop (per short).**
  - Each short carries a stop at entry × 1.50 on the perp price. It is checked in every bar, before the liquidation and funding of that bar.
  - If the bar OPEN ≥ entry × (2 − 0.005), the position is liquidated: a gap through the stop, F2 rule, margin lost.
  - Else if OPEN ≥ stop: cover at OPEN × 1.01.
  - Else if HIGH ≥ stop: cover at stop × 1.01.
  - The extra 1 % is a stop-slippage allowance, on top of the 0.10 % short cost.
  - Funding events inside the stop bar are not applied (the position is gone).
  - This is what the live system will place: a STOP_MARKET reduce-only order at entry.
- **R2 Cooldown.** A coin that was stopped or liquidated cannot be shorted again for 30 calendar days from that exit.
- **R3 Concentration.** Unchanged from F2: at most 5 shorts, 10 % of equity each at entry, 1x isolated. With R1, a single position's notional cannot grow past about 15 % of entry equity without being closed.

**Long book:** unchanged (research rule).

**Live-only rule, NOT simulated as a trading rule:**
- **K1 kill switch:** all trading stops for the user's review if the account equity is 35 % below its peak.
- The backtest only REPORTS how often K1 would have fired (mix and each sleeve).

## Runs (MAIN 2021-01-01..2026-09-30, real perp data; the same inputs as F2)

| Run | What |
|---|---|
| OFF | Rules off. Must reproduce F2 (gate G0). |
| RS | Primary. |
| RS_cost020 | RS with 0.20 % short cost. |
| RS_CONTROL | RS with the shuffled-label CONTROL predictions. |

**Report-only variants (no gates; counted as trials for DSR):**
- RS_stop30: stop at ×1.30.
- RS_stop75: stop at ×1.75.
- RS_age30: RS plus "no short if the perp's first bar is < 30 days before the decision".

**PRE 2018–19 synthetic** (spot prices as perp, as in F2): RS. Report only.

## Gates (primary = M_AI3 mix = mean of the 3 sleeves' daily equity, MAIN, AI)

| Gate | Condition |
|---|---|
| G0 | OFF reproduces the F2 MAIN AI_LS sleeve finals within $0.01 (D1, H4, H1 from `strategy_f2_longshort/claims.json`) AND the AI_LO finals within $0.01. Else INVALID. |
| G1 | Liquidations(RS, all sleeves) ≤ 7 (≤ 10 % of F2's 69; only gaps remain possible) |
| G2 | MaxDD(RS) ≤ MaxDD(F2 LS) = 30.33 % (F2 claims) |
| G3 | final(RS) > final(LO) AND Calmar(RS) > Calmar(LO). The shorts must still be worth having. |
| G4 | 2022 return(RS) > 0 |
| G5 | final(RS_cost020) > final(LO) |
| G6 | final(RS) > final(RS_CONTROL) |

## Decision
- **PASS:** all of G1..G6 hold. RS becomes the risk rule set of the F4 paper log and of the F6 testnet code.
- **FAIL:** reported. F4 then logs plain F2 as the primary line and RS as a shadow line. The user decides.
- **INVALID:** G0 fails.

## Reported, no gates
- Per sleeve finals, stops, liquidations, cooldown blocks.
- Short P&L and funding.
- K1 trigger counts.
- Per-year returns.
- DSR of the RS mix, with N = 79 + 4 (RS and the 3 report-only variants) = 83.
