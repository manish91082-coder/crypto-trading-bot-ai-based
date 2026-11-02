"""Claims check for FORWARD_GATE_CALENDAR.md (A3, 2026-10-28). Every number of the calendar is recomputed from its source
(VM snapshot logs/gate_calendar/vm_snapshot_2026-10-28T0850Z.txt, the protocols, deploy/eco_dd_alarm.json) and the text the
calendar must contain for it is checked. Usage: python src/audits/verify_gate_calendar.py   -> TOTAL n checks, FAIL k."""
import json
import re
import sys
from pathlib import Path

import pandas as pd

R_ = Path(__file__).resolve().parents[2]
CAL = (R_ / "FORWARD_GATE_CALENDAR.md").read_text(encoding="utf-8").replace("−", "-")   # typographic minus -> ASCII
SNAP = (R_ / "logs" / "gate_calendar" / "vm_snapshot_2026-10-28T0850Z.txt").read_text(encoding="utf-8")
res = []


def ok(t, c, m):
    res.append(bool(c))
    print(f"[{'PASS' if c else 'FAIL'}] {t}: {m}")


def has(t, text, why):
    ok(t, text in CAL, f"'{text}' in calendar ({why})")


def proto(rel, text):
    return text in (R_ / rel).read_text(encoding="utf-8")


# TC: rows of the tracking table in the snapshot
tc = pd.read_csv(pd.io.common.StringIO("\n".join(l for l in SNAP.splitlines() if l.startswith(("date,full_day", "2026-10-2")) and l.count(",") > 10)))
full = tc[tc.full_day]
has("C1", f"{len(full)}/14 दिन", f"TC full days {len(full)}")
has("C2", f"{full.d_day.iloc[0]:.2f} और +{full.d_day.iloc[1]:.2f}", f"d_day {list(full.d_day.round(3))}")
has("C3", f"कुल {full.d_cum.iloc[-1]:.2f} USDT", f"d_cum {full.d_cum.iloc[-1]:.3f}")
ok("C4", proto("logs/eco/ECO_AMENDMENT_1_PREREGISTERED.md", "|d_day| ≤ 0.30% of E0 on ≥ 12 of 14 days")
   and proto("logs/eco/ECO_AMENDMENT_1_PREREGISTERED.md", "|d_cum| ≤ 1.0% of E0") and "tol_day\": 30.0" in SNAP and "tol_cum\": 100.0" in SNAP,
   "TC rule text in amendment 1 and tolerances 30 / 100 in the live TC json")
d14 = pd.Timestamp("2026-10-26") + pd.Timedelta(days=13)
has("C5", "26 अक्टूबर से 8 नवंबर", f"14th full day = {d14.date()}")
# Sleeve A
sa = "logs/paper_n1/SLEEVE_A_FORWARD_PROTOCOL_PREREGISTERED.md"
ends = [pd.Timestamp("2026-10-24 04:00") + pd.Timedelta(hours=72 * k) for k in range(1, 7)]
ok("C6", proto(sa, "F_k = (2026-10-24 04:00 + (k − 1)·72 h, 2026-10-24 04:00 + k·72 h], for k = 1 … 6.")
   and [e.strftime("%m-%d") for e in ends] == ["10-27", "10-30", "11-02", "11-05", "11-08", "11-11"],
   f"window ends {[str(e) for e in ends]}")
ok("C7", re.search(r'"F1",\s*23,\s*"consistent"', SNAP) is not None and "F1: 23 closes, **consistent**" in CAL, "F1 23 closes consistent")
ok("C8", proto(sa, "at least 20 live closes") and proto(sa, "≥ 2 \"not consistent\", or any \"records suspect\""), "sleeve A rule text")
# MK1, FWD-WATCH, PaperN1, PaperSpotS1
n_mk1 = int(re.search(r'"n_orders": (\d+)', SNAP).group(1))
has("C9", f"{n_mk1} orders", f"MK1 n_orders {n_mk1}")
ok("C10", proto("logs/eco_maker/MK1_PROTOCOL_PREREGISTERED.md", "after ≥ 300 orders"), "MK1 decision at 300")
cl = [int(x) for x in re.findall(r'"closed_trades": (\d+)', SNAP)]
has("C11", f"FW1: {cl[0]} closed, FW2: {cl[1]} closed", f"closed trades {cl}")
ok("C12", proto("logs/fwd_watch/FWD_WATCH_PROTOCOL_PREREGISTERED.md", "≥ 80 closed forward trades")
   and proto("logs/fwd_watch/FWD_WATCH_PROTOCOL_PREREGISTERED.md", "≥ 200 closed forward trades"), "FW1 80 / FW2 200")
n_pn1 = int(re.search(r"=== PAPER_N1\nrecords (\d+)", SNAP).group(1))
has("C13", f"{n_pn1} records", f"PaperN1 records {n_pn1}")
d90 = pd.Timestamp("2026-10-21") + pd.Timedelta(days=90)
ok("C14", '"T": "2026-10-21 04:00:00"' in SNAP and d90.strftime("%Y-%m-%d") == "2027-01-19" and "19 जनवरी 2027" in CAL,
   f"PaperN1 first cycle 2026-10-21 -> day 90 {d90.date()}")
eq = float(re.findall(r'"equity": ([0-9.]+)', SNAP.split("=== PAPER_SPOT_S1")[1].split("===")[0])[-1])
has("C15", f"Equity {eq:,.2f}", f"PaperSpotS1 last equity {eq}")
ok("C16", proto("logs/paper_spot_s1/PAPER_SPOT_S1_PROTOCOL_PREREGISTERED.md", "Day 90 (2027-01-23) is a process gate"), "S1 day 90")
# DDX thresholds and band change dates
cfg = json.loads((R_ / "deploy" / "eco_dd_alarm.json").read_text(encoding="utf-8"))
b = {x["H"]: x for x in cfg["bands"]}
has("C17", f"पीला {b[30]['yellow_dd']:.2%} → {b[90]['yellow_dd']:.2%}".replace("%", "%", 1), "30 -> 90 yellow")
has("C18", f"लाल {b[30]['red_dd']:.2%} → {b[90]['red_dd']:.2%}", "30 -> 90 red")
has("C19", f"पीला {b[180]['yellow_dd']:.2%}, लाल {b[180]['red_dd']:.2%}", "180-day band")
s = pd.Timestamp(cfg["start_utc"])
ok("C20", (s + pd.Timedelta(days=31)).strftime("%m-%d") == "11-26" and (s + pd.Timedelta(days=91)).strftime("%Y-%m-%d") == "2027-01-25"
   and "**26 नवंबर**" in CAL and "25 जनवरी 2027" in CAL, "a = 31 on 2026-11-26, a = 91 on 2027-01-25")
# live state facts
ok("C21", "ECO_TELEGRAM" not in SNAP.split("=== EXTRA env keys present (names only)")[1].split("===")[0], "no Telegram key names in .env")
lx = re.findall(r"^(\S+)\.csv \{.*'exit_code': '(\d+)'\}", SNAP, re.M)
ok("C22", all(c == "0" for _, c in lx) and len(lx) >= 29, f"last exit 0 for all {len(lx)} cron_status csv files")
has("C23", "R-2026.10.28-3", "release id")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
