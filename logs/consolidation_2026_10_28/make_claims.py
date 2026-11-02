"""Writes claims.json for CONSOL-2026-10-28. Each claim ties a value printed in the report to an exact
substring of its locked source file. 'num' (optional) must equal a number found in the substring (within tol)."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
VM = "logs/consolidation_2026_10_28/vm_snapshot.txt"
R = {i: p for i, p in enumerate([
    None,
    "RESEARCH_SPOT_DCA_SPOT_FUTURES_24_OCT_2026.md", "RESEARCH_SPOT_SLEEVE_24_OCT_2026.md",
    "RESEARCH_ECO_MONTHLY_OUTLOOK_25_OCT_2026.md", "RESEARCH_ROOT_CAUSE_25_OCT_2026.md",
    "RESEARCH_BTC_DIRECTION_ENTRY_EXIT_25_OCT_2026.md", "RESEARCH_METHODS_CATALOG_26_OCT_2026.md",
    "RESEARCH_MANUAL_10_DAYS_BTC_26_OCT_2026.md", "RESEARCH_ORACLE_9M_2026_PART_A_B_26_OCT_2026.md",
    "RESEARCH_ORACLE_9M_2026_PART_C_D_26_OCT_2026.md", "RESEARCH_NONPRICE_NP1_NP3_26_OCT_2026.md",
    "RESEARCH_METHODS_BENCH_BATCH1_26_OCT_2026.md", "RESEARCH_GREEN_CANDLE_JAN_2026_27_OCT_2026.md",
    "RESEARCH_MICRO_MOMENTUM_1S_2026_27_OCT_2026.md", "RESEARCH_FEE_HURDLE_MAP_27_OCT_2026.md",
    "RESEARCH_DRAWDOWN_DDX_27_OCT_2026.md", "RESEARCH_METHODS_BENCH_BATCH2_27_OCT_2026.md",
    "RESEARCH_TURN_DETECT_2026_27_OCT_2026.md"])}

C = []
def c(cid, value, src, substr, num=None, tol=0.0):
    C.append(dict(id=cid, value=value, source=src, substr=substr, num=num, tol=tol))

# 1 spot DCA
c("dca_final", "2,617", R[1], "10,000 USDT **2,617** रह गए (−73.8%", 2617)
c("dca_dd", "−89.9%", R[1], "max drawdown **−89.9%**", -89.9)
c("dca_win", "97%", R[1], "**97% trades profit में बंद हुए**", 97)
c("dca_hold_pct", "2nd percentile", R[1], "(2nd percentile)")
c("short30", "−13.1%", R[1], "औसत **−13.1%** प्रति trade", -13.1)
c("carry_cagr", "~4.6%", R[1], "**CAGR ~4.6%, drawdown ~1%**", 4.6)
c("carry_2026", "+2.2%", R[1], "2026 (सितंबर तक) +2.2%", 2.2)
c("carry_corr", "0.12", R[1], "ECO–carry 0.12", 0.12)
c("btc_30d", "+133%", R[1], "30 दिन में **+133%**", 133)
# 2 spot sleeve
c("s1_g2", "78.5%", R[2], "**78.5%** रहा", 78.5)
c("s6_cagr", "+2.4%", R[2], "CAGR सिर्फ़ +2.4%", 2.4)
c("s5_hold", "−17.4%", R[2], "**2024–26 में −17.4% सालाना", -17.4)
# 3 monthly outlook
c("p3_median", "9,985", R[3], "**9,985 USDT** (−0.15%)", 9985)
c("p3_worst", "9,132", R[3], "**9,132 USDT** (−8.7%, फ़रवरी 2026)", 9132)
c("p3_best", "10,714", R[3], "**10,714 USDT** (+7.1%, अगस्त 2026)", 10714)
c("p3_posm", "12 में 6", R[3], "12 में 6 (50%)")
c("exec_gap", "1.2%", R[3], "**1.2% का फ़र्क**", 1.2)
c("months23", "2–3 महीने", R[3], "कम से कम 2–3 महीने चलने दें")
# 4 root cause
c("n1_p3", "−12.5%", R[4], "P3 में **−12.5% सालाना**", -12.5)
c("d1_p3", "+15.6%", R[4], "+15.6% सालाना, drawdown सिर्फ़ 12.6%", 15.6)
c("n1_corr", "0.71", R[4], "(साल-दर-साल BTC से correlation 0.71)", 0.71)
c("eco_p3", "−0.3%", R[4], "| ECO-W2 (deployed) | +65.9% | −0.3% |", -0.3)
c("kpi", "हर quarter positive, drawdown 15% से कम", R[4], "\"हर quarter positive, drawdown 15% से कम\"")
c("posdays", "48%", R[4], "पिछले साल 48% दिन positive थे", 48)
c("p5m", "71%", R[4], "| 5m | 0.19% | **60%** | **71%** | 47–49% |", 71)
c("rc_check", "§5.4", R[4], "**यह अगला ज़रूरी check है।**")
# 5 BTC direction
c("n990", "990", R[5], "**990** configurations test हुईं", 990)
c("ai_t", "−4.3", R[5], "t = −4.3", -4.3)
c("cal168", "168", R[5], "168 में से किसी भी (दिन, घंटा) bucket का dev में t > 2 नहीं था", 168)
# 6 catalog
c("cat139", "139", R[6], "| A दिशा | 139 |", 139)
# 7 manual
c("manual_in", "+8.2%", R[7], "कुल **+8.2% net**", 8.2)
# 8 oracle A/B
c("v1a", "−82.5%", R[8], "**−82.5%**", -82.5)
c("v1b", "−27.1%", R[8], "**−27.1%**", -27.1)
c("n272", "272", R[8], "272 नए दिनों पर **फ़ेल**", 272)
# 9 oracle C/D
c("cd_gross", "+0.002%", R[9], "सिर्फ़ **+0.002%** है", 0.002)
c("cd_lead", "0/6", R[9], "**फ़ेल** (0/6 साल)")
c("mirror", "mirror edge", R[9], "\"Mirror edge\" असल में था ही नहीं")
# 10 non-price
c("np1_14", "18 में से 14", R[10], "18 में से 14 (feature, समय) जोड़े")
c("np_ic", "0.04–0.08", R[10], "संकेत की ताकत IC लगभग 0.04–0.08 है")
c("np4", "−0.123%", R[10], "**−0.123%**", -0.123)
c("noliq", "liquidation", R[10], "| Liquidations | **उपलब्ध नहीं** (Binance इसे public नहीं देता) | — |")
# 11 batch 1
c("b1", "0/567", R[11], "(0/567)")
# 12 green candle
c("gc0", "12 में से 0", R[12], "**12 में से 0 configurations पास**")
c("pgg", "45–49%", R[12], "45–49% है")
# 13 micro
c("micro0", "0 / 180", R[13], "| **0 / 180** | **0 / 180** |")
c("rhythm", "+0.0019%", R[13], "**+0.0019%**", 0.0019)
# 14 fee map
c("p1h", "61.8%", R[14], "| 1 घंटा | 0.391% | +0.299% | 61.8% |", 61.8)
c("p1d", "52.2%", R[14], "| **1 दिन** | 2.117% | +2.025% | **52.2%** |", 52.2)
c("p7d", "50.7%", R[14], "| **7 दिन** | 6.177% | +6.085% | **50.7%** |", 50.7)
c("maker513", "51.3%", R[14], "52.2% से घटकर 51.3%", 51.3)
# 15 DDX
c("al30", "7.4% / 9.4%", R[15], "| ≤ 30 दिन | 7.4% | 9.4% |")
c("al90", "11.1% / 14.7%", R[15], "| ≤ 90 दिन | 11.1% | 14.7% |")
c("al180", "14.1% / 18.0%", R[15], "| ≤ 180 दिन | 14.1% | 18.0% |")
c("al365", "17.5% / 22.1%", R[15], "| ≤ 1 साल | 17.5% | 22.1% |")
c("ddx6", "6 बार", R[15], "हर तरीक़ा fail हुआ, 6 बार।")
c("paths", "10,000", R[15], "stationary bootstrap किया गया: 10,000 रास्ते", 10000)
# 16 batch 2
c("b2", "0/972", R[16], "(0/972)")
c("dsr035", "0.35", R[16], "सबसे ऊँचा DSR 0.35 था", 0.35)
c("n1539", "1,539", R[16], "1,539 primary configs", 1539)
# 17 TURN
c("lag62", "62 मिनट", R[17], "62 मिनट और 57% चाल निकल जाती है")
c("leg57", "57%", R[17], "62 मिनट और 57% चाल निकल जाती है", 57)
c("s296", "296", R[17], "296 setups", 296)
c("auc", "0.53–0.55", R[17], "(AUC 0.53–0.55)")
c("t40", "~40 turns", R[17], "~40 turns")
# ecosystem records
c("fee_fut", "0.018%, taker 0.036%", "logs/fees/FEES_RECORD.md", "10% → 0.018% / 0.036%")
c("fee_demo", "0.040%", "logs/fees/FEES_RECORD.md", "charged 0.040% taker", 0.040)
c("fee2_dep", "14:20 UTC", "logs/fees/FEE_AMENDMENT_2_RESULTS.md", "## Deployment (VM, 2026-10-25 14:20 UTC)")
c("tf_r0", "0.1499", "logs/research_1d_true_fee/TRUE_FEE_1D_RESULTS.json", "\"p3_2025_10_on\": 0.14985460523281935", 0.1499, 0.00005)
c("tf_r1", "0.2377", "logs/research_1d_true_fee/TRUE_FEE_1D_RESULTS.json", "\"p3_2025_10_on\": 0.23771253590112118", 0.2377, 0.00005)
c("ls_rec", "Not deployed", "logs/log_ship/CODE_CHANGES_AFTER_LOCK.md", "**Not deployed.** The live VM still runs v6")
c("f7_period", "2021-01-01..2026-09-30", "logs/strategy_f7_risk/F7_PROTOCOL_PREREGISTERED.md", "## Runs (MAIN 2021-01-01..2026-09-30")
c("mk1_300", "300", "logs/eco_maker/MK1_PROTOCOL_PREREGISTERED.md", "300")
c("s1_d90", "2027-01-23", "logs/paper_spot_s1/PAPER_SPOT_S1_PROTOCOL_PREREGISTERED.md", "**Day 90 (2027-01-23) is a process gate, not a performance gate.**")
# VM snapshot
c("vm_cron", "13443469f4ec", VM, "crontab_l_sha256 13443469f4ec6508e1e74708fa0e955e315836332fc66f27205b43a30e457de7")
c("vm_demo_dd", "1.775%", VM, "peak 10061.770683621337 maxDD_pct 1.775", 1.775)
c("vm_demo_n", "74 cycles", VM, "data/eco_demo cycles 74")
c("vm_demo_eq", "9,933.6", VM, "last None 9933.615177383028", 9933.6, 0.05)
c("vm_shadow_dd", "1.78%", VM, "data/eco_shadow first None 9997.881614351843 last None 9937.171525332424 peak 10063.225762254548 maxDD_pct 1.78", 1.78)
c("vm_tc", "−1.25", VM, "2026-10-27,True,9927.132308,9928.379444,-1.247136234", -1.25, 0.005)
c("vm_sleeve", "consistent", VM, "\"verdict\": \"consistent\"")
c("vm_sleeve_p", "pending", VM, "\"verdict\": \"pending\"")
c("vm_mk1", "39", VM, "\"n_orders\": 39", 39)
c("vm_fw1", "5", VM, "\"closed_trades\": 5,", 5)
c("vm_fw2", "10", VM, "\"closed_trades\": 10,", 10)
c("vm_liq", "28,973", VM, "2026-10-27,2026-10-27.jsonl.gz,28973", 28973)
c("vm_logship", "64", VM, "logship_runs_since_2026-10-25T13:36Z 64 nonzero 0", 64)
c("vm_spot", "1,008.57", VM, "\"equity\": 1008.5698271354588", 1008.57, 0.005)
c("vm_n1", "9,764.7", VM, "\"equity\": 9764.72781691861", 9764.7, 0.05)
c("vm_disk", "36%", VM, "48G   17G   31G  36% /", 36)
c("vm_mem", "3,288", VM, "3908         620        2587           0         991        3288", 3288)
c("vm_fees", "b76c0495", VM, "b76c04950e0922f4cbec27bc9bd4ded5a500fae600dd1aa444930a8a92d491a5  deploy/fees.json")
c("vm_ls_sha", "aca75629", VM, "aca7562982946ac1e09644e58defbb59d7d56274d188b6c8a86de17f963f1d57  deploy/ship_logs_drive.py")
c("vm_ls_time", "13:36:32", VM, "2026-10-25 19:06:32.872850291 +0530 deploy/ship_logs_drive.py")

(HERE / "claims.json").write_text(json.dumps(C, ensure_ascii=False, indent=1), encoding="utf-8")
print("claims", len(C))
