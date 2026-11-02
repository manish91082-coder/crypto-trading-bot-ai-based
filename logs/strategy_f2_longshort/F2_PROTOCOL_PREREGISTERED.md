# F1 + F2: market-neutral long-short with the existing brains (pre-registered)

Locked before any long-short result is computed. Code:
- engine: `src/pipeline_1d/f2_longshort.py`
- runner: `src/pipeline_1d/f2_run.py`
- data: `src/downloaders/download_futures_um_perp.py`
- verifier: `src/audits/verify_f2_claims.py`

Research only: NO orders, no account, no GitHub. The project rule "spot long-only" is unchanged until the user decides.

## Question
Our brains rank coins (relative skill). Spot long-only holds the TOP; can adding a SHORT book of the BOTTOM-ranked coins (USD-M perpetual, 1x) improve risk and return, especially in bear periods? The descriptive check (gross, not pre-registered) found:
- top-5 minus bottom-5: +0.50 %/day in 2021–26;
- +0.10 to +0.15 %/day in 2018–19, which is not significant.

## Data (F1)
- Binance Vision USD-M perpetual 1h klines and funding rates, 2020-01..2026-09, for every coin of the research test universe (Step 19 U, 135 coins). Every zip is SHA256-checked against its `.CHECKSUM`.
- The perp name is the first of SYM / 1000SYM / 1000000SYM with files; a 404 means it did not exist.
- **Gate F1-G1:** every downloaded file passed its checksum (log).
- **Gate F1-G2 (price scale):** for each coin, the median of perp close / spot close over common hours must lie in [0.98, 1.02]. A "1000" perp is divided by 1000 first. A coin failing this is excluded from the short book and listed.

## Design (fixed)
- **Signals:** the stored research predictions, unchanged:

  | Sleeve | Signal | Rebalance |
  |---|---|---|
  | D1 | `U_AI_predictions` (R5) | every 5 days |
  | H4 | `R6_AI` | daily, 20:00 bar |
  | H1 | `R24_AI` | daily, 23:00 bar |

  CONTROL = the stored shuffled-label predictions.
- **Long book:** exactly the research long-only rule. Top 5, kept while rank ≤ 10, next-open fills, invest 50 % of equity, spot cost 0.25 % per fill.
- **Short book (new):**
  - Selection: the 5 LOWEST-ranked members that have a perpetual bar at the decision time, kept while their rank from the bottom (among shortable members) is ≤ 10.
  - Notional: 50 % of equity in total (10 % per position) at 1x isolated margin. Margin = notional, taken from the cash that the 50 % long-only setup leaves idle.
  - Fills: at the perp's next 1h/4h/1D open.
  - Costs: 0.10 % per fill (taker 0.05 % + 0.05 % allowance); stress 0.20 %.
  - Funding: every event in the holding period; the short receives units × price × rate.
  - Liquidation: if the perp high reaches entry × (2 − 0.005), the margin is lost.
  - A coin is never long and short at the same time.
- **Mix:** M_AI3 = the mean of the three sleeves' daily equity (each sleeve $10,000), as in Step 27.
- **PRE 2018–19:** USD-M perpetuals did not exist for these coins (BTCUSDT perp started Sep 2019).
  - PRE therefore uses a SYNTHETIC short on spot prices: no funding, the same 0.10 % cost, every member shortable.
  - It is labelled "synthetic", and it is optimistic about shortability.

## Gate G0 (engine = research)
- With the short book off (invest_short = 0), the engine must reproduce the Step 27 MAIN 50 % sleeve finals within $0.01: D1 $43,151.15 · H4 $49,365.87 · H1 $69,134.22.
- It must reproduce the PRE 50 % finals within $0.01 (from `step27_combine/claims.json` `sleeve_finals.PRE_f50`).
- Otherwise the run is INVALID.

## Gates (primary: M_AI3 long-short, AI, MAIN with real perp data; ALL must hold → PASS)
| Gate | Condition |
|---|---|
| G1 | final(LS) > final(long-only 50 %) AND Calmar(LS) > Calmar(long-only 50 %) |
| G2 | MaxDD(LS) < MaxDD(long-only 50 %) |
| G3 | 2022 return of LS > 0 |
| G4 | final(AI LS) > final(CONTROL LS) |
| G5 | PRE synthetic: final(LS) > final(long-only 50 %) |
| G6 | Short cost 0.20 %: final(LS) > final(long-only 50 %) |

## Reported, no gates
- Per sleeve.
- Short-book-only P&L, funding received or paid, liquidations.
- Per-year returns.
- DSR of the LS mix, with N = 75 + the variants run here.

## Decision
- **PASS** → candidate for a paper forward log (F4), only with the user's yes.
- **FAIL** → reported. No futures trading is proposed.
