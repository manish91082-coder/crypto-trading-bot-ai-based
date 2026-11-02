"""ECO tracking check TC (amendment 1 §5, logs/eco/ECO_AMENDMENT_1_PREREGISTERED.md): demo vs shadow, forward, not a trial.
Daily (UTC), per finished UTC day D after the cut-over:
  diff(D) = eco equity of the last ok demo cycle of D - the same for the shadow (eco units); diff at the cut-over = 0 (same adopted state)
  d_day(D) = diff(D) - diff(D-1)      d_cum(D) = diff(D)
Gate after 14 FULL days (the cut-over day is partial, not counted): |d_day| <= 0.30% E0 on >= 12 of 14 days and |d_cum| <= 1.0% E0.
Report: slippage of demo fills vs the decision mark (bps, + = worse), rejected / unconfirmed orders, band skips, funding demo vs shadow.
Usage (VM cron, daily): python src/eco/eco_tracking.py [--demo data/eco_demo] [--shadow data/eco_shadow] [--now "2026-10-26 02:05"]
Writes logs/eco/tracking/tc_daily.csv and tc_report.json (recomputed from the ledgers every run; the verifier recomputes them)."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import eco_core as C

PROJ = C.PROJ
OUT = PROJ / "logs" / "eco" / "tracking"
TOL_DAY, TOL_CUM, N_FULL, N_OK = 0.0030, 0.010, 14, 12


def load(root):
    L = [json.loads(l) for l in (PROJ / root / "ledger.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    return [r for r in L if r.get("mode") != "reset"]


def day_last(L):
    """{UTC date: eco equity of the last ok cycle of that day}"""
    out = {}
    for r in L:
        if r.get("ok") and r.get("eco_equity") is not None:
            out[pd.Timestamp(r["T"]).date()] = float(r["eco_equity"])
    return out


def run(demo_root, shadow_root, now):
    D, S = load(demo_root), load(shadow_root)
    t0 = pd.Timestamp(D[0]["T"])
    cut_day = t0.date()
    ed, es = day_last(D), day_last(S)
    today = pd.Timestamp(now).date()
    days = sorted(d for d in set(ed) | set(es) if d < today)              # finished UTC days only
    rows, prev = [], 0.0
    for d in days:
        if d not in ed or d not in es:
            rows.append(dict(date=str(d), full_day=d > cut_day, demo=ed.get(d), shadow=es.get(d), diff=None, d_day=None, d_cum=None,
                             note="no ok cycle of one instance on this day"))
            continue
        diff = ed[d] - es[d]
        rows.append(dict(date=str(d), full_day=d > cut_day, demo=ed[d], shadow=es[d], diff=diff, d_day=diff - prev, d_cum=diff, note=""))
        prev = diff
    for r in rows:
        r["day_ok"] = None if r["d_day"] is None else abs(r["d_day"]) <= TOL_DAY * C.E0
    # per-day execution stats from the demo records
    by_day = {}
    for r in D:
        if not r.get("ok"):
            continue
        d = str(pd.Timestamp(r["T"]).date())
        s = by_day.setdefault(d, dict(fills=0, slip_bps_sum_notional=0.0, notional=0.0, rejected=0, unconfirmed=0, band_skips=0, funding_demo=0.0))
        for o in r.get("orders", []):
            m = r["price"].get(o["perp"])
            if m:
                n = abs(o["qty"]) * m
                s["fills"] += 1; s["notional"] += n
                s["slip_bps_sum_notional"] += n * (1 if o["qty"] > 0 else -1) * (o["px"] / m - 1) * 1e4
        for n_ in r.get("notes", []) or []:
            s["rejected"] += n_.startswith("order ") and " failed: " in n_ and "unconfirmed" not in n_
            s["unconfirmed"] += n_.startswith("order ") and "not confirmed" in n_
        s["band_skips"] += sum(1 for x in r.get("skipped", []) if "inside band" in str(x[1]))
        s["funding_demo"] += sum((r.get("funding") or {}).values())
    for r in S:
        if r.get("ok"):
            d = str(pd.Timestamp(r["T"]).date())
            by_day.setdefault(d, dict(fills=0, slip_bps_sum_notional=0.0, notional=0.0, rejected=0, unconfirmed=0, band_skips=0, funding_demo=0.0))
            by_day[d]["funding_shadow"] = by_day[d].get("funding_shadow", 0.0) + sum((r.get("funding") or {}).values())
    for r in rows:
        s = by_day.get(r["date"], {})
        r.update(fills=s.get("fills", 0), slip_bps=(s["slip_bps_sum_notional"] / s["notional"]) if s.get("notional") else None,
                 rejected=s.get("rejected", 0), unconfirmed=s.get("unconfirmed", 0), band_skips=s.get("band_skips", 0),
                 funding_demo=s.get("funding_demo", 0.0), funding_shadow=s.get("funding_shadow", 0.0))
    full = [r for r in rows if r["full_day"]]
    first14 = full[:N_FULL]
    gate = None
    if len(first14) == N_FULL:
        n_ok = sum(1 for r in first14 if r["day_ok"])
        last_cum = first14[-1]["d_cum"]
        gate = dict(days=[first14[0]["date"], first14[-1]["date"]], n_day_ok=n_ok, need=N_OK, d_cum=last_cum,
                    passed=bool(n_ok >= N_OK and last_cum is not None and abs(last_cum) <= TOL_CUM * C.E0))
    rep = dict(cut_over_T=str(t0), now=str(now), n_full_days=len(full), tol_day=TOL_DAY * C.E0, tol_cum=TOL_CUM * C.E0, gate=gate,
               demo_ledger_sha256=hashlib.sha256((PROJ / demo_root / "ledger.jsonl").read_bytes()).hexdigest(),
               shadow_ledger_sha256=hashlib.sha256((PROJ / shadow_root / "ledger.jsonl").read_bytes()).hexdigest(),
               code_sha256=C.sha_f(Path(__file__)))
    return rows, rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", default="data/eco_demo")
    ap.add_argument("--shadow", default="data/eco_shadow")
    ap.add_argument("--now", default=None)
    a = ap.parse_args()
    now = pd.Timestamp(a.now) if a.now else pd.Timestamp.now("UTC").tz_localize(None)
    rows, rep = run(a.demo, a.shadow, now)
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT / "tc_daily.csv", index=False, float_format="%.10g")
    (OUT / "tc_report.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    g = rep["gate"]
    print(f"TC {now}: full days {rep['n_full_days']}/{N_FULL}; last day {rows[-1] if rows else None}; gate {g}")
    bad = [r["date"] for r in rows if r["full_day"] and r["day_ok"] is False]
    if bad:
        print(f"days over the d_day tolerance ({TOL_DAY * C.E0:.0f} eco units): {bad}")


if __name__ == "__main__":
    main()
