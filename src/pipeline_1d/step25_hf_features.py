"""
Step 25: do 15m / 5m candles add to the 1h R24 brain (the 1-day relative question)?
Protocol: logs/strategy_1d_step25_hf/STEP25_PROTOCOL_PREREGISTERED.md (SHA256 locked before any Step 25 model is trained).
"""
import sys
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "pipeline_1d", SRC_DIR / "analytics", SRC_DIR / "execution"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import core_rows_1d as CR
import step13_unseen_coins_1d as S13
import step15_slow_relative_1d as S15
import step19_large_caps_1d as S19
import step22_pre2020_exam_1d as S22
import step23_4h_brain as S23
import step24_1h_brain as S24
from config import DATA_DIR, LOGS_DIR

OUT = LOGS_DIR / "strategy_1d_step25_hf"
PROTO_NAME = "STEP25_PROTOCOL_PREREGISTERED.md"
HF, HF_PRE = DATA_DIR / "universe_hf", DATA_DIR / "universe_pre2020_hf"
START, END, END_BAR, FINAL_T = S24.START, S24.END, S24.END_BAR, S24.FINAL_T
HF_BASE = ["rv5_1h", "rv5_4h", "maxdd5_4h", "maxup5_4h", "volburst5_1h", "upshare5_4h", "ret15_last", "taker15_last", "std15_24h"]
HF_XR = ["rv5_4h", "maxdd5_4h"]
FEATS = S24.FEATS + HF_BASE + [f"xr_{c}" for c in HF_XR]
assert len(FEATS) == 42
REF_R24 = (201548.26, 0.92)


def read_hf(path):
    d = pd.read_csv(path, usecols=["timestamp", "open", "close", "volume", "taker_buy_base"], parse_dates=["timestamp"])
    assert d.timestamp.dtype.kind == "M", path
    return d.sort_values("timestamp").set_index("timestamp")


def gap_ret(d, step):
    r = d.close / d.close.shift(1) - 1
    return r.where(d.index.to_series().diff() == step)


def hf_features(d5, d15, hours):
    """Feature values for hour bars `hours` (DatetimeIndex of bar starts t), using candles with open < t+1h only."""
    r5 = gap_ret(d5, pd.Timedelta(minutes=5))
    w5 = pd.DataFrame(index=d5.index)
    w5["rv5_1h"] = r5.rolling("1h", min_periods=8).std()
    w5["rv5_4h"] = r5.rolling("4h", min_periods=30).std()
    w5["maxdd5_4h"] = d5.close / d5.close.rolling("4h", min_periods=30).max() - 1
    w5["maxup5_4h"] = d5.close / d5.close.rolling("4h", min_periods=30).min() - 1
    w5["volburst5_1h"] = d5.volume.rolling("1h", min_periods=8).max() / d5.volume.rolling("24h", min_periods=200).mean()
    w5["upshare5_4h"] = (d5.close > d5.open).astype(float).rolling("4h", min_periods=30).mean()
    r15 = gap_ret(d15, pd.Timedelta(minutes=15))
    w15 = pd.DataFrame(index=d15.index)
    w15["ret15_last"] = d15.close / d15.open - 1
    w15["taker15_last"] = d15.taker_buy_base / d15.volume
    w15["std15_24h"] = r15.rolling("24h", min_periods=60).std()
    tgt = pd.DataFrame(dict(bar=hours))
    a = pd.merge_asof(tgt.assign(t=tgt.bar + pd.Timedelta(minutes=55)).sort_values("t"),
                      w5.reset_index().rename(columns={"timestamp": "t"}), on="t", direction="backward",
                      tolerance=pd.Timedelta(minutes=55))
    b = pd.merge_asof(tgt.assign(t=tgt.bar + pd.Timedelta(minutes=45)).sort_values("t"),
                      w15.reset_index().rename(columns={"timestamp": "t"}), on="t", direction="backward",
                      tolerance=pd.Timedelta(minutes=45))
    out = a.drop(columns="t").merge(b.drop(columns="t"), on="bar", how="left").set_index("bar")
    return out.replace([np.inf, -np.inf], np.nan)


