"""
S3: futures features (funding + basis) added to R6 / R24 / D1; paired test vs the stored research predictions on
identical rows. Protocol: logs/research_s3_futures_features/S3_PROTOCOL_PREREGISTERED.md
Usage: python s3_futures_features.py R6|R24|D1
"""
import sys
import json
import time
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "pipeline_1d", SRC_DIR / "analytics", SRC_DIR / "execution", SRC_DIR / "research"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
import core_rows_1d as CR
import step11_ai_confident_1d as S11
import step13_unseen_coins_1d as S13
import step15_slow_relative_1d as S15
import step19_large_caps_1d as S19
import step22_pre2020_exam_1d as S22
import step23_4h_brain as S23
import step24_1h_brain as S24
import s2_bear_training as S2
from config import DATA_DIR, LOGS_DIR

OUT = LOGS_DIR / "research_s3_futures_features"
PROTO = "S3_PROTOCOL_PREREGISTERED.md"
FUM = DATA_DIR / "futures_um"
GATE = LOGS_DIR / "strategy_f2_longshort" / "F1_G2_scale_gate.csv"
FUT = ["basis_now", "basis_7d", "fund_24h", "fund_7d"]
FUT_ALL = FUT + ["xr_basis_now", "xr_fund_24h"]
H = pd.Timedelta(hours=1)
_CACHE = {}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def coin_fut(sym):
    """Hourly futures features indexed by the END time of each spot hour bar (known at that moment)."""
    if sym in _CACHE:
        return _CACHE[sym]
    g = pd.read_csv(GATE).set_index("symbol")
    spot = S24.bars_1h(S24.UNI1H / f"{sym}_1h_full.csv.gz").close.astype("float64") if (S24.UNI1H / f"{sym}_1h_full.csv.gz").exists() else None
    if spot is None:
        _CACHE[sym] = None
        return None
    f = pd.DataFrame(index=spot.index + H)
    if sym in g.index and g.at[sym, "status"] == "ok":
        d = pd.read_csv(FUM / f"{sym}_perp_1h.csv.gz", usecols=["timestamp", "close"], parse_dates=["timestamp"]).set_index("timestamp").close
        d = d / float(g.at[sym, "scale"])
        b = (d.reindex(spot.index) / spot - 1).replace([np.inf, -np.inf], np.nan)
        b.index = b.index + H
        f["basis_now"] = b.values
        f["basis_7d"] = b.rolling("168h", min_periods=48).mean().values
        ff = FUM / f"{sym}_funding.csv"
        if ff.exists():
            fr = pd.read_csv(ff, parse_dates=["time"]).sort_values("time")
            et, cs = fr.time.values, np.r_[0.0, np.cumsum(fr.funding_rate.values)]
            te = f.index.values
            for name, w in (("fund_24h", np.timedelta64(24, "h")), ("fund_7d", np.timedelta64(7, "D"))):
                hi, lo = np.searchsorted(et, te, "right"), np.searchsorted(et, te - w, "right")
                v = cs[hi] - cs[lo]
                v[hi == 0] = np.nan                                            # before the first funding event
                f[name] = v
        else:
            f["fund_24h"], f["fund_7d"] = np.nan, np.nan
    else:
        for c in FUT:
            f[c] = np.nan
    _CACHE[sym] = f
    return f


def add_fut(R, tcol, bar_len):
    parts = []
    for s, g in R.groupby("symbol", sort=False):
        f = coin_fut(s)
        t_end = pd.DatetimeIndex(g[tcol].values) + bar_len
        x = f.reindex(t_end)[FUT].values if f is not None else np.full((len(g), len(FUT)), np.nan)
        parts.append(pd.DataFrame(x, index=g.index, columns=FUT))
    A = pd.concat(parts).reindex(R.index)
    R = pd.concat([R.drop(columns=[c for c in FUT_ALL if c in R]), A.astype("float64")], axis=1)
    R["xr_basis_now"] = R.groupby(tcol).basis_now.rank(pct=True)
    R["xr_fund_24h"] = R.groupby(tcol).fund_24h.rank(pct=True)
    return R


def years_diff(T, label, tcol, p_new, p_old):
    out = {}
    for y in range(2021, 2027):
        m = (T[tcol].dt.year == y) & T[label].notna()
        out[y] = float(roc_auc_score(T[label][m].astype(int), p_new[m]) - roc_auc_score(T[label][m].astype(int), p_old[m.values]))
    return out


