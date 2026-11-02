"""Synthetic test of eco_tracking.py + verify_eco_tracking.py (known answers). Writes only under a temp folder; the tracking
outputs it produces in logs/eco/tracking are removed at the end (the real run makes them).
Case A: 16 full days, d_day over tolerance on exactly 2 of the first 14 -> gate PASS.  Case B: 3 days over -> gate FAIL.
Case C: a day without a shadow cycle -> empty diff, the next day's d_day is measured from the last good day."""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

R_ = Path(__file__).resolve().parents[2]
OUT = R_ / "logs" / "eco" / "tracking"
assert not OUT.exists(), "logs/eco/tracking exists: this test must not overwrite real tracking output"
res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}")


def write(root, recs):
    root.mkdir(parents=True, exist_ok=True)
    with open(root / "ledger.jsonl", "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")


def build(tmp, jumps, skip_shadow_day=None):
    """jumps: {day index: extra demo-shadow move that day (eco units)}; day 0 = cut-over day (partial)."""
    t0 = pd.Timestamp("2026-11-01 04:21")
    D, S = [], []
    gap = 0.0
    for i in range(17):
        gap += jumps.get(i, 1.0)                     # a normal day moves the gap by 1 eco unit (< 30)
        for h in ([4, 5, 23] if i == 0 else [0, 12, 23]):
            T = (t0.normalize() + pd.Timedelta(days=i, hours=h, minutes=21)) if i else t0 + pd.Timedelta(hours=h - 4)
            base = 10_000 + 5 * i
            D.append(dict(T=str(T), mode="demo", ok=True, eco_equity=base + gap, price={"BTCUSDT": 100.0},
                          orders=[dict(perp="BTCUSDT", qty=1.0, px=100.05, reduce_only=False)], skipped=[["ETHUSDT", "inside band: |delta| 3 USDT"]],
                          notes=["order XRPUSDT -5 failed: {'code': -2019}"] if h == 12 else [], funding={"BTCUSDT": -0.1}))
            if i != skip_shadow_day:
                S.append(dict(T=str(T + pd.Timedelta(minutes=2)), mode="plan", ok=True, eco_equity=base, price={}, orders=[], skipped=[], notes=[],
                              funding={"BTCUSDT": -0.1}))
    write(tmp / "demo", D); write(tmp / "shadow", S)


def run(tmp, now="2026-11-18 02:05"):
    a = subprocess.run([sys.executable, str(R_ / "src" / "eco" / "eco_tracking.py"), "--demo", str(tmp / "demo"), "--shadow", str(tmp / "shadow"),
                        "--now", now], capture_output=True, text=True)
    v = subprocess.run([sys.executable, str(R_ / "src" / "audits" / "verify_eco_tracking.py"), str(tmp / "demo"), str(tmp / "shadow")],
                       capture_output=True, text=True)
    rep = json.loads((OUT / "tc_report.json").read_text())
    rows = pd.read_csv(OUT / "tc_daily.csv")
    return a, v, rep, rows


try:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        build(tmp, {3: 40.0, 9: -35.0})                       # 2 days over 30 -> 12/14 ok; d_cum = 14*1 + 40 - 35 - 2 + ... see below
        a, v, rep, rows = run(tmp)
        exp_cum = sum({3: 40.0, 9: -35.0}.get(i, 1.0) for i in range(15))   # gap at the end of full day 14 (day index 14)
        g = rep["gate"]
        ok("TA", a.returncode == 0 and g and g["n_day_ok"] == 12 and g["passed"] is True and abs(g["d_cum"] - exp_cum) < 1e-9
           and len(rows) == 17, f"case A: gate {g}, expected 12/14 ok, d_cum {exp_cum}, PASS")
        ok("TA-v", v.returncode == 0, "case A verifier: " + v.stdout.strip().splitlines()[-1])
        r3 = rows[rows.date == "2026-11-04"].iloc[0]
        ok("TA-x", r3.fills == 3 and abs(r3.slip_bps - 5.0) < 1e-6 and r3.rejected == 1 and r3.band_skips == 3 and abs(r3.funding_demo + 0.3) < 1e-9,
           f"execution stats day 3: fills {r3.fills}, slip {r3.slip_bps:.4f} bps (buy at 100.05 vs mark 100 = +5), rejected {r3.rejected}, band skips {r3.band_skips}")
        build(tmp, {3: 40.0, 9: -35.0, 11: 31.0})            # 3 days over -> FAIL
        a, v, rep, rows = run(tmp)
        ok("TB", rep["gate"]["n_day_ok"] == 11 and rep["gate"]["passed"] is False and v.returncode == 0, f"case B: gate {rep['gate']} (expected 11/14, FAIL); verifier rc {v.returncode}")
        build(tmp, {}, skip_shadow_day=5)
        a, v, rep, rows = run(tmp)
        r5, r6 = rows[rows.date == "2026-11-06"].iloc[0], rows[rows.date == "2026-11-07"].iloc[0]
        ok("TC", pd.isna(r5["diff"]) and abs(r6.d_day - 2.0) < 1e-9 and v.returncode == 0,
           f"case C: day without a shadow cycle -> diff empty; next d_day {r6.d_day} (2 days of +1 from the last good day); verifier rc {v.returncode}")
        a, v, rep, rows = run(tmp, now="2026-11-05 02:05")
        ok("TD", rep["gate"] is None and rows.date.max() == "2026-11-04" and v.returncode == 0,
           f"case D: only finished days counted (last {rows.date.max()}), no gate before 14 full days; verifier rc {v.returncode}")
        t = pd.read_csv(OUT / "tc_daily.csv", dtype=str, keep_default_na=False)
        t.loc[t.date == "2026-11-03", "d_day"] = str(float(t.loc[t.date == "2026-11-03", "d_day"].iloc[0]) + 0.01)
        t.to_csv(OUT / "tc_daily.csv", index=False)
        v = subprocess.run([sys.executable, str(R_ / "src" / "audits" / "verify_eco_tracking.py"), str(tmp / "demo"), str(tmp / "shadow")],
                           capture_output=True, text=True)
        ok("TE", v.returncode == 1 and "[K2 FAIL]" in v.stdout, "d_day of 2026-11-03 changed by 0.01 in the output -> verifier K2 FAIL, rc "
           + str(v.returncode))
finally:
    shutil.rmtree(OUT, ignore_errors=True)
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
