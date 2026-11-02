"""Independent verifier of the spot DCA study (logs/research_spot_dca/SPOT_DCA_PROTOCOL_PREREGISTERED.md).
No code shared with src/research/spot_dca_study.py; raw CSV rows and plain loops only.
V1 manifest SHAs  V2 200 random grade decisions  V3 P full ledger replayed by a cash loop (fill prices, final and 20 daily
equities)  V4 every TP / delisting exit obeys the fill rule  V5 B1 funding per year"""
import csv
import hashlib
import json
import random
import statistics
from datetime import date, datetime, timedelta
from pathlib import Path

R_ = Path(__file__).resolve().parents[2]
OUT = R_ / "logs" / "research_spot_dca"
FEE = 0.00085
res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}", flush=True)


def rows(sym):
    out = {}
    with open(R_ / "data" / "universe_all" / "1d" / f"{sym}_1d.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = date.fromisoformat(r["timestamp"][:10])
            if date(2020, 1, 1) <= d <= date(2026, 9, 30) and d not in out:
                out[d] = (float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]), float(r["quote_volume"]))
    return out


rep = json.loads((OUT / "SPOT_DCA_RESULTS.json").read_text())
man = list(csv.DictReader(open(OUT / "input_manifest.csv", encoding="utf-8")))
bad = [m["path"] for m in man if hashlib.sha256((R_ / m["path"]).read_bytes()).hexdigest() != m["sha256"]]
ok("V1", not bad and hashlib.sha256((OUT / "input_manifest.csv").read_bytes()).hexdigest() == rep["manifest_sha256"],
   f"{len(man)} input files: SHA mismatches {len(bad)}; manifest SHA == report")

# V2 (missed-entry direction): 200 random (coin, day) graded A/B by loops, eligible, not held; when the study's cash at that
# close was >= 50% of equity (cash cannot explain a skip), the study must have bought that coin at the next open.
syms = [Path(m["path"]).name[:-7] for m in man]
random.seed(2026)
cache = {}
T0 = json.loads((OUT / "P_full_trades.json").read_text())
OP0 = list(csv.DictReader(open(OUT / "P_full_open_at_end.csv")))
EQR = {r["date"][:10]: (float(r["equity"]), float(r["cash"])) for r in csv.DictReader(open(OUT / "P_full_equity.csv"))}
held_iv = {}
for t in T0:
    held_iv.setdefault(t["sym"], []).append((date.fromisoformat(t["buys"][0][0]), date.fromisoformat(t["exit"][:10])))
for p in OP0:
    held_iv.setdefault(p["sym"], []).append((date.fromisoformat(p["entry"][:10]), date(2026, 9, 30)))
entries = {(t["sym"], date.fromisoformat(t["buys"][0][0])) for t in T0} | {(p["sym"], date.fromisoformat(p["entry"][:10])) for p in OP0}


def grade_at(R, ds, k):
    closes = [R[x][3] for x in ds[:k + 1]]
    a_u = a_d = None
    for i in range(1, len(closes)):
        ch = closes[i] - closes[i - 1]; u, dn = max(ch, 0.0), max(-ch, 0.0)
        a_u = u if a_u is None else a_u + (u - a_u) / 14; a_d = dn if a_d is None else a_d + (dn - a_d) / 14
    rsi = 100.0 if a_d == 0 else 100 - 100 / (1 + a_u / a_d)
    d = ds[k]
    mh = max(R[x][1] for x in ds[max(0, k - 89):k + 1])
    dd = R[d][3] / mh - 1
    rev = R[d][3] > R[ds[k - 1]][1]
    qv = [R[d - timedelta(days=i)][4] for i in range(30) if d - timedelta(days=i) in R]
    elig = k + 1 >= 200 and len(qv) >= 20 and statistics.median(qv) >= 10e6
    gA = dd <= -0.30 and rsi <= 35 and rev
    return elig, gA, (dd <= -0.15 and rsi <= 45 and rev and not gA)


