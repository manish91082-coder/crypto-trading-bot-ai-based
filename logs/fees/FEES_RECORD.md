# Fee record (evidence for `deploy/fees.json` v1, 2026-10-25)

| Item | Value | Evidence |
|---|---|---|
| Futures base maker / taker | 0.020% / 0.040% | Our own account, `GET /fapi/v1/commissionRate`, 2026-10-25, BTCUSDT / ETHUSDT / SOLUSDT: `makerCommissionRate 0.000200`, `takerCommissionRate 0.000400` (VM output in this session) |
| Futures BNB discount | 10% → 0.018% / 0.036% | Binance support article 360033544231: a 10% discount when fees are paid in BNB on USDⓈ-M futures; the BNB must be in the USDⓈ-M futures wallet |
| Spot VIP 0 | 0.100%; with BNB 0.075% (25% off) | Binance official fee page, recorded 2026-10-15 in `logs/cost_study_step2/STEP2_COST_PROTOCOL_PREREGISTERED.md`. The page could not be re-fetched from this machine on 2026-10-25. Binance.US support states the same 0.1000% / 0.0750% |
| Book impact per fill | 0.010% (median, 333–1,000 USDT) | `logs/cost_study_step2/cost_table_preliminary.csv` (21 coins, live depth snapshots) |
| Demo account | charged 0.040% taker | `/fapi/v3/account` assets: BTC 0.01, USDT 5,055.81, USDC 5,000. **No BNB.** `/fapi/v1/feeBurn` → false (2026-10-25) |

**To get the BNB rate on a real account:**
- spot: hold BNB in the spot wallet and switch on "Use BNB to pay fees";
- futures: transfer BNB to the USDⓈ-M futures wallet and switch on the BNB fee burn.

If the BNB balance is insufficient, Binance charges the base fee.
