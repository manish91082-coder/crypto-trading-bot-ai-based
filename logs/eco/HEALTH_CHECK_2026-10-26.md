# VM health check: 2026-10-26, about 15:20 UTC (read-only, plus the verifiers re-run by hand)

## VM
- **Uptime:** 9 days 22 h. **Disk:** 35% used (17 / 48 GB). **Memory:** 3,199 MB available of 3,908.
- **Installed crontab** SHA256 `b04c384dd3c0…`, equal to `deploy/crontab.txt`.

## Cron status, last 48 h (`logs/cron_status/*.csv`)
Every scheduled job ran with exit code 0, and there were no non-zero exits in the last 48 h:
- ECO_Demo / ECO_Shadow: 35 runs each;
- ECO_Plan, EMO_Meter, LogShip: 48 runs each;
- ECO_Alerts: 120 runs;
- PaperN1: 24 runs;
- all the daily jobs.

F6_DemoOps last ran on 2026-10-24. That is expected, because it was retired at the cut-over.

## Verifiers re-run by hand at about 15:20 UTC

| Verifier | Result | Last state |
|---|---|---|
| verify_eco_live data/eco_demo | 11 checks, FAIL 0 | 35 cycles; eco equity 9,891.34 (start 10,000); weights 1D 0.539 / N1 0.461; 24 symbols |
| verify_eco_live data/eco_shadow | 11 / 0 | eco equity 9,892.06 |
| verify_eco_live data/eco (plan, since 2026-10-22) | 11 / 0 | 118 cycles; eco equity 10,030.20 |
| verify_eco_tracking | 4 checks, **K1 FAIL** (see below), K2–K4 PASS | 0 full days, so no gate yet |
| verify_paper_spot_s1 --fresh | 5 / 0 | 1 record (D 2026-10-25, buy at 80,154.09, equity 999.15) |
| verify_sleeve_a_forward | 1 / 0 | verdict pending; F1 ends 2026-10-27 04:00 UTC and is evaluated by the 04:35 UTC job |
| verify_paper_live data/paper_n1 | 5 / 0 | equity 9,731.41 (start 10,000), 5 days |
| verify_emotion_live | 5 / 0 | 25/25 symbols |

## The K1 FAIL in the hand run is a timing effect, not a defect

**How K1 works.** The tracking report (`logs/eco/tracking/tc_report.json`) stores the SHA of both ledgers at its run time (02:05 UTC). K1 compares that SHA with the ledgers on disk *now*.

**Why the hand run failed.** The ledgers are append-only and gained 13 hourly cycles after 02:05. Checked on the VM:
- the report's SHA equals the SHA of the first 22 lines of each ledger;
- each ledger now has 35 lines.

**The scheduled run passed.** The cron verifier runs right after the report (the same cron line). It exited 0 at 02:05:02 UTC (`ECO_Tracking.csv`), and the verifier exits 1 on any FAIL.

**Conclusion.** No action is needed. The check is only meaningful in the scheduled order.

## Tracking day 2026-10-25 (partial day, cut-over 04:21 UTC)
- **Demo − shadow:** −0.82 USDT eco.
- **Fills:** 29; slippage 2.37 bps.
- **Rejected / unconfirmed orders:** 0 / 0.
- **Funding:** demo 0.1343, shadow 0.1343.