def run_intraday(name):
    mod, h = (S23, 6) if name == "R6" else (S24, 24)
    base_file = S23.OUT / "test_predictions_4h.csv" if name == "R6" else S24.OUT / "test_predictions_1h.csv"
    col, label, known = f"{name}_AI", f"label{h}", f"known{h}"
    A, B = S2.split_sets()
    data_k, last_k, data_n, last_n, _ = CR.load_folder(S13.UNI / "1d", S23.UNI1H, S23.END)
    data, last = {**data_k, **data_n}, {**last_k, **last_n}
    kc = list(data_k)
    Ute = S23.daily_members(data, last, kc + sorted(B & set(data)), 20, S23.START - pd.Timedelta(days=1), S23.END - pd.Timedelta(days=1))
    Utr = S23.daily_members(data, last, kc + sorted(A & set(data)), 30, pd.Timestamp("2020-01-01"), S23.END - pd.Timedelta(days=1))
    del data_k, data_n, data
    bars = S23.bars_4h if name == "R6" else S24.bars_1h
    btc = bars(S23.UNI1H / "BTCUSDT_1h_full.csv.gz").close
    if name == "R24":
        R, px, _ = S24.build_rows(dict(train=Utr, test=Ute), S23.UNI1H, btc, hour_filter=dict(train=lambda hr: hr % 3 == 0))
    else:
        R, px, _ = S23.build_rows(dict(train=Utr, test=Ute), S23.UNI1H, btc)
    TR, TE = R["train"], R["test"]
    end_bar = S23.END_BAR if name == "R6" else S24.END_BAR
    TE = TE[(TE.bar >= S23.START) & (TE.bar <= end_bar)].reset_index(drop=True)
    base = pd.read_csv(base_file, usecols=["symbol", "bar", col], parse_dates=["bar"])
    g0 = dict(rows_identical=bool(len(base) == len(TE) and (base.symbol.values == TE.symbol.values).all() and (base.bar.values == TE.bar.values).all()))
    bl = pd.Timedelta(hours=4) if name == "R6" else H
    TR, TE = add_fut(TR, "bar", bl), add_fut(TE, "bar", bl)
    cov = {c: float(TE[c].notna().mean()) for c in FUT}
    g0["basis_coverage_ge_50pct"] = bool(cov["basis_now"] >= 0.5)
    print(name, "rows", len(TR), len(TE), g0, cov, flush=True)
    p = mod.wf(TR, TE, mod.FEATS + FUT_ALL, label, known)
    pr = S2.paired(TE, label, p, base[col].values)
    pr["years_diff"] = years_diff(TE, label, "bar", p, base[col].values)
    pr["coverage"] = cov
    TE[["symbol", "bar", label] + FUT_ALL].assign(new=p.values, base=base[col].values).to_csv(OUT / f"{name}_test_predictions.csv", index=False)
    sim = S23.sim4h if name == "R6" else S24.sim1h
    summ = S23.summarize4h if name == "R6" else S24.summarize1h
    new_port = summ(sim(TE[["symbol", "bar"]].assign(score=p.values), h, px, 0.0025))
    base_port = json.loads((mod.OUT / "claims.json").read_text())["portfolio"][col]
    return g0, pr, new_port, base_port


