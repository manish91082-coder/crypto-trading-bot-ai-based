"""Independent verifier for the fee-hurdle map (checks H1-H4). Own csv/gzip/zipfile reading and plain loops.
Run: python src/audits/verify_fee_hurdle_map.py"""
import csv, gzip, hashlib, io, json, zipfile
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "logs" / "fee_hurdle_map"
res = []


def check(n, ok, d=""):
    res.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {n}  {d}", flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                return h.hexdigest()
            h.update(b)


def close(a, b, t=1e-9):
    return abs(a - b) <= t * max(1.0, abs(a), abs(b))


def main():
    check("H1 protocol SHA", sha(OUT / "FEE_HURDLE_PROTOCOL_PREREGISTERED.md") == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0])
    man = list(csv.DictReader(open(OUT / "input_manifest.csv")))
    check("H1 input SHAs", all(sha(ROOT / r["file"]) == r["sha256"] for r in man), f"{len(man)} files")
    fees = json.loads((ROOT / "deploy/fees.json").read_text())
    rt_fut = 2 * fees["rules"]["paper_futures_taker_per_side"]
    rt_spot = 2 * fees["rules"]["paper_spot_per_side"]
    rt_mk = 2 * (fees["futures_usdm"]["bnb_maker"] + fees["impact_per_side"])
    main_rows = {r["horizon"]: r for r in csv.DictReader(open(OUT / "hurdle_map.csv"))}
    mine = {}
    # 1s horizons
    acc = {10: [0, 0.0, 0], 30: [0, 0.0, 0], 60: [0, 0.0, 0]}
    for m in range(1, 6):
        prices = {}
        with zipfile.ZipFile(ROOT / f"data/external/binance_1s/spot_1s/BTCUSDT-1s-2026-0{m}.zip") as z:
            with z.open(z.namelist()[0]) as fh:
                for row in csv.reader(io.TextIOWrapper(fh, "ascii")):
                    prices[int(row[0]) // 1_000_000] = float(row[4])
        s0 = min(prices)
        s0 -= s0 % 86400
        last = max(prices)
        for h, a in acc.items():
            t = s0
            while t + h <= last:
                p0, p1 = prices.get(t), prices.get(t + h)
                if p0 is not None and p1 is not None:
                    r = p1 / p0 - 1
                    a[0] += 1
                    a[1] += abs(r)
                    a[2] += abs(r) > rt_fut
                t += h
    for name, h in (("10s", 10), ("30s", 30), ("1m", 60)):
        n, s, g = acc[h]
        mine[name] = (n, s / n, g / n)
    # 5m horizons
    closes = {}
    with gzip.open(ROOT / "data/universe_hf/5m/BTCUSDT_5m_full.csv.gz", "rt") as f:
        rd = csv.reader(f)
        next(rd)
        for row in rd:
            ts = row[0][:19]
            if "2020-01-01" <= ts[:10] <= "2026-09-30":
                closes.setdefault(ts, float(row[4]))
    start = datetime(2020, 1, 1)
    nsteps = int((datetime(2026, 10, 1) - start).total_seconds() // 300)
    keys = [(start + timedelta(minutes=5 * i)).strftime("%Y-%m-%d %H:%M:%S") for i in range(nsteps)]
    for name, k in (("5m", 1), ("15m", 3), ("30m", 6), ("1h", 12), ("4h", 48), ("1d", 288), ("3d", 864), ("7d", 2016), ("14d", 4032), ("28d", 8064)):
        n = g = 0
        s = 0.0
        i = 0
        while i + k < nsteps:
            p0, p1 = closes.get(keys[i]), closes.get(keys[i + k])
            if p0 is not None and p1 is not None:
                r = p1 / p0 - 1
                n += 1
                s += abs(r)
                g += abs(r) > rt_fut
            i += k
        mine[name] = (n, s / n, g / n)
    for name, (n, e, g) in mine.items():
        r = main_rows[name]
        ok = n == int(r["n"]) and close(e, float(r["E_abs_r"])) and close(g, float(r["share_abs_gt_fut"]))
        check(f"H2 {name} n / E|r| / share>fee", ok, f"n {n}, E|r| {e * 100:.4f}%")
        ok3 = close(0.5 + rt_fut / (2 * e), float(r["p_star_fut"])) and close(0.5 + rt_spot / (2 * e), float(r["p_star_spot"])) \
            and close(0.5 + rt_mk / (2 * e), float(r["p_star_maker"])) and close(e - rt_fut, float(r["perfect_net_fut"]))
        check(f"H3 {name} p* and perfect net", ok3, f"p*fut {(0.5 + rt_fut / (2 * e)) * 100:.1f}%")
    good = all(sha(OUT / l.split()[1]) == l.split()[0] for l in (OUT / "OUTPUT_SHA256.txt").read_text().splitlines())
    check("H4 output SHAs", good)
    print(f"\nTOTAL {len(res)} checks, {sum(res)} PASS, {len(res) - sum(res)} FAIL -> {'ALL PASS' if all(res) else 'FAILURES'}")


if __name__ == "__main__":
    main()
