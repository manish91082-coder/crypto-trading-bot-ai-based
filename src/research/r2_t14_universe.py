"""T14: the A3 brain on the expanded universe (protocol logs/r2_4h_t14/T14_PROTOCOL_PREREGISTERED.md).
Stage 1 (store): signals + trades + features for every candidate coin with the A1c / A2 code paths, PIT liquidity filter,
regression check vs the A2 store. Stage 2 (model): the A3 pipeline (same functions) with N trials = 14."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import probe_scalein as P
import master_audit_portfolio as MA
import r2_a1_edge_map as A1
import r2_realtime_pivots as RT
import r2_a2_store as A2
import swing_anatomy_phase1 as SA
import ladder_sessions as L

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "logs" / "r2_4h_t14"
ST = ROOT / "data" / "derived" / "r2_t14"
SIG = {"S-LAD": 0, "S-BRK": 1, "S-TRD": 2, "S-DTB": 3}
LIQ, LIQ_DAYS, LIQ_MIN_DAYS = 50e6, 30, 20


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def candidates():
    s = lambda d, pat: {p.name.split("_")[0] for p in (ROOT / d).glob(pat)}
    return sorted(s("data/universe_hf/5m", "*_5m_full.csv.gz") & s("data/universe_all/1h", "*_1h_full.csv.gz")
                  & s("data/universe_all/1d", "*_1d.csv") & s("data/futures_um", "*_funding.csv") & s("data/futures_um", "*_perp_1h.csv.gz"))


def coin_trades(coin, fund):
    bsig, h = RT.bars4h(coin)
    sig, _ = RT.swing_signals(coin, bsig, P.START, P.END)
    b = P.bars(coin, "4h")
    idx = {t: i for i, t in enumerate(b.index)}
    O, H, Lo, C = (b[k].values.astype("float64") for k in ("open", "high", "low", "close"))
    rows = []
    for name, side, kt, piv, A, failed in sig:
        e = idx.get(pd.Timestamp(kt))
        if e is None or e + A1.T > len(O):
            continue
        stop = piv - P.BUF * A if side == "long" else piv + P.BUF * A
        r = A1.one_trade(O, H, Lo, C, e, side, stop, A)
        if r:
            rows.append(dict(signal=name, coin=coin, side=side, entry_time=b.index[e], **r))
    atr = A1.atr14(b)
    for sname in ("S-BRK", "S-TRD"):
        busy = {"long": -1, "short": -1}
        for i, side in A1.bar_signals(b, sname):
            e = i + 1
            if i <= busy[side] or e + A1.T > len(O) or not np.isfinite(atr[i]) or not (P.START <= b.index[e] < P.END):
                continue
            A = atr[i]
            stop = O[e] - 2 * A if side == "long" else O[e] + 2 * A
            r = A1.one_trade(O, H, Lo, C, e, side, stop, A)
            if r:
                rows.append(dict(signal=sname, coin=coin, side=side, entry_time=b.index[e], **r))
                busy[side] = e + r["exit_idx"]
    D = pd.DataFrame(rows)
    if D.empty:
        return D, bsig, h, b
    first = pd.Timestamp(fund[coin][0][0])
    D["perp_ok"] = D.entry_time >= first
    D["funding_R"] = [MA.fund_R(fund, coin, s, [(1.0, px, 0)], et, x, "4h", R) for s, px, et, x, R in
                      zip(D.side, D.entry_px, D.entry_time, D.exit_idx, D.R_price)]
    for k, s in A1.COSTS.items():
        D[f"fee_{k}"] = s * (D.entry_px + D.exit_px) / D.R_price
        D[f"net_{k}"] = D.gross - D[f"fee_{k}"] - D.funding_R
    D["year"] = D.entry_time.dt.year
    D["period"] = np.where(D.entry_time < A1.P1_END, "P1", np.where(D.entry_time < A1.DEV_END, "P2", "P3"))
    return D, bsig, h, b


def liquidity(coin):
    v = pd.read_csv(ROOT / "data" / "futures_um" / f"{coin}_perp_1h.csv.gz", usecols=["timestamp", "quote_volume"], parse_dates=["timestamp"])
    d = v.set_index("timestamp").quote_volume.resample("1D").sum(min_count=1).dropna()
    return d


def liq_ok(daily, T):
    day = pd.Timestamp(T).floor("D")
    w = daily[(daily.index >= day - pd.Timedelta(days=LIQ_DAYS)) & (daily.index < day)]
    return bool(len(w) >= LIQ_MIN_DAYS and w.median() >= LIQ), float(w.median()) if len(w) else np.nan, int(len(w))


def build():
    coins = candidates()
    fund = MA.load_funding(coins)
    ccols = [c for c in pd.read_parquet(L.LEGS).columns if c.startswith("c_")]
    fng = SA.fng_table()
    btc_b, _ = RT.bars4h("BTCUSDT")
    allT, allS = [], []
    for n, coin in enumerate(coins):
        D, bsig, h, b = coin_trades(coin, fund)
        if D.empty:
            continue
        cx = A2.context(coin, bsig, h, None if coin == "BTCUSDT" else btc_b, fng)
        tl = RT.Timeline(bsig)
        D = D.sort_values("entry_time").reset_index(drop=True)
        lists = A2.live_lists(tl, list(D.entry_time))
        mf = ROOT / "data" / "futures_info" / f"{coin}_metrics_daily.csv"
        m = pd.read_csv(mf, parse_dates=["date"]).set_index("date") if mf.exists() else None
        f = pd.read_csv(ROOT / "data" / "futures_um" / f"{coin}_funding.csv"); f["time"] = pd.to_datetime(f["time"]); f = f.sort_values("time").reset_index(drop=True)
        dv = liquidity(coin)
        idx = {ts: i for i, ts in enumerate(b.index)}
        O, C = b.open.values, b.close.values
        rows = []
        for r, cur in zip(D.itertuples(index=False), lists):
            T = pd.Timestamp(r.entry_time)
            ok, med, nd = liq_ok(dv, T)
            x = dict(signal=r.signal, coin=coin, side_str=r.side, entry_time=T, available_at=T, perp_ok=r.perp_ok, period=r.period,
                     net_base=r.net_base, label=int(r.net_base > 0), signal_type=SIG[r.signal], side=1 if r.side == "long" else -1,
                     liq_ok=ok, liq_median=med, liq_days=nd)
            x.update(A2.swing_feats_from_list(cur, bsig, cx, ccols))
            x.update(A2.metric_feats(m, T) if m is not None else {k: np.nan for k in A2.F6})
            x.update(A2.funding_feat(f, T))
            e = idx[T]
            x["canary_next_ret"] = C[e + 5] / O[e] - 1 if e + 5 < len(C) else np.nan
            rows.append(x)
        allS.append(pd.DataFrame(rows)); allT.append(D)
        print(f"{n + 1}/{len(coins)} {coin}: trades {len(D)}, liquid {sum(r['liq_ok'] for r in rows)}", flush=True)
    return pd.concat(allT, ignore_index=True), pd.concat(allS, ignore_index=True)


def main():
    proto = OUT / "T14_PROTOCOL_PREREGISTERED.md"
    assert sha(proto) == (OUT / "T14_PROTOCOL_SHA256.txt").read_text().split()[0], "T14 protocol changed"
    ST.mkdir(parents=True, exist_ok=True)
    T, S = build()
    T.to_parquet(ST / "t14_trades_all.parquet", index=False)
    S.to_parquet(ST / "t14_rows_all.parquet", index=False)
    # regression check vs A2 store (10 research coins)
    a2 = pd.read_parquet(ROOT / "data" / "derived" / "r2_a2" / "feature_store.parquet")
    feats = json.loads((ROOT / "data" / "derived" / "r2_a2" / "feature_list.json").read_text())
    key = ["signal", "coin", "side_str", "entry_time"]
    m = a2.merge(S, on=key, suffixes=("", "_t14"))
    bad = {c: int((~np.isclose(m[c].astype(float), m[c + "_t14"].astype(float), rtol=1e-9, atol=1e-12, equal_nan=True)).sum())
           for c in feats + ["net_base"]}
    reg = dict(a2_rows=len(a2), matched=len(m), a2_rows_not_in_t14=int(len(a2) - len(m)), mismatches={k: v for k, v in bad.items() if v})
    print("regression vs A2:", reg, flush=True)
    assert not reg["mismatches"] and reg["a2_rows_not_in_t14"] == 0, "regression check failed -> stop before modelling"
    Sl = S[S.liq_ok].reset_index(drop=True)
    Sl.to_parquet(ST / "feature_store.parquet", index=False)
    (ST / "feature_list.json").write_text(json.dumps(feats, indent=1))
    T.rename(columns={}).to_parquet(ST / "a1c_trades.parquet", index=False)
    summary = dict(protocol_sha=sha(proto), candidates=len(candidates()), coins_with_trades=int(S.coin.nunique()),
                   rows_all=len(S), rows_liquid=len(Sl), coins_liquid=int(Sl.coin.nunique()), regression=reg,
                   liquid_by_period=Sl.groupby("period").size().to_dict(), store_sha=sha(ST / "feature_store.parquet"),
                   trades_sha=sha(ST / "a1c_trades.parquet"))
    (OUT / "t14_store_summary.json").write_text(json.dumps(summary, indent=1, default=str))
    print(json.dumps(summary, indent=1, default=str))


if __name__ == "__main__":
    main()