def run_d1():
    A, B = S2.split_sets()
    S15.ASOF = S19.ASOF
    data_k, last_k, data_n, last_n, _ = CR.load_folder(S13.UNI / "1d", S13.UNI / "1h", S19.ASOF)
    half = {s: ("A_design" if s in A else "B_confirm") for s in A | B}
    data_n = {s: data_n[s] for s in half if s in data_n}
    last_n = {s: last_n[s] for s in data_n}
    Pk, Pn, F = CR.build(data_k, last_k, data_n, last_n, S13.UNI / "1h", S13.UNI / "1h", S19.ASOF, S11.fng_table())
    Pn["half"] = Pn.symbol.map(half)
    Pn["eligible"] = Pn.liquid & (Pn.idx + 1 >= S15.MIN_HIST)
    Pk["eligible"] = Pk.liquid & (Pk.idx + 1 >= S15.MIN_HIST)
    Pk["fwd_r5"], Pk["known_r5"] = S15.add_relative(Pk, data_k, last_k, 5)
    Pn["fwd_r5"], Pn["known_r5"] = S15.add_relative(Pn, data_n, last_n, 5)
    med = Pk.dropna(subset=["fwd_r5"]).groupby("date")["fwd_r5"].median()
    for P in (Pk, Pn):
        rel = P["fwd_r5"] - P.date.map(med)
        P["label_r5"] = np.where(rel.isna(), np.nan, (rel > 0).astype(float))
    train = pd.concat([Pk, Pn[Pn.eligible & (Pn.half == "A_design")]], ignore_index=False).reset_index(drop=True)
    test = Pn[Pn.eligible & (Pn.half == "B_confirm") & (Pn.date >= S19.OOS_START)].reset_index(drop=True)
    nk = len(Pk)
    D = pd.Timedelta(days=1)
    train, test = add_fut(train, "date", D), add_fut(test, "date", D)
    pk, pn, _ = S13.wf_transfer(train, test, F + FUT_ALL, "label_r5", "known_r5", "date", False, 5, S11.KW)
    known_pred = pk[pk.index < nk]
    newp = pd.concat([train.loc[known_pred.index, ["symbol", "date"]].assign(score=known_pred.values),
                      test[["symbol", "date"]].assign(score=pn.reindex(test.index).values)], ignore_index=True)
    base = pd.read_csv(S19.OUT / "U_AI_predictions.csv", usecols=["symbol", "date", "score", "label_r5"], parse_dates=["date"])
    U = base.merge(newp.rename(columns={"score": "new"}), on=["symbol", "date"], how="left")
    feats = pd.concat([train, test])[["symbol", "date"] + FUT_ALL].drop_duplicates(["symbol", "date"])
    U = U.merge(feats, on=["symbol", "date"], how="left")
    cov = float(U.basis_now.notna().mean())
    g0 = dict(rows_identical=bool(U.new.notna().all() and len(U) == len(base)), basis_coverage_ge_50pct=bool(cov >= 0.5))
    U = U.rename(columns={"date": "bar"})
    pr = S2.paired(U, "label_r5", U.new, U.score.values)
    pr["years_diff"] = years_diff(U, "label_r5", "bar", U.new, U.score.values)
    pr["coverage"] = dict(basis_now=cov)
    U.to_csv(OUT / "D1_test_predictions.csv", index=False)
    data, last = {**data_k, **data_n}, {**last_k, **last_n}
    px1 = {s: data[s].set_index("timestamp")[["open", "low", "close"]] for s in set(U.symbol) | {"BTCUSDT"}}
    sn = S22.summary(S22.simulate(U[["symbol", "bar", "new"]].rename(columns={"bar": "date", "new": "score"}), S23.START, S23.END, px1, last, 1.0, 5, 10), S23.START, S23.END)
    sb = S22.summary(S22.simulate(U[["symbol", "bar", "score"]].rename(columns={"bar": "date"}), S23.START, S23.END, px1, last, 1.0, 5, 10), S23.START, S23.END)
    return g0, pr, sn, sb


def main():
    name = sys.argv[1]
    OUT.mkdir(parents=True, exist_ok=True)
    h_ = sha(OUT / PROTO)
    assert h_ == (OUT / "S3_PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed after registration"
    t0 = time.time()
    g0, pr, new_port, base_port = run_d1() if name == "D1" else run_intraday(name)
    g = dict(G0=all(g0.values()), G1=pr["ci_low"] > 0,
             G2=new_port["calmar"] > base_port["calmar"] and new_port["final"] > base_port["final"],
             G3=sum(v > 0 for v in pr["years_diff"].values()) >= 4)
    g = {k: bool(v) for k, v in g.items()}
    g["decision"] = ("INVALID_G0" if not g["G0"] else "PASS" if g["G1"] and g["G2"] and g["G3"] else
                     "SKILL_ADD_ONLY" if g["G1"] else "FAIL")
    claims = dict(protocol_sha256=h_, brain=name, G0_detail=g0, paired=pr, portfolio_new=new_port, portfolio_base=base_port, gates=g,
                  predictions_sha256=sha(OUT / f"{name}_test_predictions.csv"), gate_file_sha256=sha(GATE), seconds=round(time.time() - t0))
    (OUT / f"claims_{name}.json").write_text(json.dumps(claims, indent=2, default=str))
    print(json.dumps(claims, default=str))


if __name__ == "__main__":
    main()
