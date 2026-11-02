"""Independent verifier of the spot sleeve study (logs/research_spot_sleeve/SPOT_SLEEVE_PROTOCOL_PREREGISTERED.md).
No code shared with src/research/spot_sleeve_study.py: csv rows, calendar loops, own SMA / signals / fills.
V1 manifest SHAs  V2 S1/S3/S4/S6 final equity and trade counts, every period  V3 S5 holdings on 20 random Mondays
V4 the 20% S1 + ECO mix"""
import csv
import hashlib
import json
import random
import statistics
from datetime import date, timedelta
from pathlib import Path

R_ = Path(__file__).resolve().parents[2]
OUT = R_ / "logs" / "research_spot_sleeve"
res = []
PER = dict(P0=("2018-03-06", "2019-12-31"), dev=("2020-07-01", "2023-12-31"), holdout=("2024-01-01", "2026-09-30"), full=("2020-07-01", "2026-09-30"))
END = date(2026, 9, 30)


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}", flush=True)


def rows(path, lo=None, hi=None):
    out = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = date.fromisoformat(r["timestamp"][:10])
            if (lo is None or d >= lo) and (hi is None or d <= hi) and d not in out:
                out[d] = (float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]), float(r["quote_volume"]))
    return out


rep = json.loads((OUT / "SPOT_SLEEVE_RESULTS.json").read_text(encoding="utf-8"))
man = list(csv.DictReader(open(OUT / "input_manifest.csv", encoding="utf-8")))
bad = [m["path"] for m in man if hashlib.sha256((R_ / m["path"]).read_bytes()).hexdigest() != m["sha256"]]
ok("V1", not bad and hashlib.sha256((OUT / "input_manifest.csv").read_bytes()).hexdigest() == rep["manifest_sha256"], f"{len(man)} inputs, SHA mismatches {len(bad)}")

btc = rows(R_ / "data" / "universe_pre2020" / "1d" / "BTCUSDT_1d.csv", hi=date(2019, 12, 31))
btc.update(rows(R_ / "data" / "universe_all" / "1d" / "BTCUSDT_1d.csv", lo=date(2020, 1, 1), hi=END))
days = []
d = min(btc)
while d <= END:
    days.append(d); d += timedelta(days=1)
close = [btc[x][3] if x in btc else None for x in days]
high = [btc[x][1] if x in btc else None for x in days]


def sma(i, n):
    if i + 1 < n:
        return None
    w = close[i - n + 1:i + 1]
    return None if any(v is None for v in w) else sum(w) / n


S = {"S1": [], "S3": [], "S4": [], "S6": []}
cur4, cur6 = False, False
for i, d in enumerate(days):
    c, s200, s50 = close[i], sma(i, 200), sma(i, 50)
    S["S1"].append(c is not None and s200 is not None and c > s200)
    S["S3"].append(s50 is not None and s200 is not None and s50 > s200)
    if d.weekday() == 0:
        cur4 = c is not None and i >= 28 and close[i - 28] is not None and c / close[i - 28] > 1
    S["S4"].append(cur4)
    hs = [h for h in high[max(0, i - 364):i + 1] if h is not None]
    hi365 = max(hs) if len(hs) >= 200 else None
    p50 = sma(i - 1, 50) if i >= 1 else None
    crossed = (c is not None and s50 is not None and p50 is not None and close[i - 1] is not None and close[i - 1] <= p50 and c > s50)
    if not cur6 and hi365 is not None and c is not None and c <= 0.70 * hi365 and crossed:
        cur6 = True
    elif cur6 and c is not None and s50 is not None and c < s50:
        cur6 = False
    S["S6"].append(cur6)
pos = {d: i for i, d in enumerate(days)}
badv = []
for k, sig in S.items():
    for per, (a, b) in PER.items():
        a_, b_ = date.fromisoformat(a), date.fromisoformat(b)
        cash, units, n_tr, lastc, entry = 10_000.0, 0.0, 0, None, None
        for i in range(pos[a_], pos[b_] + 1):
            d = days[i]
            want = sig[i - 1]
            if d in btc:
                o = btc[d][0]
                if want and units == 0:
                    units = cash * (1 - 0.001) / o; cash = 0.0
                elif not want and units > 0:
                    cash = units * o * (1 - 0.001); units = 0.0; n_tr += 1
                lastc = btc[d][3]
            elif lastc is None:
                j = i
                while days[j] not in btc:
                    j -= 1
                lastc = btc[days[j]][3]
        n_tr += 1 if units > 0 else 0
        final = cash + units * lastc
        R = rep[f"base_{per}"][k]
        if abs(final / R["final"] - 1) > 1e-6 or n_tr != R["trades"]:
            badv.append((k, per, round(final, 4), round(R["final"], 4), n_tr, R["trades"]))