found, tested, missed, tries = 0, 0, [], 0
while found < 200 and tries < 200000:
    tries += 1
    s = random.choice(syms)
    if s not in cache:
        cache[s] = rows(s)
    R = cache[s]; ds = sorted(R)
    if len(ds) < 220 or any((ds[i + 1] - ds[i]).days != 1 for i in range(len(ds) - 1)):
        continue
    k = random.randrange(200, len(ds) - 1); d = ds[k]
    if not (date(2020, 7, 1) <= d < date(2026, 9, 30)):
        continue
    elig, gA, gB = grade_at(R, ds, k)
    if not (elig and (gA or gB)):
        continue
    if any(a <= d < b or a == d for a, b in held_iv.get(s, [])):
        continue
    found += 1
    eq_, cash_ = EQR[str(d)]
    spent = sum(b[2] * (1 + FEE) for t in T0 for b in t["buys"] if b[0][:10] == str(d + timedelta(days=1)))
    spent += sum(b[2] * (1 + FEE) for p in OP0 for b in json.loads(p["buys"]) if b[0][:10] == str(d + timedelta(days=1)))
    if cash_ - spent >= (0.05 if gA else 0.02) * eq_ * (1 + FEE):   # cash left even after all the study's actual buys
        tested += 1
        if (s, d + timedelta(days=1)) not in entries:
            missed.append((s, str(d), "A" if gA else "B"))
ok("V2", found == 200 and not missed, f"{found} graded (coin, day) found by loops; {tested} where cash left after the study's actual buys still covered it: entries missed by the study {len(missed)} {missed[:3]}")
# V3 / V4: replay the P full ledger
T = json.loads((OUT / "P_full_trades.json").read_text())
OP = list(csv.DictReader(open(OUT / "P_full_open_at_end.csv")))
EQ = {r["date"][:10]: float(r["equity"]) for r in csv.DictReader(open(OUT / "P_full_equity.csv"))}
events, bad_px, bad_exit, bad_grade = [], [], [], []
for t in T:
    R = cache.get(t["sym"]) or cache.setdefault(t["sym"], rows(t["sym"]))
    q = 0.0
    for (bd, px, nt, g) in t["buys"]:
        d = date.fromisoformat(bd)
        if abs(R[d][0] / px - 1) > 1e-12:
            bad_px.append((t["sym"], bd, px, R[d][0]))
        q += nt / px
        events.append((d, 0, -nt * (1 + FEE), t["sym"], nt / px))
        if g in ("A", "B"):                                         # a new entry: decided at the close of the prior day
            pd_ = d - timedelta(days=1); ds = sorted(x for x in R if x <= pd_)
            k = len(ds) - 1
            closes = [R[x][3] for x in ds]
            a_u = a_d = None
            for i in range(1, len(closes)):
                ch = closes[i] - closes[i - 1]; u, dn = max(ch, 0.0), max(-ch, 0.0)
                a_u = u if a_u is None else a_u + (u - a_u) / 14; a_d = dn if a_d is None else a_d + (dn - a_d) / 14
            rsi = 100.0 if a_d == 0 else 100 - 100 / (1 + a_u / a_d)
            mh = max(R[x][1] for x in R if pd_ - timedelta(days=89) <= x <= pd_)
            dd = R[pd_][3] / mh - 1; rev = (pd_ - timedelta(days=1)) in R and R[pd_][3] > R[pd_ - timedelta(days=1)][1]
            okg = (dd <= -0.30 and rsi <= 35 + 1e-9 and rev) if g == "A" else (dd <= -0.15 and rsi <= 45 + 1e-9 and rev)
            gap_free = all((ds[i + 1] - ds[i]).days == 1 for i in range(len(ds) - 1))
            if gap_free and not okg:
                bad_grade.append((t["sym"], bd, g, round(dd, 4), round(rsi, 2), rev))
    xd = date.fromisoformat(t["exit"][:10]); o, h, lo, c, _ = R[xd]
    avg = sum(b[2] for b in t["buys"]) / q
    if t["why"] == "tp":
        tpx = None
        for tp in (0.10,):
            tpx = avg * (1 + tp)
        good = abs(t["exit_px"] - (o if o >= tpx else tpx)) <= 1e-9 * tpx and (o >= tpx or h >= tpx)
    elif t["why"] == "delisted":
        good = abs(t["exit_px"] - c) <= 1e-12 * c and max(R) == xd
    else:
        good = False
    if not good:
        bad_exit.append((t["sym"], t["exit"], t["why"], t["exit_px"]))
    events.append((xd, 1, q * t["exit_px"] * (1 - FEE), t["sym"], -q))