def add_hf(R, folder, rng_test=None):
    parts, trunc_ok, trunc_n = [], True, 0
    for s, g in R.groupby("symbol"):
        d5 = read_hf(folder / "5m" / f"{s}_5m_full.csv.gz")
        d15 = read_hf(folder / "15m" / f"{s}_15m_full.csv.gz")
        hrs = pd.DatetimeIndex(g.bar.unique()).sort_values()
        f = hf_features(d5, d15, hrs)
        if rng_test is not None and trunc_n < 40 and rng_test.random() < 0.25:
            t = hrs[rng_test.integers(len(hrs))]
            cut = t + pd.Timedelta(hours=1)
            ft = hf_features(d5[d5.index < cut], d15[d15.index < cut], pd.DatetimeIndex([t]))
            x, y = f.loc[t, HF_BASE].values.astype(float), ft.loc[t, HF_BASE].values.astype(float)
            same = np.all((np.isnan(x) & np.isnan(y)) | np.isclose(x, y, rtol=1e-12, atol=0))
            trunc_ok &= bool(same)
            trunc_n += 1
        parts.append(g[["symbol", "bar"]].join(f, on="bar"))
    H = pd.concat(parts)
    R = R.join(H[HF_BASE].astype("float32"))
    for c in HF_XR:
        R[f"xr_{c}"] = R.groupby("bar")[c].rank(pct=True).astype("float32")
    return R, trunc_ok, trunc_n