ok("V2", not badv, f"S1/S3/S4/S6 x 4 periods recomputed by calendar loops (final equity within 1e-6, trade counts): mismatches {badv[:4]}")

# V3: S5 holdings on 20 random Mondays
STABLE = {"USDC", "BUSD", "TUSD", "FDUSD", "USDP", "DAI", "PAX", "USDS", "USDSB", "SUSD", "UST", "USTC", "EUR", "GBP", "AUD", "BRL",
          "TRY", "AEUR", "EURI", "XUSD", "USD1", "BFUSD", "RLUSD"}
H = {}
for per in ("full",):
    H.update(json.loads((OUT / f"S5_holdings_{per}.json").read_text()))
U = {}
for f in sorted((R_ / "data" / "universe_all" / "1d").glob("*_1d.csv")):
    s = f.name[:-7]
    if s.endswith("USDT") and not s.endswith(("UPUSDT", "DOWNUSDT", "BULLUSDT", "BEARUSDT")) and s[:-4] not in STABLE:
        U[s] = rows(f, lo=date(2020, 1, 1), hi=END)
random.seed(7)
mondays = random.sample(sorted(H), 20)
badh = []
for m in mondays:
    t = date.fromisoformat(m)
    i = pos[t]
    regime = close[i] is not None and sma(i, 200) is not None and close[i] > sma(i, 200)
    if not regime:
        exp = []
    else:
        cand = []
        for s, R in U.items():
            if t not in R or (t - timedelta(days=28)) not in R:
                continue
            nb = sum(1 for x in R if x <= t)
            qv = [R[t - timedelta(days=j)][4] for j in range(30) if (t - timedelta(days=j)) in R]
            if nb < 200 or len(qv) < 20:
                continue
            cand.append((statistics.median(qv), s, R[t][3] / R[t - timedelta(days=28)][3] - 1))
        top20 = sorted(cand, key=lambda z: -z[0])[:20]
        exp = [z[1] for z in sorted(top20, key=lambda z: -z[2])[:5]]
    if sorted(exp) != sorted(H[m]):
        badh.append((m, exp, H[m]))
ok("V3", not badh, f"S5 holdings on 20 random Mondays recomputed by loops (regime, liquidity top 20, 28-day top 5): mismatches {badh[:2]}")

# V4: 20% S1 mix with ECO (reads the ECO parquet; loop arithmetic)
import pandas as pd                                                  # parquet reading only
eco = pd.read_parquet(R_ / "data" / "derived" / "eco" / "e2_daily_series.parquet")
er = {}
for c in eco.columns:
    if c.endswith("|ECO-W2") and not c.startswith("P1|") and not c.startswith("P2|"):
        v = eco[c].dropna()
        prev = None
        for t, x in v.items():
            if prev is not None and t.date() not in er:
                er[t.date()] = x / prev - 1
            prev = x
s1 = {}
prev = None
with open(OUT / "equity_S1_full.csv", encoding="utf-8") as f:
    for r in csv.reader(f):
        if r[0][:4].isdigit():
            d, v = date.fromisoformat(r[0][:10]), float(r[1])
            if prev is not None:
                s1[d] = v / prev - 1
            prev = v
common = sorted(set(er) & set(s1))
val, hold, pm = 10_000.0, None, None
for d in common:
    if hold is None or d.month != pm:
        hold = [val * 0.8, val * 0.2]; pm = d.month
    hold = [hold[0] * (1 + er[d]), hold[1] * (1 + s1[d])]; val = sum(hold)
rv = rep["mix"]["S1"]["share_20"]["final"]
ok("V4", abs(val / rv - 1) < 1e-9, f"ECO 80% + S1 20% monthly-rebalanced mix by a loop: {val:.4f} vs report {rv:.4f}")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
raise SystemExit(1 if False in res else 0)
