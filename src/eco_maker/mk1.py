"""MK1 (logs/eco_maker/MK1_PROTOCOL_PREREGISTERED.md, SHA 8a8b2f72...): for every ECO DEMO order since the cut-over, the cost of the
actual MARKET fill vs a limit-at-mark with market fallback after W = 5 / 15 min, from 1m futures klines (data.binance.vision, checksum-verified).
Measurement only: changes nothing in ECO. Usage (VM): python src/eco_maker/mk1.py [--ledger data/eco_demo/ledger.jsonl]"""
import argparse
import csv
import hashlib
import io
import json
import math
import time
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJ = Path(__file__).resolve().parents[2]
OUT = PROJ / "data/eco_maker"
F = json.loads((PROJ / "deploy/fees.json").read_text(encoding="utf-8"))
COSTS = {"demo": (F["demo_account_charged_taker"] * 1e4, F["futures_usdm"]["base_maker"] * 1e4),
         "real": (F["futures_usdm"]["bnb_taker"] * 1e4, F["futures_usdm"]["bnb_maker"] * 1e4)}
CUT = datetime(2026, 10, 25, 4, 21)
WS = (5, 15)


def get(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if i == tries - 1:
                raise
        except Exception:                                    # noqa: BLE001  (network retry)
            if i == tries - 1:
                raise
        time.sleep(3 * (i + 1))


def klines(sym, day, log):
    """1m bars of one symbol-day: {open_time: (high, low, close)}; None if not yet published or checksum fails."""
    d = OUT / "klines1m" / sym
    d.mkdir(parents=True, exist_ok=True)
    name = f"{sym}-1m-{day}.zip"
    f = d / name
    key = f"data/futures/um/daily/klines/{sym}/1m/{name}"
    if not f.exists():
        want = get("https://data.binance.vision/" + key + ".CHECKSUM")
        if want is None:
            return None
        data = get("https://data.binance.vision/" + key)
        if data is None or hashlib.sha256(data).hexdigest() != want.decode().split()[0]:
            log(f"checksum FAIL or missing {key}")
            return None
        f.write_bytes(data)
        with open(OUT / "KLINES_MANIFEST.csv", "a", encoding="utf-8") as m:
            m.write(f"{key},{hashlib.sha256(data).hexdigest()},{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ}\n")
    z = zipfile.ZipFile(f)
    out = {}
    for line in z.read(z.namelist()[0]).decode().splitlines():
        if not line or not line[0].isdigit():
            continue
        x = line.split(",")
        v = int(x[0])
        t = datetime(1970, 1, 1) + (timedelta(microseconds=v) if v > 10 ** 14 else timedelta(milliseconds=v))
        out[t] = (float(x[2]), float(x[3]), float(x[4]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", default="data/eco_demo/ledger.jsonl")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    def log(msg):
        line = f"{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ} {msg}"
        print(line, flush=True)
        with open(OUT / "run_log.txt", "a", encoding="utf-8") as f:
            f.write(line + "\n")

    log(f"mk1 start; code {hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12]}; protocol "
        f"{hashlib.sha256((PROJ / 'logs/eco_maker/MK1_PROTOCOL_PREREGISTERED.md').read_bytes()).hexdigest()[:12]}")
    recs = [json.loads(l) for l in (PROJ / a.ledger).read_text(encoding="utf-8").splitlines() if l.strip()]
    rows, pending, cache = [], 0, {}
    for r in recs:
        if not r.get("ok"):
            continue
        T = datetime.strptime(str(r["T"])[:19], "%Y-%m-%d %H:%M:%S")
        if T < CUT:
            continue
        for o in r.get("orders", []):
            m = r["price"].get(o["perp"])
            if not m or not o.get("qty"):
                continue
            sym, side, fpx = o["perp"], (1 if o["qty"] > 0 else -1), float(o["px"])
            day = T.strftime("%Y-%m-%d")
            if (sym, day) not in cache:
                cache[(sym, day)] = klines(sym, day, log)
            k = cache[(sym, day)]
            if k is None:
                pending += 1
                continue
            slip = side * (fpx / m - 1) * 1e4
            row = dict(T=T.strftime("%Y-%m-%d %H:%M"), perp=sym, side=side, notional=abs(o["qty"]) * m, mark=m, fill=fpx, slip_bps=slip)
            for W in WS:
                bars = [k.get(T + timedelta(minutes=j)) for j in range(1, W)]
                last = k.get(T + timedelta(minutes=W - 1))
                if last is None or any(b is None for b in bars):
                    row[f"filled_{W}"] = None
                    continue
                filled = any((b[1] < m) if side > 0 else (b[0] > m) for b in bars)
                row[f"filled_{W}"] = filled
                move = side * (last[2] / m - 1) * 1e4
                for col, (tk, mk) in COSTS.items():
                    mkt = slip + tk
                    lim = mk if filled else move + slip + tk
                    row[f"mkt_{col}"], row[f"lim{W}_{col}"], row[f"d{W}_{col}"] = mkt, lim, lim - mkt
            rows.append(row)
    cols = ["T", "perp", "side", "notional", "mark", "fill", "slip_bps"] + [f"filled_{W}" for W in WS] + \
           ["mkt_demo", "mkt_real"] + [f"{p}{W}_{c}" for W in WS for p in ("lim", "d") for c in COSTS]
    with open(OUT / "mk1_orders.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)
    summ = dict(run_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), n_orders=len(rows), pending_klines=pending, decision_at=300)
    for W in WS:
        ok = [x for x in rows if x.get(f"filled_{W}") is not None]
        sw = sum(x["notional"] for x in ok)
        summ[f"W{W}"] = dict(n=len(ok), fill_rate=sum(x[f"filled_{W}"] for x in ok) / len(ok) if ok else None)
        for c in COSTS:
            if not ok:
                continue
            mean = sum(x["notional"] * x[f"d{W}_{c}"] for x in ok) / sw
            wk = {}
            for x in ok:
                key = tuple(datetime.strptime(x["T"], "%Y-%m-%d %H:%M").isocalendar())[:2]
                wk[key] = wk.get(key, 0.0) + x["notional"] * (x[f"d{W}_{c}"] - mean)
            se = math.sqrt(len(wk) / (len(wk) - 1) * sum(v * v for v in wk.values())) / sw if len(wk) > 1 else None
            summ[f"W{W}"][c] = dict(mkt_bps=sum(x["notional"] * x[f"mkt_{c}"] for x in ok) / sw, lim_bps=sum(x["notional"] * x[f"lim{W}_{c}"] for x in ok) / sw,
                                    delta_bps=mean, ci95=None if se is None else [mean - 1.96 * se, mean + 1.96 * se], weeks=len(wk))
    (OUT / "mk1_summary.json").write_text(json.dumps(summ, indent=1), encoding="utf-8")
    log(f"mk1: {json.dumps(summ)}")


if __name__ == "__main__":
    main()
