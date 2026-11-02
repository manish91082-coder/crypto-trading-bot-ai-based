"""Independent verifier for the green-candle study (protocol §8, V1-V6).

Recomputes everything from the raw csv files with gzip/csv and plain Python loops.
It imports nothing from src/research/green_candle.py; pandas is used only to read the main script's outputs.
Run: python src/audits/verify_green_candle.py
"""
import csv, gzip, hashlib, json, math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "logs" / "green_candle_2026"
TOL = 1e-9
TFM = {"5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440}
PER = {"JAN": ("2026-01-01", "2026-02-01"), "FS26": ("2026-02-01", "2026-10-01")}
for y in range(2020, 2026):
    PER[f"Y{y}"] = (f"{y}-01-01", f"{y + 1}-01-01")

results = []


def check(name, ok, detail=""):
    results.append((name, ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def close(a, b):
    return abs(a - b) <= TOL * max(1.0, abs(a), abs(b))


def read_rows(path):
    op = gzip.open if str(path).endswith(".gz") else open
    rows = {}
    with op(path, "rt", newline="") as f:
        rd = csv.reader(f)
        next(rd)
        for r in rd:
            ts = r[0][:19] if len(r[0]) > 10 else r[0] + " 00:00:00"
            if "2020-01-01" <= ts[:10] <= "2026-09-30":
                rows[ts] = (float(r[1]), float(r[2]), float(r[3]), float(r[4]))
    return rows


def bucket(ts, m):
    day, hh, mm = ts[:10], int(ts[11:13]), int(ts[14:16])
    if m == 1440:
        return day + " 00:00:00"
    k = (hh * 60 + mm) // m * m
    return f"{day} {k // 60:02d}:{k % 60:02d}:00"


def build(rows5, m):
    bars = {}
    for ts in sorted(rows5):
        o, h, l, c = rows5[ts]
        key = bucket(ts, m)
        if key not in bars:
            bars[key] = [o, h, l, c]
        else:
            b = bars[key]
            b[1] = max(b[1], h)
            b[2] = min(b[2], l)
            b[3] = c
    return bars


def col_of(o, c):
    return "G" if c > o else ("R" if c < o else "D")


def simulate(seq, rule):
    """seq: list of (ts, o, c). Returns trades (entry_ts, exit_ts_or_None, entry_px, exit_px, forced)."""
    n = len(seq)
    cols = [col_of(o, c) for _, o, c in seq]
    out = []
    state = "flat"
    entry = None
    k = 0
    while k < n:
        if state == "flat":
            if rule == "R1":
                go = k >= 1 and cols[k] == "G" and cols[k - 1] != "G"
            else:
                go = k >= 2 and cols[k] == "G" and cols[k - 1] == "G" and cols[k - 2] != "G"
            if go and k + 1 < n:
                state, entry = "long", k + 1
                k += 1  # bar k+1 is the first held bar; its own close may trigger the exit
                continue
        else:
            if cols[k] == "R":
                if k + 1 < n:
                    out.append((seq[entry][0], seq[k + 1][0], seq[entry][1], seq[k + 1][1], False))
                else:
                    out.append((seq[entry][0], None, seq[entry][1], seq[n - 1][2], True))
                state = "flat"
        k += 1
    if state == "long":
        out.append((seq[entry][0], None, seq[entry][1], seq[n - 1][2], True))
    return out


def main():
    proto = OUT / "GREEN_CANDLE_PROTOCOL_PREREGISTERED.md"
    lock = (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0]
    check("V1 protocol SHA", sha(proto) == lock, lock[:12])
    man = list(csv.DictReader(open(OUT / "input_manifest.csv")))
    check("V1 input SHAs", all(sha(ROOT / r["file"]) == r["sha256"] for r in man), f"{len(man)} files")
    fees = json.loads((ROOT / "deploy" / "fees.json").read_text())
    cfut, cspot = fees["rules"]["paper_futures_taker_per_side"], fees["rules"]["paper_spot_per_side"]

    rows5 = read_rows(ROOT / "data/universe_hf/5m/BTCUSDT_5m_full.csv.gz")
    bars = {tf: build(rows5, m) for tf, m in TFM.items()}

    # V2 aggregation vs main output (JAN) and vs files (JAN)
    bj = pd.read_parquet(OUT / "bars_jan2026.parquet")
    bad = 0
    cnt = 0
    for r in bj.itertuples(index=False):
        key = str(r.timestamp)[:19]
        if len(key) == 10:
            key += " 00:00:00"
        mine = bars[r.tf].get(key)
        cnt += 1
        if mine is None or not all(close(a, b) for a, b in zip(mine, (r.open, r.high, r.low, r.close))):
            bad += 1
    jan_mine = sum(1 for tf in TFM for k in bars[tf] if k.startswith("2026-01"))
    check("V2 JAN bars equal main output", bad == 0 and cnt == jan_mine, f"{cnt} bars, {bad} mismatches, mine {jan_mine}")
    for tf, rel in (("15m", "data/universe_hf/15m/BTCUSDT_15m_full.csv.gz"), ("1h", "data/universe_all/1h/BTCUSDT_1h_full.csv.gz"),
                    ("1d", "data/universe_all/1d/BTCUSDT_1d.csv")):
        f = read_rows(ROOT / rel)
        keys = [k for k in bars[tf] if k.startswith("2026-01")]
        mism = sum(1 for k in keys if k not in f or not all(close(a, b) for a, b in zip(bars[tf][k], f[k])))
        fk = sum(1 for k in f if k.startswith("2026-01"))
        check(f"V2 JAN {tf} aggregate equals file", mism == 0 and fk == len(keys), f"{len(keys)} bars, {mism} mismatches")

    # V3 Part A counts
    pa = json.loads((OUT / "partA_jan2026.json").read_text())
    for tf in TFM:
        seq = [(k, v[0], v[3]) for k, v in sorted(bars[tf].items()) if k.startswith("2026-01")]
        cols = [col_of(o, c) for _, o, c in seq]
        ok = cols.count("G") == pa[tf]["G"] and cols.count("R") == pa[tf]["R"] and cols.count("D") == pa[tf]["D"]
        tc = {}
        for a, b in zip(cols[:-1], cols[1:]):
            tc[a + b] = tc.get(a + b, 0) + 1
        ok &= all(tc.get(k, 0) == v for k, v in pa[tf]["transition_counts"].items())
        runs = []
        i = 0
        while i < len(cols):
            if cols[i] == "G":
                j = i
                while j + 1 < len(cols) and cols[j + 1] == "G":
                    j += 1
                runs.append((i, j))
                i = j + 1
            else:
                i += 1
        lens = {"1": 0, "2": 0, "3": 0, "4": 0, "5+": 0}
        sg = 0.0
        for i, j in runs:
            L = j - i + 1
            lens[str(L) if L < 5 else "5+"] += 1
            sg += seq[j][2] / seq[i][1] - 1
        orc = pa[tf]["oracle"]
        ok &= lens == pa[tf]["run_lengths_observed"] and len(runs) == orc["n_runs"]
        ok &= close(sg, orc["sum_gross"]) and close(sg - 2 * cfut * len(runs), orc["sum_net_fut"]) \
            and close(sg - 2 * cspot * len(runs), orc["sum_net_spot"])
        check(f"V3 JAN {tf} colours/transitions/runs/oracle", ok, f"G {cols.count('G')} runs {len(runs)} sum_gross {sg:.6f}")

    # V4 + V5 trades
    T = pd.read_parquet(OUT / "trades_all.parquet")
    for per, (s, e) in PER.items():
        for tf in TFM:
            seq = [(k, v[0], v[3]) for k, v in sorted(bars[tf].items()) if s <= k[:10] < e]
            for rule in ("R1", "R2"):
                mine = simulate(seq, rule)
                tm = T[(T.period == per) & (T.tf == tf) & (T.rule == rule)].reset_index(drop=True)
                sum_mine = sum(x / en - 1 - 2 * cfut for _, _, en, x, _ in mine)
                ok = len(mine) == len(tm) and close(sum_mine, float(tm["net_fut"].sum()))
                if per == "JAN":
                    for (et, xt, ep, xp, fo), r in zip(mine, tm.itertuples(index=False)):
                        ok &= str(r.entry_time)[:19] == et
                        ok &= (xt is None and bool(r.forced)) or (xt is not None and str(r.exit_time)[:19] == xt)
                        ok &= close(ep, r.entry_px) and close(xp, r.exit_px) and close(xp / ep - 1 - 2 * cfut, r.net_fut)
                    check(f"V4 JAN {tf} {rule} every trade", ok, f"{len(mine)} trades")
                else:
                    check(f"V5 {per} {tf} {rule} count+sum", ok, f"{len(mine)} trades, sum net fut {sum_mine:.6f}")

    # V6 output SHAs
    good = True
    for line in (OUT / "OUTPUT_SHA256.txt").read_text().splitlines():
        h, f = line.split()
        good &= sha(OUT / f) == h
    check("V6 output SHAs", good)
    nf = sum(1 for _, ok in results if not ok)
    print(f"\nTOTAL {len(results)} checks, {len(results) - nf} PASS, {nf} FAIL -> {'ALL PASS' if nf == 0 else 'FAILURES'}")


if __name__ == "__main__":
    main()
