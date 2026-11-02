"""Independent verifier of ECO amendment 3 §1 (logs/eco/ECO_AMENDMENT_3_PREREGISTERED.md §4).
Re-implements the drawdown alarm with pandas (cummax) from the DDX CSV and the DDX start date (2026-10-26, a constant of
logs/drawdown_ddx/DDX_PROTOCOL_PREREGISTERED.md), and compares it with eco_alerts.dd_status (the only thing imported from it).
  V1 config: deploy/eco_dd_alarm.json bands = the CSV rows, source SHA = the CSV's SHA, start = 2026-10-26T00:00:00
  V2 synthetic: 300 random ledgers (random walks, junk records, random 'now') -> dd within 1e-12, same a, H*, level, base T
  V3 real: each ledger.jsonl given on the command line (read only) -> the same comparison, and the level is printed
Usage: python src/audits/verify_eco_dd_alarm.py [--cfg deploy/eco_dd_alarm.json] [--now "2026-10-28 09:00"] [ledger.jsonl ...]
Exit 0 = all PASS."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

R_ = Path(__file__).resolve().parents[2]
CSV = R_ / "logs" / "drawdown_ddx" / "alarm_thresholds.csv"
START = pd.Timestamp("2026-10-26 00:00:00")                    # DDX protocol Part B: first full demo day
res = []


def ok(t, c, m):
    res.append(bool(c))
    print(f"[{'PASS' if c else 'FAIL'}] {t}: {m}")


def mine(L, now, bands):
    """the §1 rule, written independently: -> (dd, a, H, level, base_T) or None."""
    df = pd.DataFrame([dict(T=r.get("T"), mode=r.get("mode"), e=r.get("eco_equity")) for r in L])
    if df.empty:
        return None
    df = df[(df["mode"] != "reset") & df["e"].map(lambda v: type(v) in (int, float) and np.isfinite(v))].copy()
    df["T"] = pd.to_datetime(df["T"])
    df["e"] = df["e"].astype(float)
    pre, post = df[df["T"] < START], df[df["T"] >= START]
    if post.empty:
        return None
    s = pd.concat([pre.tail(1), post])
    dd = float((1.0 - s["e"] / s["e"].cummax()).max())
    a = int(np.floor((now - START).total_seconds() / 86400.0))
    b = bands[bands["H"] >= a]
    b = (b.iloc[0] if len(b) else bands.iloc[-1])
    level = None if a < 0 else ("red" if dd > b["red_dd"] else "yellow" if dd > b["yellow_dd"] else "normal")
    return dd, a, int(b["H"]), level, str(s["T"].iloc[0])


def compare(tag, L, now, cfg, bands, show=False):
    m, t = mine(L, now, bands), AL.dd_status(L, now, cfg)
    if m is None or t is None:
        return (m is None and t is None), f"{tag}: both None" if m is None and t is None else f"{tag}: mine {m} theirs {t}"
    same = abs(m[0] - t["dd"]) <= 1e-12 and (m[1], m[2], m[3], m[4]) == (t["a"], t["H"], t["level"], t["base_T"])
    msg = f"{tag}: dd {m[0]:.6%} a {m[1]} H* {m[2]} level {m[3]} base {m[4]} | code: dd {t['dd']:.6%} a {t['a']} H* {t['H']} level {t['level']}"
    return same, msg


def synth(rng):
    t0 = START + pd.Timedelta(hours=int(rng.integers(-200, 100)))
    n = int(rng.integers(1, 2000))
    e = 10_000.0 * np.exp(np.cumsum(rng.normal(0, rng.choice([0.002, 0.01, 0.03]), n)))
    L = [dict(T=str(t0 + pd.Timedelta(hours=i)), mode="demo", ok=True, eco_equity=float(x)) for i, x in enumerate(e)]
    for _ in range(int(rng.integers(0, 6))):                    # junk: reset, None, missing, bool, NaN, a string
        j = dict(T=str(t0 + pd.Timedelta(hours=int(rng.integers(0, n)))), mode="demo", ok=True)
        k = int(rng.integers(0, 6))
        j.update([dict(mode="reset", eco_equity=1.0), dict(eco_equity=None), dict(ok=False), dict(eco_equity=True),
                  dict(eco_equity=float("nan")), dict(eco_equity="9000")][k])
        L.insert(int(rng.integers(0, len(L) + 1)), j)
    L.sort(key=lambda r: r["T"])                                 # a ledger is in time order
    now = t0 + pd.Timedelta(hours=n - 1, minutes=int(rng.integers(0, 600)))
    return L, now


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cfg", default=str(R_ / "deploy" / "eco_dd_alarm.json"))
    ap.add_argument("--now", default=None)
    ap.add_argument("ledgers", nargs="*")
    a = ap.parse_args()
    cfg = json.loads(Path(a.cfg).read_text(encoding="utf-8"))
    bands = pd.read_csv(CSV, float_precision="round_trip").sort_values("H").reset_index(drop=True)
    rows = [dict(H=int(r.H), yellow_dd=float(r.yellow_dd), red_dd=float(r.red_dd)) for r in bands.itertuples()]
    csv_sha = hashlib.sha256(CSV.read_bytes()).hexdigest()
    ok("V1", cfg["bands"] == rows and cfg["source_sha256"] == csv_sha and pd.Timestamp(cfg["start_utc"]) == START,
       f"config bands = CSV {cfg['bands'] == rows}; source sha = CSV {csv_sha[:12]} {cfg['source_sha256'] == csv_sha}; start {cfg['start_utc']}")
    rng, bad, lv = np.random.default_rng(20261028), [], {}
    for i in range(300):
        L, now = synth(rng)
        same, msg = compare(f"synthetic {i}", L, now, cfg, bands)
        if not same:
            bad.append(msg)
        m = mine(L, now, bands)
        lv[m[3] if m else "none"] = lv.get(m[3] if m else "none", 0) + 1
    ok("V2", not bad, f"300 random ledgers: mismatches {len(bad)} {bad[:2]}; levels seen {lv}")
    now = pd.Timestamp(a.now) if a.now else pd.Timestamp.now("UTC").tz_localize(None)
    for f in a.ledgers:
        L = [json.loads(l) for l in Path(f).read_text(encoding="utf-8").splitlines() if l.strip()]
        same, msg = compare(f, L, now, cfg, bands)
        ok("V3", same, f"{len(L)} records, now {now}: {msg}")
    print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
    sys.exit(1 if False in res else 0)


sys.path.insert(0, str(R_ / "src" / "eco"))
import eco_alerts as AL                                        # noqa: E402 - only dd_status is used

if __name__ == "__main__":
    main()