def paired_auc_diff(y, p_new, p_old, months, reps=2000, seed=1):
    um = np.unique(months)
    idx = {m: np.where(months == m)[0] for m in um}
    rng = np.random.default_rng(seed)
    d = []
    for _ in range(reps):
        k = np.concatenate([idx[m] for m in rng.choice(um, len(um))])
        d.append(roc_auc_score(y[k], p_new[k]) - roc_auc_score(y[k], p_old[k]))
    return dict(diff=float(roc_auc_score(y, p_new) - roc_auc_score(y, p_old)),
                ci_low=float(np.percentile(d, 2.5)), ci_high=float(np.percentile(d, 97.5)))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    h_ = S23.sha_file(OUT / PROTO_NAME)
    assert h_ == (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed after registration"
    t0 = time.time()
    claims = dict(protocol_sha256=h_)
    c24 = json.loads((S24.OUT / "claims.json").read_text())
    assert abs(c24["portfolio"]["R24_AI"]["final"] - REF_R24[0]) < 0.01 and abs(c24["portfolio"]["R24_AI"]["calmar"] - REF_R24[1]) < 1e-9
    split = pd.read_csv(S15.SPLIT)
    A, B = set(split[split.half == "A_design"].symbol), set(split[split.half == "B_confirm"].symbol)
    data_k, last_k, data_n, last_n, _ = CR.load_folder(S13.UNI / "1d", S24.UNI1H, END)
    data, last = {**data_k, **data_n}, {**last_k, **last_n}
    known = list(data_k)
    Ute = S23.daily_members(data, last, known + sorted(B & set(data)), 20, START - pd.Timedelta(days=1), END - pd.Timedelta(days=1))
    Utr = S23.daily_members(data, last, known + sorted(A & set(data)), 30, pd.Timestamp("2020-01-01"), END - pd.Timedelta(days=1))
    del data_k, data_n, data
    btc_close = S24.bars_1h(S24.UNI1H / "BTCUSDT_1h_full.csv.gz").close
    R, px, _ = S24.build_rows(dict(train=Utr, test=Ute), S24.UNI1H, btc_close, hour_filter=dict(train=lambda hr: hr % 3 == 0))
    TR, TE = R["train"], R["test"]
    TE = TE[(TE.bar >= START) & (TE.bar <= END_BAR)].reset_index(drop=True)
    base = pd.read_csv(S24.OUT / "test_predictions_1h.csv", usecols=["symbol", "bar", "R24_AI", "label24"], parse_dates=["bar"])
    g0 = dict(a_rows_identical=len(base) == len(TE) and (base.symbol.values == TE.symbol.values).all()
              and (base.bar.values == TE.bar.values).all())
    print("rows", len(TR), len(TE), g0, f"({time.time()-t0:.0f}s)", flush=True)

    used = sorted(set(TR.symbol) | set(TE.symbol))
    have = set()
    for tf in ("15m", "5m"):
        fl = pd.read_csv(LOGS_DIR / "hf_download" / f"files_log_2020_26_{tf}.csv")
        have |= {(s, tf) for s in fl.symbol.unique()}
    g0["c_sha_logs_for_all_coins"] = all((s, tf) in have for s in used for tf in ("15m", "5m"))
    rng = np.random.default_rng(25)
    TR, ok1, n1 = add_hf(TR, HF, rng)
    TE, ok2, n2 = add_hf(TE, HF, rng)
    g0["b_truncation_selftest"] = ok1 and ok2 and (n1 + n2) >= 40
    claims["truncation_selftest_rows"] = n1 + n2
    claims["hf_missing_share_test"] = {c: float(TE[c].isna().mean()) for c in HF_BASE}
    print("HF features added", g0, claims["hf_missing_share_test"], f"({time.time()-t0:.0f}s)", flush=True)

    p = S24.wf(TR, TE, FEATS, "label24", "known24")
    m = TE.label24.notna() & p.notna()
    claims["R24_HF_skill"] = S23.auc_ci(TE, p, "label24")
    claims["R24_base_skill_same_rows"] = S23.auc_ci(TE, pd.Series(base.R24_AI.values, index=TE.index), "label24")
    claims["paired_auc_diff"] = paired_auc_diff(TE.label24[m].values.astype(int), p[m].values, base.R24_AI.values[m.values],
                                                TE.bar[m].dt.to_period("M").astype(str).values)
    print("skill", claims["R24_HF_skill"], claims["R24_base_skill_same_rows"]["auc"], claims["paired_auc_diff"], f"({time.time()-t0:.0f}s)", flush=True)
    out = TE[["symbol", "bar", "label24"]].assign(R24_HF=p.values, R24_base=base.R24_AI.values)
    out.to_csv(OUT / "test_predictions_hf.csv", index=False)

    runs = {}
    for name, cost in (("R24_HF", 0.0025), ("R24_HF_cost040", 0.0040)):
        res = S24.sim1h(TE[["symbol", "bar"]].assign(score=p.values), 24, px, cost)
        res["trades"].to_csv(OUT / f"{name}_trades.csv", index=False)
        runs[name] = S24.summarize1h(res)
        print(name, runs[name], flush=True)
    claims["portfolio"] = runs

    # 2018-19
    U22 = pd.read_csv(S22.OUT / "U_pre2020_predictions.csv", usecols=["symbol", "date"], parse_dates=["date"])
    btc_pre = S24.bars_1h(S24.PRE1H / "BTCUSDT_1h_full.csv.gz").close
    Rp, _, _ = S24.build_rows(dict(pre=U22), S24.PRE1H, btc_pre)
    P = Rp["pre"]
    P = P[(P.bar >= S24.PRE_START) & (P.bar <= S24.PRE_END + pd.Timedelta(hours=23))].reset_index(drop=True)
    pb = pd.read_csv(S24.OUT / "pre2020_predictions_1h.csv", usecols=["symbol", "bar", "R24_FROZEN"], parse_dates=["bar"])
    g0["d_pre_rows_identical"] = len(pb) == len(P) and (pb.symbol.values == P.symbol.values).all() and (pb.bar.values == P.bar.values).all()
    P, ok3, _ = add_hf(P, HF_PRE)
    tr = TR[(TR.known24 < FINAL_T) & TR.label24.notna()]
    mf = S23.fit(tr[FEATS].values, tr.label24.values.astype(int))
    pp = pd.Series(mf.predict_proba(P[FEATS].values)[:, 1], index=P.index)
    claims["pre2020_HF"] = S23.auc_ci(P, pp, "label24")
    claims["pre2020_base"] = S23.auc_ci(P, pd.Series(pb.R24_FROZEN.values, index=P.index), "label24")
    print("2018-19", claims["pre2020_HF"], claims["pre2020_base"]["auc"], flush=True)
    P[["symbol", "bar", "label24"]].assign(R24_HF_FROZEN=pp.values, R24_FROZEN=pb.R24_FROZEN.values).to_csv(OUT / "pre2020_predictions_hf.csv", index=False)

    gates = {f"G0{k[0]}_{k[2:]}": bool(v) for k, v in g0.items()}
    gates["G0"] = all(g0.values())
    r = runs["R24_HF"]
    gates.update(G2_added_skill=claims["paired_auc_diff"]["ci_low"] > 0,
                 G3a_calmar=r["calmar"] > REF_R24[1], G3b_trade_ci=r["trade_ci_low_pct"] > 0,
                 G3c_cost040=runs["R24_HF_cost040"]["cagr_pct"] > 0,
                 G4_pre2020=claims["pre2020_HF"]["auc"] > claims["pre2020_base"]["auc"] and claims["pre2020_HF"]["ci_low"] > 0.50)
    gates = {k: bool(v) for k, v in gates.items()}
    rest = all(gates[k] for k in ("G3a_calmar", "G3b_trade_ci", "G3c_cost040", "G4_pre2020"))
    gates["decision"] = ("INVALID_G0" if not gates["G0"] else "PASS_HF_ADDS" if gates["G2_added_skill"] and rest else
                         "SKILL_ADD_ONLY" if gates["G2_added_skill"] else "FAIL_HF_ADDS_NOTHING")
    claims["gates"] = gates
    claims["test_predictions_sha256"] = S23.sha_file(OUT / "test_predictions_hf.csv")
    (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=str))
    print("\nGATES:", json.dumps(gates), f"({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
