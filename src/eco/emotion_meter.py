"""EMO meter (R-A): hourly crowd-emotion meter, information only. Protocol logs/emotion/EMO_METER_PROTOCOL_PREREGISTERED.md.
Public Binance endpoints only, no keys, NO orders; nothing here feeds ECO decisions.
Usage (VM cron, hourly after the ECO cycle):  python src/eco/emotion_meter.py [--root data/emotion]"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import eco_core as C
import eco_exchange as X

PROJ = C.PROJ
PROTO = PROJ / "logs" / "emotion" / "EMO_METER_PROTOCOL_PREREGISTERED.md"
ENDP = {"oi": "/futures/data/openInterestHist", "top": "/futures/data/topLongShortPositionRatio",
        "retail": "/futures/data/globalLongShortAccountRatio", "taker": "/futures/data/takerlongshortRatio"}
SCORE_FEATS = ("oi_chg_24h", "retail_acct_ls", "taker_24h", "funding")
TEMP_FEATS = ("retail_acct_ls", "taker_24h", "funding", "oi_chg_24h")


def universe(eco_ledger, cap=40):
    syms = {"BTCUSDT", "ETHUSDT"}
    if Path(eco_ledger).exists():
        L = [json.loads(l) for l in Path(eco_ledger).read_text(encoding="utf-8").splitlines() if l.strip()]
        last = next((r for r in reversed(L) if r.get("ok") and ("held_net" in r or "targets_net" in r)), None)
        if last:
            syms |= set(last.get("held_net", {})) | set(last.get("targets_net", {}))
    return sorted(syms)[:cap]


def features(rows, kl, funding, cut_ms):
    """rows: {endpoint key: list of dicts}, kl: klines rows, cut_ms: start of the current hour (only earlier rows count)."""
    d = {k: sorted([r for r in v if int(r["timestamp"]) < cut_ms], key=lambda r: int(r["timestamp"])) for k, v in rows.items()}
    b = [k for k in kl if int(k[0]) < cut_ms and int(k[6]) < cut_ms]          # closed bars only
    oi = [float(r["sumOpenInterestValue"]) for r in d["oi"]]
    if len(oi) < 25 or len(d["taker"]) < 24 or len(b) < 48:
        raise ValueError(f"not enough closed rows: oi {len(oi)}, taker {len(d['taker'])}, bars {len(b)}")
    f = dict(oi_chg_24h=oi[-1] / oi[-25] - 1,
             top_pos_ls=float(np.log(float(d["top"][-1]["longShortRatio"]))),
             retail_acct_ls=float(np.log(float(d["retail"][-1]["longShortRatio"]))),
             taker_24h=float(np.mean([np.log(float(r["buySellRatio"])) for r in d["taker"][-24:]])),
             funding=float(funding))
    f["smart_minus_retail"] = f["top_pos_ls"] - f["retail_acct_ls"]
    hi, lo, op, cl, qv = (np.array([float(k[i]) for k in b]) for i in (2, 3, 1, 4, 7))
    rng = hi[-24:] - lo[-24:]
    m = rng > 0
    f["wick_24h"] = float(np.mean((rng[m] - np.abs(cl[-24:] - op[-24:])[m]) / rng[m]))
    f["vol_surprise"] = float(qv[-24:].sum() / qv[-48:-24].sum() - 1)
    f["ret_24h"] = float(cl[-1] / cl[-25] - 1)
    last_ts = {k: int(v[-1]["timestamp"]) for k, v in d.items()} | {"kline": int(b[-1][0])}
    return f, last_ts


def scores(feats):
    """crowding score = mean percentile rank of SCORE_FEATS (rank / n, ties averaged); market temperature = medians."""
    ok = sorted(s for s, f in feats.items() if all(np.isfinite(f.get(k, np.nan)) for k in SCORE_FEATS))
    if not ok:
        return {}, {}
    df = pd.DataFrame({s: feats[s] for s in ok}).T
    pr = df[list(SCORE_FEATS)].rank(pct=True, method="average")
    sc = {s: float(pr.loc[s].mean()) for s in ok}
    temp = {k: float(np.median(df[k].values)) for k in TEMP_FEATS}
    return sc, temp


def run(src, eco_ledger, now):
    cut = pd.Timestamp(now).floor("h")
    cut_ms = int(cut.value // 10**6)
    syms = universe(eco_ledger)
    prem = src.get("/fapi/v1/premiumIndex") or []
    fund = {x["symbol"]: x.get("lastFundingRate") for x in prem}
    feats, last_ts, errors = {}, {}, []
    for s in syms:
        try:
            rows = {k: src.get(p, symbol=s, period="1h", limit=49) for k, p in ENDP.items()}
            kl = src.get("/fapi/v1/klines", symbol=s, interval="1h", limit=49)
            if any(not v for v in rows.values()) or not kl or fund.get(s) is None:
                raise ValueError("empty answer: " + ",".join(k for k, v in rows.items() if not v) + ("" if kl else " klines"))
            feats[s], last_ts[s] = features(rows, kl, fund[s], cut_ms)
        except Exception as e:                                             # noqa: BLE001 - recorded, symbol left out of the ranks
            errors.append(f"{s}: {type(e).__name__}: {str(e)[:160]}")
    sc, temp = scores(feats)
    top = sorted(sc, key=lambda s: -sc[s])
    return dict(T=str(cut), n_symbols=len(syms), n_ok=len(feats), features=feats, last_ts=last_ts, crowding=sc, temperature=temp,
                most_crowded_long=top[:5], least_crowded=top[-5:][::-1], errors=errors + list(getattr(src, "errors", []))[:20])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/emotion")
    a = ap.parse_args()
    assert C.sha_f(PROTO) == (PROTO.parent / "EMO_METER_PROTOCOL_SHA256.txt").read_text().split()[0], "EMO meter protocol changed"
    root = PROJ / a.root
    root.mkdir(parents=True, exist_ok=True)
    now = pd.Timestamp.now("UTC").tz_localize(None)
    L = root / "ledger.jsonl"
    if L.exists() and L.stat().st_size:
        last = json.loads(L.read_text(encoding="utf-8").strip().splitlines()[-1])
        if last["T"] == str(now.floor("h")):
            print("emotion meter: hour already recorded"); return
    rec = run(X.Public(X.PUBLIC), PROJ / "data" / "eco" / "ledger.jsonl", now)
    rec.update(run_utc=str(now), code_sha256=C.sha_f(Path(__file__)), protocol_sha256=C.sha_f(PROTO))
    C.append_ledger(L, rec)
    print(f"emotion {rec['T']}: {rec['n_ok']}/{rec['n_symbols']} symbols, temperature {({k: round(v, 5) for k, v in rec['temperature'].items()})}, "
          f"most crowded long {rec['most_crowded_long']}, errors {len(rec['errors'])}")


if __name__ == "__main__":
    main()
