# FWD-R2 pass/fail (written 2026-10-30, after the 08:51Z run)

**Timing, stated honestly.** This was planned to be locked before the first forward trade. It was locked after one trade had become visible: SB2 TRXUSDT, entry 2026-10-30 00:00Z at 0.3528, open, mark -5.84%. No other forward result exists. The thresholds below are the ones already written in RESEARCH_BTC_ALLTF_R2_AUDIT_30_OCT_2026.md section 6 before that trade appeared; only the evaluation date and the minimum trade count are new.

**Unit of test.** Each strategy separately: SA, SB, SB2, SC. Equal weight across the frozen coins in forward_r2_universe.json, marked to market daily, with fees from deploy/fees.json and funding.

**Evaluation date.** 2026-12-24 (8 weeks after FORWARD_START 2026-10-29T13:30Z). No earlier verdict.

**PASS needs all of:**
1. At least 30 closed trades. Fewer gives INCONCLUSIVE, and the test continues.
2. Forward CAGR > 0.
3. Forward Sharpe above half of the backtest value: SA 1.05, SB 0.79, SB2 0.76, SC 0.77.
4. Forward max drawdown below twice the backtest value: SA 24%, SB 17.4%, SB2 17.4%, SC 17.4%.

**FAIL:** at least 30 closed trades and any of conditions 2-4 not met.

**Known limit.** PEPEUSDT and MUBUSDT return no Bybit futures data under those names, so SB, SB2 and SC run on 28 of the 30 frozen coins. The list stays frozen.

A PASS only allows moving on to testnet. It is not a claim of profit.
