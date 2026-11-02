"""Independent verifier for GEMV (logs/research_gemini_review/GEMV_PROTOCOL_PREREGISTERED.md). Own code; does not import gemv_check.
1 200 random (row, model) values recomputed with an own implementation of the notebook path rules (1e-12)
2 summary means / medians / label shares / fill rates recomputed from the row file (1e-12)
3 SHAs / protocol lock"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

R_ = Path(__file__).resolve().parents[2]
O_ = R_ / "logs" / "research_gemini_review"
res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}", flush=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def own_path(entry, side, r1, slp, H, L, C):
    """own implementation of the notebook rules (protocol text): stop first; BE at +0.70R -> +0.15R; TP1 35% @1.2R (stop +0.25R);
    TP2 35% @2.3R (stop +1.25R); TP3 rest @3.6R; trail extreme-0.95R once fav >= 1.35R; time exit at last close minus maker friction."""
    fm, fs = 0.00051 / (slp + 1e-8), 0.00085 / (slp + 1e-8)
    w, acc, stage, be = 1.0, 0.0, 0, False
    stop = entry - side * r1
    best = entry
    lv = [entry + side * m * r1 for m in (1.2, 2.3, 3.6)]
    for hk, lk in zip(H, L):
        fav = ((hk - entry) if side == 1 else (entry - lk)) / (r1 + 1e-12)
        if (lk <= stop) if side == 1 else (hk >= stop):
            return acc + w * (side * (stop - entry) / (r1 + 1e-12) - (fm if be else fs))
        best = max(best, hk) if side == 1 else min(best, lk)
        if not be and fav >= 0.70:
            be, stop = True, entry + side * 0.15 * r1
        hit = lambda p: (hk >= p) if side == 1 else (lk <= p)
        if stage == 0 and hit(lv[0]):
            acc += 0.35 * (1.2 - fm); w -= 0.35; stage = 1; be = True; stop = entry + side * 0.25 * r1
        if stage == 1 and hit(lv[1]):
            acc += 0.35 * (2.3 - fm); w -= 0.35; stage = 2; stop = entry + side * 1.25 * r1
        if stage == 2 and hit(lv[2]):
            return acc + w * (3.6 - fm)
        if be and fav >= 1.35:
            t = best - side * 0.95 * r1
            stop = max(stop, t) if side == 1 else min(stop, t)
    return acc + w * (side * (C[-1] - entry) / (r1 + 1e-12) - fm) if w > 0 else acc


D = pd.read_parquet(O_ / "gemv_rows.parquet")
cache, bad, done = {}, [], 0
rng = np.random.default_rng(99)
for idx in rng.choice(len(D), 200, replace=False):
    r = D.iloc[idx]
    if r.coin not in cache:
        x = pd.read_csv(R_ / "data" / "universe_hf" / "5m" / f"{r.coin}_5m_full.csv.gz", usecols=["timestamp", "open", "high", "low", "close"])
        x["timestamp"] = pd.to_datetime(x.timestamp)
        g = x.groupby(x.timestamp.dt.floor("h"))
        b = pd.DataFrame(dict(open=g.open.first(), high=g.high.max(), low=g.low.min(), close=g.close.last()))
        cache[r.coin] = b[(b.index >= "2021-01-01") & (b.index < "2026-10-01")]
    b = cache[r.coin]
    o, h, l, c = b.open.values, b.high.values, b.low.values, b.close.values
    i = b.index.get_loc(r.t); sd = int(r.side); sp = r.sl_pct; R1 = c[i] * sp
    if sd == 1:
        pA = max(l[i + 1], c[i] - 0.18 * R1) if l[i + 1] <= c[i] else c[i]
    else:
        pA = min(h[i + 1], c[i] + 0.18 * R1) if h[i + 1] >= c[i] else c[i]
    a = own_path(pA, sd, R1, sp, h[i + 1:i + 21], l[i + 1:i + 21], c[i + 1:i + 21])
    lim = c[i] - sd * 0.18 * R1
    fil = (l[i + 1] <= lim) if sd == 1 else (h[i + 1] >= lim)
    if fil:
        same = (l[i + 1] <= lim - R1) if sd == 1 else (h[i + 1] >= lim + R1)
        bb = (-1.0 - 0.00085 / (sp + 1e-8)) if same else own_path(lim, sd, R1, sp, h[i + 2:i + 21], l[i + 2:i + 21], c[i + 2:i + 21])
    else:
        bb = np.nan
    cc = own_path(o[i + 1], sd, R1, sp, h[i + 1:i + 21], l[i + 1:i + 21], c[i + 1:i + 21]) - 0.00027 / sp
    good = abs(a - r.rA) < 1e-12 and abs(cc - r.rC) < 1e-12 and (fil == bool(r.filledB)) and ((np.isnan(bb) and np.isnan(r.rB)) or abs(bb - r.rB) < 1e-12)
    done += 1
    if not good:
        bad.append(f"{r.coin} {r.t} {sd}: A {a:.6f}/{r.rA:.6f} B {bb}/{r.rB} C {cc:.6f}/{r.rC:.6f}")
ok("1", not bad, f"{done} random rows recomputed with own path code: mismatches {len(bad)} {bad[:3]}")

S = pd.read_csv(O_ / "GEMV_summary.csv")
mx = 0.0
for sd, g in D.groupby("side"):
    lab = "long" if sd == 1 else "short"
    for m in "ABC":
        v = g[f"r{m}"].dropna(); row = S[(S.side == lab) & (S.model == m)].iloc[0]
        mx = max(mx, abs(v.mean() - row.mean_R), abs(v.median() - row.median_R), abs((v > 0.10).mean() - row.label1_share), abs(len(v) - row.n))
    f = g[g.filledB]; row = S[(S.side == lab) & S.model.str.startswith("A-B")].iloc[0]
    mx = max(mx, abs((f.rA - f.rB).mean() - row.mean_R))
ok("2", mx < 1e-12, f"summary recomputed from rows: max |diff| {mx:.1e}")
cl = json.loads((O_ / "claims_gemv.json").read_text())
ok("3", cl["protocol_sha"] == sha(O_ / "GEMV_PROTOCOL_PREREGISTERED.md") == (O_ / "GEMV_PROTOCOL_SHA256.txt").read_text().split()[0]
   and cl["rows_sha"] == sha(O_ / "gemv_rows.parquet") and cl["summary_sha"] == sha(O_ / "GEMV_summary.csv")
   and cl["code_sha"] == sha(R_ / "src" / "research" / "gemv_check.py"), "claims / SHAs / protocol lock consistent")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
