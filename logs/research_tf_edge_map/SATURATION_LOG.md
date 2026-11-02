# Saturation log (TFX-S), started 2026-10-20

## Round 1 (audit by reading; before any S-measurement)
Findings A1-A10 as listed in TFXS_PROTOCOL_PREREGISTERED.md (locked).
- Material: A1 (maker wording false). Possibly material (decided by S1-S6): A3, A4, A5, A6. Gaps: A7, A8. Minor: A2. Limitations: A9, A10.

## Round 2 (S1-S7 measured; verifier verify_tfx_saturation.py 6/6 PASS)
Material:
- R2-M1 (A3 confirmed): coin-year CIs were too narrow. Month blocks: U1 COST-VIABLE-PERP-STRICT 14 -> 0, TIMING+ 48 -> 19, TIMING+-STRICT 16 -> 2; U2X COST-VIABLE-PERP 21 -> 3. Report wording "साफ़ / STRICT" must be withdrawn; non-strict long-trend viability at 4h-1D (U1) survives, also at 2x taker cost (21 cells COST-VIABLE-2X).
- R2-M2 (A4): trend edge is TAIL-driven. U1 4h-1D trend long cells: median and 5%-trimmed excess NEGATIVE (e.g. 4h TSMOM long median -0.83%, trimmed -0.70%); top 1% of trades = 31-122% of total net P&L (corrected in round 3 audit; first logged as 49-122).
- R2-M3 (A6): year-unstable. Trend-long excess negative in 2022 and 2025 at 4h-1D (U1 and U2X); Spearman(BTC year return, long-short net) = 0.71-0.89 over 7 years at 1h-1D. "Timing works in both directions" holds only on average; the edge is mostly "be on the side of the big trend" + tail capture.
- R2-M4 (new): RSI-oversold LONG at 8h/12h/1D is the most ROBUST cell: positive median/trimmed excess and net, top-1% share 0.11-0.21, monthly sleeve Sharpe ~1.05-1.08 (U1) / 0.6-0.8 (U2X), MDD 0.20-0.27, correlation with trend-long sleeves ~0 (-0.24..+0.25); U2X P3 positive at 8h/12h (U1 P3 negative). Report line "MR 4h+ नुकसानदेह" must be split: shorting overbought = harmful; buying oversold on 8h-1D = candidate.
- R2-M5 (A1 settled): maker 5m-30m: several long MR cells MAKER-VIABLE with month blocks (5m RSI long, 15m BB/RSI/EMAX long, 30m EMAX/BB long) but P3 negative (~-0.1%) and A10 caveat (maker both sides, adverse selection; arXiv 2502.18625 live Binance maker study: fill probability vs post-fill return trade-off).
- R2-M6 (A7/A8): N_eff = 4.3 for 112 U1 sleeves, 3.9 for 40 trend sleeves 1h-1D (U2X 4.4 / 3.9). Adjacent TF same family median rho 0.57 (4h-1D). Long vs short rho -0.28; U1 trend long vs U2X trend short rho -0.33. -> more TFs add ~nothing; diversification comes from side/universe/family-type. TFX multiple-testing count for later DSR = ~5 (not 117).
- R2-M7: alt trend-short sleeves (U2X) monthly Sharpe -0.46..+0.57, MDD 0.36-1.15 -> N4 (alt shorts) is weaker than the report said.
Minor: fast-TF sleeves' monthly P&L correlated ~1 across families (cost x turnover dominates); A2 arithmetic.
-> Integrate into report (Part 2), revise N1-N5. Then Round 3 audit.

## Round 3 (audit of the integrated report; S8 number check against files)
Minor only (0 material):
- tail-share range written 49-122% -> 31-122% (1D DONCH long 31%). Fixed in report + log.
- section 0 / 8 numbering inconsistency (old "N4 = forward recorder" vs "N4 = alt shorts"); section 7 "alt shorts regime-proof" contradicted by S6. Fixed.
- rho U1 trend-long vs alt trend-short: report used -0.33 (mean, all TFs) and the table -0.34 (median 4h-1D); unified to median -0.34. Alt-short MDD lower bound 0.36 -> 0.35 (rounding).
- External rows added: Zarattini et al. 2025 (abstract), arXiv 2502.18625 (live Binance maker), DSR effective-N (secondary).
=> SATURATED at round 3 per protocol rule (one full round with 0 material findings). Open questions that research cannot answer further: N1 portfolio, N2 regime rule, N3 maker adverse selection, survivorship/alt spreads, forward evidence.

## Coverage audit (user's actual request; DISC protocol a9f46d40)
- C0 matrix written (indicators, strategies, TFs, data, math, AI classes, training, testing) with status/evidence/priority.
- C1 = D1-D6 measured. Material: SPA "money after cost" only borderline (U1 p 0.046; U2X 0.056); 7 new indicators add no independent bet (N_eff 3.98 -> 3.87); new candidates XS-mom 1D (7/7 years positive, rho 0.16), alt trend-short = crash hedge (positive in all 8 worst BTC weeks), gated carry (>= 0 every year but 0-4%/yr recently, rho 0.63, liquidation-margin risk); funding/premium-extreme contrarian shorts fail.
- C2 = re-check vs survey taxonomy (Fang et al. 2022): 3 more items (LPPLS/explosive-root bubble tests M, news/social sentiment L, portfolio optimisers partial) - none H and measurable now -> coverage saturated; remaining G1-G10 need trials/data/demo.
- verify_disc: 6/7 PASS, check 5 (D5 p-value tolerance) FAIL; post-hoc seed study: net-taker best-cell p 0.03-0.06 (borderline), excess p <= 0.005 (robust). Report updated.
