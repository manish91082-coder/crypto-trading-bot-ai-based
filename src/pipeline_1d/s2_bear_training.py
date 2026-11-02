"""
S2: add the 2017-19 bear-market rows to the TRAINING set of R6 / R24 / D1; paired test vs the stored research
predictions on identical test rows. Protocol: logs/research_s2_bear_training/S2_PROTOCOL_PREREGISTERED.md
Usage: python s2_bear_training.py R6|R24|D1
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
import step25_hf_features as S25
from config import LOGS_DIR

OUT = LOGS_DIR / "research_s2_bear_training"
PROTO = "S2_PROTOCOL_PREREGISTERED.md"
PRE_CUT = pd.Timestamp("2020-01-01")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def split_sets():
    split = pd.read_csv(S15.SPLIT)
    assert sha(S15.SPLIT) == "a16333402ed7d7137cf8ebc667b1cdc66e35e614d3369da065062fe7c960d2d0"
    return set(split[split.half == "A_design"].symbol), set(split[split.half == "B_confirm"].symbol)


def pre_members(A):
    dk, lk, dn, ln, _ = S22.load_pre(S22.PRE / "1d", S22.PRE / "1h", S22.ASOF_PRE)
    data, last = {**dk, **dn}, {**lk, **ln}
    cand = list(dk) + sorted(A & set(data))
    return S23.daily_members(data, last, cand, 30, pd.Timestamp("2017-08-01"), PRE_CUT - pd.Timedelta(days=2))


def paired(TE, label, p_new, p_old):
    m = TE[label].notna() & p_new.notna()
    y = TE[label][m].values.astype(int)
    d = S25.paired_auc_diff(y, p_new[m].values, p_old[m.values], TE.bar[m].dt.to_period("M").astype(str).values)
    y22 = (TE.bar.dt.year == 2022) & m
    d["diff_2022"] = float(roc_auc_score(TE[label][y22].astype(int), p_new[y22]) - roc_auc_score(TE[label][y22].astype(int), p_old[y22.values]))
    d["auc_new"], d["auc_base"] = float(roc_auc_score(y, p_new[m].values)), float(roc_auc_score(y, p_old[m.values]))
    return d


def run_intraday(name):
    mod, h, hours = (S23, 6, None) if name == "R6" else (S24, 24, lambda hr: hr % 3 == 0)
    base_file = S23.OUT / "test_predictions_4h.csv" if name == "R6" else S24.OUT / "test_predictions_1h.csv"
    col, label, known = f"{name}_AI", f"label{h}", f"known{h}"
    A, B = split_sets()
    data_k, last_k, data_n, last_n, _ = CR.load_folder(S13.UNI / "1d", S23.UNI1H, S23.END)
    data, last = {**data_k, **data_n}, {**last_k, **last_n}
    known_c = list(data_k)
    Ute = S23.daily_members(data, last, known_c + sorted(B & set(data)), 20, S23.START - pd.Timedelta(days=1), S23.END - pd.Timedelta(days=1))
    Utr = S23.daily_members(data, last, known_c + sorted(A & set(data)), 30, pd.Timestamp("2020-01-01"), S23.END - pd.Timedelta(days=1))
    del data_k, data_n, data
    bars = S23.bars_4h if name == "R6" else S24.bars_1h
    btc = bars(S23.UNI1H / "BTCUSDT_1h_full.csv.gz").close
    hf = dict(train=hours) if hours else None
    R, px, _ = mod.build_rows(dict(train=Utr, test=Ute), S23.UNI1H, btc, hour_filter=hf) if name == "R24" else mod.build_rows(dict(train=Utr, test=Ute), S23.UNI1H, btc)
    TR, TE = R["train"], R["test"]
    end_bar = S23.END_BAR if name == "R6" else S24.END_BAR
    TE = TE[(TE.bar >= S23.START) & (TE.bar <= end_bar)].reset_index(drop=True)
    base = pd.read_csv(base_file, usecols=["symbol", "bar", col], parse_dates=["bar"])
    g0 = dict(rows_identical=bool(len(base) == len(TE) and (base.symbol.values == TE.symbol.values).all() and (base.bar.values == TE.bar.values).all()))
    Up = pre_members(A)
    btc_pre = bars(S23.PRE1H / "BTCUSDT_1h_full.csv.gz").close
    Rp, _, _ = mod.build_rows(dict(train=Up), S23.PRE1H, btc_pre, hour_filter=hf) if name == "R24" else mod.build_rows(dict(train=Up), S23.PRE1H, btc_pre)
    TP = Rp["train"]
    TP = TP[TP.bar < PRE_CUT]
    g0["pre_rows"] = int(len(TP))
    g0["pre_rows_before_2020"] = bool(len(TP) > 0 and (TP.bar < PRE_CUT).all() and (TP[known].dropna() <= PRE_CUT).all())
    TRall = pd.concat([TR, TP[TR.columns]], ignore_index=True)
    print(name, "rows: train", len(TR), "+ pre", len(TP), "test", len(TE), g0, flush=True)
    p = mod.wf(TRall, TE, mod.FEATS, label, known)
    pr = paired(TE, label, p, base[col].values)
    out = TE[["symbol", "bar", label]].assign(new=p.values, base=base[col].values)
    out.to_csv(OUT / f"{name}_test_predictions.csv", index=False)
    sim = S23.sim4h if name == "R6" else S24.sim1h
    summ = S23.summarize4h if name == "R6" else S24.summarize1h
    res = sim(TE[["symbol", "bar"]].assign(score=p.values), h, px, 0.0025)
    new_port = summ(res)
    base_port = json.loads((mod.OUT / "claims.json").read_text())["portfolio"][col]
    return g0, pr, new_port, base_port


def run_d1():
    A, B = split_sets()
    t0 = time.time()
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
    print(f"main rows: train {len(train)} (reference {nk}), test {len(test)} ({time.time()-t0:.0f}s)", flush=True)
    # ---- pre-2020 rows (Step 22 construction) ----
    dk, lk, dn, ln, _ = S22.load_pre(S22.PRE / "1d", S22.PRE / "1h", S22.ASOF_PRE)
    Qk, Qn, F2 = CR.build(dk, lk, dn, ln, S22.PRE / "1h", S22.PRE / "1h", S22.ASOF_PRE, S11.fng_table())
    assert F2 == F
    S15.ASOF = S22.ASOF_PRE
    for Q, d_, l_ in ((Qk, dk, lk), (Qn, dn, ln)):
        Q["eligible"] = Q.liquid & (Q.idx + 1 >= S15.MIN_HIST)
        Q["fwd_r5"], Q["known_r5"] = S15.add_relative(Q, d_, l_, 5)
    medp = Qk.dropna(subset=["fwd_r5"]).groupby("date")["fwd_r5"].median()
    for Q in (Qk, Qn):
        rel = Q["fwd_r5"] - Q.date.map(medp)
        Q["label_r5"] = np.where(rel.isna(), np.nan, (rel > 0).astype(float))
    pre = pd.concat([Qk, Qn[Qn.eligible & Qn.symbol.isin(A)]], ignore_index=True)
    pre = pre[pre.date < PRE_CUT]
    # restore the module state that CR.build changed for the pre-2020 folders
    S15.ASOF = S19.ASOF
    for m in (CR.S7, CR.S8, S13):
        m.DATA_END = pd.Timestamp(S19.ASOF)
    g0 = dict(pre_rows=int(len(pre)), pre_rows_before_2020=bool(len(pre) > 0 and (pre.date < PRE_CUT).all() and (pre.known_r5.dropna() <= PRE_CUT).all()))
    train_all = pd.concat([train, pre.reindex(columns=train.columns)], ignore_index=True)   # reference rows stay at index < nk; "half" is NaN for pre rows
    pk, pn, _ = S13.wf_transfer(train_all, test, F, "label_r5", "known_r5", "date", False, 5, S11.KW)
    known_pred = pk[pk.index < nk]
    rows_k = train_all.loc[known_pred.index, ["symbol", "date"]].assign(score=known_pred.values)
    rows_b = test[["symbol", "date"]].assign(score=pn.reindex(test.index).values)
    newp = pd.concat([rows_k, rows_b], ignore_index=True)
    base = pd.read_csv(S19.OUT / "U_AI_predictions.csv", usecols=["symbol", "date", "score", "label_r5"], parse_dates=["date"])
    U = base.merge(newp.rename(columns={"score": "new"}), on=["symbol", "date"], how="left")
    g0["rows_identical"] = bool(U.new.notna().all() and len(U) == len(base))
    U = U.rename(columns={"date": "bar"})
    pr = paired(U, "label_r5", U.new, U.score.values)
    U.to_csv(OUT / "D1_test_predictions.csv", index=False)
    start, end = S23.START, S23.END
    data, last = {**data_k, **data_n}, {**last_k, **last_n}
    px1 = {s: data[s].set_index("timestamp")[["open", "low", "close"]] for s in set(U.symbol) | {"BTCUSDT"}}
    sn = S22.summary(S22.simulate(U[["symbol", "bar", "new"]].rename(columns={"bar": "date", "new": "score"}), start, end, px1, last, 1.0, 5, 10), start, end)
    sb = S22.summary(S22.simulate(U[["symbol", "bar", "score"]].rename(columns={"bar": "date"}), start, end, px1, last, 1.0, 5, 10), start, end)
    return g0, pr, sn, sb


def main():
    name = sys.argv[1]
    OUT.mkdir(parents=True, exist_ok=True)
    h_ = sha(OUT / PROTO)
    assert h_ == (OUT / "S2_PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed after registration"
    t0 = time.time()
    g0, pr, new_port, base_port = run_d1() if name == "D1" else run_intraday(name)
    g = dict(G0=all(v for k, v in g0.items() if isinstance(v, bool)) and g0["pre_rows"] > 0,
             G1=pr["ci_low"] > 0,
             G2=new_port["calmar"] > base_port["calmar"] and new_port.get("ret_2022", -1e9) > base_port.get("ret_2022", -1e9),
             G3=pr["diff_2022"] > 0)
    g = {k: bool(v) for k, v in g.items()}
    g["decision"] = ("INVALID_G0" if not g["G0"] else "PASS" if g["G1"] and g["G2"] and g["G3"] else
                     "SKILL_ADD_ONLY" if g["G1"] else "FAIL")
    claims = dict(protocol_sha256=h_, brain=name, G0_detail=g0, paired=pr, portfolio_new=new_port, portfolio_base=base_port, gates=g,
                  predictions_sha256=sha(OUT / f"{name}_test_predictions.csv"), seconds=round(time.time() - t0))
    (OUT / f"claims_{name}.json").write_text(json.dumps(claims, indent=2, default=str))
    print(json.dumps(claims, default=str))


if __name__ == "__main__":
    main()