ok("V4", not bad_exit, f"{len(T)} exits obey the fill rule (TP: open if open >= TP else TP price; delisting: last close): violations {len(bad_exit)} {bad_exit[:3]}")
ok("V2b", not bad_grade, f"every new entry on a gap-free series meets its grade (dd90, Wilder RSI14, reversal) recomputed by loops: violations {len(bad_grade)} {bad_grade[:3]}")
for p in OP:                                                     # open positions: their buys are cash outflows too
    R = cache.get(p["sym"]) or cache.setdefault(p["sym"], rows(p["sym"]))
    for (bd, px, nt, g) in json.loads(p["buys"]):
        d = date.fromisoformat(bd)
        if abs(R[d][0] / px - 1) > 1e-12:
            bad_px.append((p["sym"], bd, px, R[d][0]))
        events.append((d, 0, -nt * (1 + FEE), p["sym"], nt / px))
# cash loop: buys at the open (order 0), exits after (order 1) on the same day
events.sort(key=lambda e: (e[0], e[1]))
cash, held, ei = 10_000.0, {}, 0
start, end = date(2020, 7, 1), date(2026, 9, 30)
lastc = {}
pick = set(random.sample(sorted(EQ), 20)) | {max(EQ)}
bad_eq = []
d = start
while d <= end:
    while ei < len(events) and events[ei][0] == d:
        _, _, cf, s, dq = events[ei]; cash += cf; held[s] = held.get(s, 0.0) + dq
        if abs(held[s]) < 1e-12:
            del held[s]
        ei += 1
    for s in held:
        R = cache[s]
        if d in R:
            lastc[s] = R[d][3]
    if str(d) in pick:
        e = cash + sum(qq * lastc[s] for s, qq in held.items())
        if abs(e / EQ[str(d)] - 1) > 1e-6:
            bad_eq.append((str(d), e, EQ[str(d)]))
    d += timedelta(days=1)
ok("V3", not bad_px and not bad_eq and ei == len(events),
   f"P full: {len(T)} round trips + {len(OP)} open replayed by an independent cash loop: buy prices == raw opens (bad {len(bad_px)}); "
   f"equity on 21 dates incl. the last within 1e-6 (bad {bad_eq[:3]}); final {cash + sum(qq * lastc[s] for s, qq in held.items()):.2f} vs report {rep['P_full']['final']:.2f}")

# V5: B1 funding per year
for c in ("BTCUSDT", "ETHUSDT"):
    py = {}
    with open(R_ / "data" / "futures_um" / f"{c}_funding.csv", newline="") as f:
        for r in csv.DictReader(f):
            t = datetime.fromisoformat(r["time"][:19])
            if datetime(2020, 7, 1) <= t < datetime(2026, 10, 1):
                py.setdefault(t.year, []).append(float(r["funding_rate"]))
    rb = rep[f"B1_{c}"]["per_year"]
    badf = [y for y, v in py.items() if abs(sum(v) * 100 - rb[str(y)]["net_pct"]) > 1e-9 or len(v) != rb[str(y)]["n"]]
    ok("V5", not badf, f"{c} funding per year recomputed from the CSV: mismatching years {badf}")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
raise SystemExit(1 if False in res else 0)
