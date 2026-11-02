"""Independent verifier of T2-CARRY (2026-11-02). Standard library only: it shares no code with forward_carry.py and makes its own API calls, then recomputes every
hourly row from raw bars and funding with plain loops. Mutation checks prove that the comparison can fail.
Usage: python src/audits/verify_forward_carry.py   -> TOTAL n checks, FAIL k."""
import csv
import datetime as dt
import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

R_ = Path(__file__).resolve().parents[2]
D = R_ / "logs/carry_t2_2026_11_02"
H = 3600000
T0 = int(dt.datetime(2026, 11, 2, 8, tzinfo=dt.timezone.utc).timestamp() * 1000)
T1 = int(dt.datetime(2027, 1, 31, 8, tzinfo=dt.timezone.utc).timestamp() * 1000)
FAIL = []
n_ = 0


def ok(name, good, msg):
    global n_
    n_ += 1
    print(f"[{name} {'PASS' if good else 'FAIL'}] {msg}", flush=True)
    if not good:
        FAIL.append(name)


def fetch(url, **p):
    q = url + "?" + urllib.parse.urlencode(p)
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(q, headers={"User-Agent": "verify"}), timeout=25) as r:
                return json.load(r)
        except Exception:                                                     # noqa: BLE001
            if i == 3:
                raise
            time.sleep(1 + i)


def spot(sym, a, b):
    m, t = {}, a
    while t < b:
        rows = fetch("https://data-api.binance.vision/api/v3/klines", symbol=sym, interval="1h", startTime=t, limit=500)
        rows = [x for x in rows if int(x[0]) < b]
        if not rows:
            break
        for x in rows:
            m[int(x[0])] = [float(x[1]), float(x[2]), float(x[4])]
        t = int(rows[-1][0]) + H
    return m


def perp(sym, a, b):
    m, t = {}, a
    while t < b:                                                              # forward windows, the live code pages backward
        e = min(t + 500 * H, b) - 1
        rows = fetch("https://api.bybit.com/v5/market/kline", category="linear", symbol=sym, interval="60", start=t, end=e, limit=1000)["result"]["list"]
        for x in rows:
            m[int(x[0])] = [float(x[1]), float(x[2]), float(x[4])]
        t = e + 1
    return m


def rates(sym, a, b):
    m, t = {}, a
    while t < b:
        e = min(t + 40 * 24 * H, b)                                           # 120 events a page
        rows = fetch("https://api.bybit.com/v5/market/funding/history", category="linear", symbol=sym, startTime=t + 1, endTime=e, limit=200)["result"]["list"]
        for x in rows:
            m[int(x["fundingRateTimestamp"])] = float(x["fundingRate"])
        t = e
    return {k: v for k, v in m.items() if a < k <= b}


