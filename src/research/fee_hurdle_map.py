"""Fee-hurdle map: BTC move size per holding time vs round-trip cost (protocol logs/fee_hurdle_map/).
Run: python src/research/fee_hurdle_map.py"""
import hashlib, io, json, time, zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "logs" / "fee_hurdle_map"
PROTO_SHA = (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0]
FIVE = ROOT / "data/universe_hf/5m/BTCUSDT_5m_full.csv.gz"
ONES = [ROOT / f"data/external/binance_1s/spot_1s/BTCUSDT-1s-2026-0{m}.zip" for m in range(1, 6)]
H1S = {"10s": 10, "30s": 30, "1m": 60}
H5M = {"5m": 1, "15m": 3, "30m": 6, "1h": 12, "4h": 48, "1d": 288, "3d": 864, "7d": 2016, "14d": 4032, "28d": 8064}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def stats(r):
    a = np.abs(r)
    return {"n": int(len(r)), "mean_r": float(r.mean()), "E_abs_r": float(a.mean()), "median_abs_r": float(np.median(a))}


def main():
    assert sha(OUT / "FEE_HURDLE_PROTOCOL_PREREGISTERED.md") == PROTO_SHA
    f = json.loads((ROOT / "deploy/fees.json").read_text())
    rt = {"fut": 2 * f["rules"]["paper_futures_taker_per_side"], "spot": 2 * f["rules"]["paper_spot_per_side"],
          "maker": 2 * (f["futures_usdm"]["bnb_maker"] + f["impact_per_side"])}
    pd.DataFrame([{"file": str(p.relative_to(ROOT)), "sha256": sha(p)} for p in [FIVE, *ONES, ROOT / "deploy/fees.json"]]).to_csv(
        OUT / "input_manifest.csv", index=False)
    rows, rets = [], {}
    # 1s horizons, each month separately, from the month's first second
    for z in ONES:
        with zipfile.ZipFile(z) as zz:
            d = pd.read_csv(io.BytesIO(zz.read(zz.namelist()[0])), header=None, usecols=[0, 4])
        sec = d[0].to_numpy(np.int64) // 1_000_000
        s0 = sec[0] - sec[0] % 86400
        P = np.full(int(sec[-1] - s0) + 1, np.nan)
        P[sec - s0] = d[4].to_numpy(float)
        for name, h in H1S.items():
            p = P[::h]
            r = p[1:] / p[:-1] - 1
            rets.setdefault(name, []).append(r[np.isfinite(r)])
    # 5m horizons on the full grid
    d = pd.read_csv(FIVE, usecols=["timestamp", "close"])
    d["timestamp"] = pd.to_datetime(d["timestamp"])
    d = d[(d.timestamp >= "2020-01-01") & (d.timestamp < "2026-10-01")].drop_duplicates("timestamp")
    grid = pd.date_range("2020-01-01", "2026-09-30 23:55", freq="5min")
    P = d.set_index("timestamp")["close"].reindex(grid).to_numpy()
    years = grid.year.to_numpy()
    yearly = []
    dropped = {}
    for name, k in H5M.items():
        p = P[::k]
        y = years[::k][:-1]
        r = p[1:] / p[:-1] - 1
        ok = np.isfinite(r)
        dropped[name] = int((~ok).sum())
        rets[name] = [r[ok]]
        if name in ("1h", "1d", "7d"):
            for yy in range(2020, 2027):
                rr = r[ok & (y == yy)]
                e = float(np.abs(rr).mean())
                yearly.append({"horizon": name, "year": yy, "n": len(rr), "E_abs_r": e,
                               "p_star_fut": 0.5 + rt["fut"] / (2 * e), "perfect_net_fut": e - rt["fut"]})
    for name in list(H1S) + list(H5M):
        r = np.concatenate(rets[name])
        s = stats(r)
        s["horizon"] = name
        s["source"] = "1s 2026-01..05" if name in H1S else "5m 2020-01..2026-09"
        s["dropped_missing"] = dropped.get(name, 0)
        for c, v in rt.items():
            s[f"share_abs_gt_{c}"] = float((np.abs(r) > v).mean())
            s[f"perfect_net_{c}"] = s["E_abs_r"] - v
            s[f"p_star_{c}"] = 0.5 + v / (2 * s["E_abs_r"])
        rows.append(s)
    T = pd.DataFrame(rows)
    T.to_csv(OUT / "hurdle_map.csv", index=False)
    pd.DataFrame(yearly).to_csv(OUT / "hurdle_by_year.csv", index=False)
    json.dump({"protocol_sha": PROTO_SHA, "code_sha": sha(Path(__file__)), "rt": rt}, open(OUT / "RESULTS.json", "w"), indent=1)
    (OUT / "OUTPUT_SHA256.txt").write_text("".join(f"{sha(OUT / x)}  {x}\n" for x in
                                                   ["input_manifest.csv", "hurdle_map.csv", "hurdle_by_year.csv", "RESULTS.json"]))
    print(T.to_string())


if __name__ == "__main__":
    main()
