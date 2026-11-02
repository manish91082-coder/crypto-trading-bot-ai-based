"""Independent verifier of MK1 (logs/eco_maker/MK1_PROTOCOL_PREREGISTERED.md). Imports nothing from src/eco_maker.
K1 protocol lock + every stored kline zip matches KLINES_MANIFEST; K2 the order set equals the ledger orders since the cut-over;
K3 every row recomputed (fill flags, costs, deltas) from the zips; K4 the summary (weighted means, CI) recomputed."""
import csv
import hashlib
import json
import math
import sys
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

P = Path(__file__).resolve().parents[2]
O = P / "data/eco_maker"
res = []


def ok(n, g, m):
    res.append(bool(g)); print(f"[{n} {'PASS' if g else 'FAIL'}] {m}", flush=True)


pr = P / "logs/eco_maker/MK1_PROTOCOL_PREREGISTERED.md"
man = [l.split(",") for l in (O / "KLINES_MANIFEST.csv").read_text(encoding="utf-8").splitlines() if l.strip()] if (O / "KLINES_MANIFEST.csv").exists() else []
bad = [k for k, s, _ in man if hashlib.sha256((O / "klines1m" / k.split("/")[5] / k.rsplit("/", 1)[1]).read_bytes()).hexdigest() != s]
ok("K1", hashlib.sha256(pr.read_bytes()).hexdigest() == (P / "logs/eco_maker/PROTOCOL_SHA256.txt").read_text().split()[0] and not bad,
   f"protocol lock; {len(man)} kline zips match manifest, bad {bad}")
f = json.loads((P / "deploy/fees.json").read_text(encoding="utf-8"))
C = {"demo": (f["demo_account_charged_taker"] * 1e4, f["futures_usdm"]["base_maker"] * 1e4), "real": (f["futures_usdm"]["bnb_taker"] * 1e4, f["futures_usdm"]["bnb_maker"] * 1e4)}
cut = datetime(2026, 10, 25, 4, 21)
orders = []
for l in (P / "data/eco_demo/ledger.jsonl").read_text(encoding="utf-8").splitlines():
    if not l.strip():
        continue
    r = json.loads(l)
    if not r.get("ok"):
        continue
    T = datetime.strptime(str(r["T"])[:19], "%Y-%m-%d %H:%M:%S")
    if T >= cut:
        for o in r.get("orders", []):
            m = r["price"].get(o["perp"])
            if m and o.get("qty"):
                orders.append((T, o["perp"], 1 if o["qty"] > 0 else -1, abs(o["qty"]) * m, m, float(o["px"])))
stored = list(csv.DictReader(open(O / "mk1_orders.csv", encoding="utf-8")))
sm = json.loads((O / "mk1_summary.json").read_text(encoding="utf-8"))
avail = [x for x in orders if (O / "klines1m" / x[1] / f"{x[1]}-1m-{x[0]:%Y-%m-%d}.zip").exists()]
ok("K2", len(stored) == len(avail) and len(orders) - len(avail) == sm["pending_klines"],
   f"orders since cut-over {len(orders)}; with klines {len(avail)}; stored {len(stored)}; pending {sm['pending_klines']}")
kc = {}


def bars(sym, day):
    if (sym, day) not in kc:
        z = zipfile.ZipFile(O / "klines1m" / sym / f"{sym}-1m-{day}.zip")
        d = {}
        for line in z.read(z.namelist()[0]).decode().splitlines():
            if line and line[0].isdigit():
                x = line.split(","); v = int(x[0])
                d[datetime(1970, 1, 1) + (timedelta(microseconds=v) if v > 10 ** 14 else timedelta(milliseconds=v))] = (float(x[2]), float(x[3]), float(x[4]))
        kc[(sym, day)] = d
    return kc[(sym, day)]


badr = 0
mine = []
for (T, sym, sd, nt, m, fx), s in zip(avail, stored):
    k = bars(sym, f"{T:%Y-%m-%d}")
    row = {"nt": nt, "T": T}
    if s["perp"] != sym or int(s["side"]) != sd or abs(float(s["notional"]) - nt) > 1e-9:
        badr += 1; continue
    slip = sd * (fx / m - 1) * 1e4
    for W in (5, 15):
        bb = [k.get(T + timedelta(minutes=j)) for j in range(1, W)]
        last = k.get(T + timedelta(minutes=W - 1))
        if last is None or None in bb:
            badr += s[f"filled_{W}"] != ""
            continue
        fill = any((b[1] < m) if sd > 0 else (b[0] > m) for b in bb)
        badr += s[f"filled_{W}"] != str(fill)
        for c, (tk, mk) in C.items():
            d = (mk if fill else sd * (last[2] / m - 1) * 1e4 + slip + tk) - (slip + tk)
            row[(W, c)] = d
            badr += abs(float(s[f"d{W}_{c}"]) - d) > 1e-9
    mine.append(row)
ok("K3", badr == 0, f"{len(mine)} rows recomputed (fill flags, deltas, both fee columns): {badr} mismatches")
bads = 0
for W in (5, 15):
    for c in C:
        xs = [r for r in mine if (W, c) in r]
        if not xs:
            continue
        sw = sum(r["nt"] for r in xs); mean = sum(r["nt"] * r[(W, c)] for r in xs) / sw
        bads += abs(sm[f"W{W}"][c]["delta_bps"] - mean) > 1e-9
        wk = {}
        for r in xs:
            kk = tuple(r["T"].isocalendar())[:2]; wk[kk] = wk.get(kk, 0.0) + r["nt"] * (r[(W, c)] - mean)
        if len(wk) > 1:
            se = math.sqrt(len(wk) / (len(wk) - 1) * sum(v * v for v in wk.values())) / sw
            bads += abs(sm[f"W{W}"][c]["ci95"][1] - (mean + 1.96 * se)) > 1e-9
ok("K4", bads == 0, f"summary weighted means and CIs recomputed: {bads} mismatches")
print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
sys.exit(1 if False in res else 0)