def replay(sp, pp, fr, fs, ff, closes):
    """one coin: pnl, funding and margin at each close in closes"""
    n = 2500.0
    qs, qp = n / sp[T0][0], n / pp[T0][0]
    out = {}
    paid = 0.0
    done = set()
    for c in closes:
        for tau in sorted(fr):
            if tau <= c and tau not in done:
                paid += fr[tau] * qp * pp[tau // H * H][0]
                done.add(tau)
        b = c - H
        s, p = sp[b][2], pp[b][2]
        pnl = qs * (s - sp[T0][0]) + qp * (pp[T0][0] - p) + paid - n * (fs + ff) - (fs * qs * s + ff * qp * p)
        hi = pp[b][1]
        out[c] = (pnl, paid, (n - qp * (hi - pp[T0][0]) + paid) / (qp * hi), len(done))
    return out


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ---- files that exist before the first bar
lock = (D / "T2_PROTOCOL_SHA256.txt").read_text(encoding="utf-8").split()
ok("V1", lock[0] == sha(D / "T2_PROTOCOL_PREREGISTERED.md"), f"protocol SHA {lock[0][:12]} unchanged")
pl = json.loads((D / "PRELOCK_HISTORY.json").read_text(encoding="utf-8"))
ok("V2", lock[lock.index("prelock_json_sha256") + 1] == sha(D / "PRELOCK_HISTORY.json"), "prelock JSON equals the locked SHA")
txt = (D / "T2_PROTOCOL_PREREGISTERED.md").read_text(encoding="utf-8")
ok("V3", f"+{pl['hurdle_pct_of_capital']}%" in txt and pl["hurdle_pct_of_capital"] == round(pl["roll90"]["2025"]["p50"] / 2, 3), f"hurdle {pl['hurdle_pct_of_capital']} is half the 2025 median and is the protocol's number")
study = json.loads((R_ / "logs/research_spot_dca/SPOT_DCA_RESULTS.json").read_text(encoding="utf-8"))
same = True
for c in ("BTCUSDT", "ETHUSDT"):
    seen = {}
    with open(R_ / f"data/futures_um/{c}_funding.csv", newline="") as f:
        for row in csv.DictReader(f):
            if "2020-07-01" <= row["time"] < "2026-10-01":
                seen[row["time"][:4]] = seen.get(row["time"][:4], 0.0) + float(row["funding_rate"])
    same = same and all(abs(seen[y] * 100 - v["net_pct"]) < 1e-6 for y, v in study[f"B1_{c}"]["per_year"].items())
ok("V4", same, "funding per year recomputed by plain loop equals the Spot-DCA study B1")
fees_raw = (R_ / "deploy/fees.json").read_bytes()
rules = json.loads(fees_raw)["rules"]

if not (D / "carry_freeze.json").exists():
    print("no forward run yet: live checks skipped")
    print("TOTAL", n_, "checks, FAIL", len(FAIL))
    sys.exit(1 if FAIL else 0)

# ---- forward records
fz = json.loads((D / "carry_freeze.json").read_text(encoding="utf-8"))
ok("V5", fz["fs"] == rules["paper_spot_per_side"] and fz["ff"] == rules["paper_futures_taker_per_side"] and fz["fees_sha256"] == hashlib.sha256(fees_raw).hexdigest(), f"frozen fees {fz['fs']} / {fz['ff']} equal deploy/fees.json")
ok("V6", fz["frozen_utc"] >= "2026-11-02T09:00" and lock[lock.index("locked_utc") + 1] < "2026-11-02T08:00:00Z", f"protocol locked {lock[lock.index('locked_utc') + 1]} before FORWARD_START; frozen {fz['frozen_utc']}")
lines = (D / "carry_forward.jsonl").read_bytes().splitlines()
prev, chain = "GENESIS", True
for ln in lines:
    chain = chain and json.loads(ln)["prev"] == prev
    prev = hashlib.sha256(ln).hexdigest()
ok("V7", chain and len(lines) > 0, f"hash chain of {len(lines)} records")
last = json.loads(lines[-1])
body = (D / "carry_series.csv").read_bytes()
rows = list(csv.DictReader(body.decode().splitlines()))
ok("V8", hashlib.sha256(body).hexdigest() == last["series_sha256"], "series CSV equals the SHA in the last chain record")
closes = [int(r["t"]) for r in rows]
ok("V9", closes == [T0 + H * (i + 1) for i in range(len(closes))] and closes[-1] <= T1, f"{len(closes)} consecutive hours from FORWARD_START")
stop = closes[-1]
rep, raw = {}, {}
for c in ("BTCUSDT", "ETHUSDT"):
    raw[c] = (spot(c, T0, stop), perp(c, T0, stop + H), rates(c, T0, stop))
    ev = sorted(raw[c][2])
    ok(f"V10 {c[:3]}", all(b - a == 8 * H for a, b in zip(ev, ev[1:])) and len(ev) == (stop - T0) // (8 * H), f"{len(ev)} funding events, none missing")
    rep[c] = replay(*raw[c], fz["fs"], fz["ff"], closes)


def compare(rp):
    bad = peak = 0
    peak = 10000.0
    for r in rows:
        t = int(r["t"])
        eq = 10000.0 + rp["BTCUSDT"][t][0] + rp["ETHUSDT"][t][0]
        peak = max(peak, eq)
        m = min(rp["BTCUSDT"][t][2], rp["ETHUSDT"][t][2])
        if abs(eq - float(r["equity"])) > 1e-6 or abs(eq / peak - 1 - float(r["dd"])) > 1e-9 or abs(m - float(r["margin"])) > 1e-9:
            bad += 1
        for c in ("BTCUSDT", "ETHUSDT"):
            if abs(rp[c][t][1] - float(r[f"{c}_funding"])) > 1e-6 or rp[c][t][3] != int(r[f"{c}_n_funding"]):
                bad += 1
    return bad


bad = compare(rep)
ok("V11", bad == 0, f"{len(rows)} hours recomputed independently: {bad} mismatches")
s = last["summary"]
if s["last_close"] == stop:
    t = stop
    eq = 10000.0 + rep["BTCUSDT"][t][0] + rep["ETHUSDT"][t][0]
    ok("V12", abs(eq - s["equity"]) < 1e-6 and last["verdict"] in ("INTERIM", "PASS", "FAIL", "INCONCLUSIVE", "FAIL (margin)"), f"chain summary equity {s['equity']:.4f}, verdict {last['verdict']}")
    ok("V13", stop >= T1 or last["verdict"] == "INTERIM" or last["verdict"] == "FAIL (margin)", "no verdict before FORWARD_END")
c = "BTCUSDT"
sp, pp, fr = raw[c]
m1 = dict(fr)
if m1:
    k = sorted(m1)[0]
    m1[k] += 0.0001
    x = dict(rep)
    x[c] = replay(sp, pp, m1, fz["fs"], fz["ff"], closes)
    ok("M1", compare(x) > 0, "mutation: one funding rate changed, caught")
x = dict(rep)
x[c] = replay(sp, pp, fr, fz["fs"] + 0.0001, fz["ff"], closes)
ok("M2", compare(x) > 0, "mutation: spot fee changed, caught")
b = dict(sp)
b[T0] = [sp[T0][0] * 1.001, sp[T0][1], sp[T0][2]]
x = dict(rep)
x[c] = replay(b, pp, fr, fz["fs"], fz["ff"], closes)
ok("M3", compare(x) > 0, "mutation: entry price changed, caught")
print("TOTAL", n_, "checks, FAIL", len(FAIL))
sys.exit(1 if FAIL else 0)
