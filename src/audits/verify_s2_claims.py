"""
Independent verifier for S2 (logs/research_s2_bear_training).
V1 protocol + prediction hashes for every brain run.
V2 AUC new / base (plain Mann-Whitney), the 2022 AUC difference and the gates re-derived from the stored predictions.
V3 R6 only: the 2022-06 monthly model re-trained from scratch here (main train rows + pre-2020 rows, labels known
   before 2022-06-01) and its predictions for June 2022 compared with the stored ones (max |diff| < 1e-12).
Usage: python verify_s2_claims.py R6 [R24 D1]
"""
import sys
import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parent.parent
for p in (SRC, SRC / "pipeline_1d", SRC / "analytics", SRC / "execution", SRC / "research"):
    sys.path.insert(0, str(p))
import s2_bear_training as Q


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def mw(y, s):
    y, s = np.asarray(y), np.asarray(s)
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty(len(s))
    ss_ = s[order]
    i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and ss_[j + 1] == ss_[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    npos = int(y.sum())
    nneg = len(y) - npos
    return (ranks[y == 1].sum() - npos * (npos + 1) / 2) / (npos * nneg)


def check(name):
    C = json.loads((Q.OUT / f"claims_{name}.json").read_text())
    assert sha(Q.OUT / Q.PROTO) == (Q.OUT / "S2_PROTOCOL_SHA256.txt").read_text().split()[0] == C["protocol_sha256"]
    f = Q.OUT / f"{name}_test_predictions.csv"
    assert sha(f) == C["predictions_sha256"]
    d = pd.read_csv(f, parse_dates=["bar"])
    lab = {"R6": "label6", "R24": "label24", "D1": "label_r5"}[name]
    newc, basec = ("new", "base") if name != "D1" else ("new", "score")
    m = d[lab].notna() & d[newc].notna()
    y = d[lab][m].astype(int).values
    a_new, a_base = mw(y, d[newc][m].values), mw(y, d[basec][m].values)
    assert abs(a_new - C["paired"]["auc_new"]) < 1e-9 and abs(a_base - C["paired"]["auc_base"]) < 1e-9
    m22 = m & (d.bar.dt.year == 2022)
    y22 = d[lab][m22].astype(int).values
    d22 = mw(y22, d[newc][m22].values) - mw(y22, d[basec][m22].values)
    assert abs(d22 - C["paired"]["diff_2022"]) < 1e-9
    pn, pb = C["portfolio_new"], C["portfolio_base"]
    g = dict(G1=C["paired"]["ci_low"] > 0, G2=pn["calmar"] > pb["calmar"] and pn.get("ret_2022", -1e9) > pb.get("ret_2022", -1e9),
             G3=d22 > 0)
    assert all(C["gates"][k] == v for k, v in g.items())
    print(f"[V1+V2 PASS] {name}: AUC new {a_new:.4f} base {a_base:.4f} (diff {a_new - a_base:+.4f}); 2022 diff {d22:+.4f}; "
          f"Calmar {pn['calmar']} vs {pb['calmar']}; 2022 {pn.get('ret_2022')} vs {pb.get('ret_2022')}; decision {C['gates']['decision']}")
    return d


def retrain_r6_month(d):
    S23, CR, S13 = Q.S23, Q.CR, Q.S13
    A, B = Q.split_sets()
    data_k, last_k, data_n, last_n, _ = CR.load_folder(S13.UNI / "1d", S23.UNI1H, S23.END)
    data, last = {**data_k, **data_n}, {**last_k, **last_n}
    Utr = S23.daily_members(data, last, list(data_k) + sorted(A & set(data)), 30, pd.Timestamp("2020-01-01"), S23.END - pd.Timedelta(days=1))
    Ute = S23.daily_members(data, last, list(data_k) + sorted(B & set(data)), 20, S23.START - pd.Timedelta(days=1), S23.END - pd.Timedelta(days=1))
    btc = S23.bars_4h(S23.UNI1H / "BTCUSDT_1h_full.csv.gz").close
    R, _, _ = S23.build_rows(dict(train=Utr, test=Ute), S23.UNI1H, btc)
    Up = Q.pre_members(A)
    Rp, _, _ = S23.build_rows(dict(train=Up), S23.PRE1H, S23.bars_4h(S23.PRE1H / "BTCUSDT_1h_full.csv.gz").close)
    TP = Rp["train"][Rp["train"].bar < Q.PRE_CUT]
    TR = pd.concat([R["train"], TP[R["train"].columns]], ignore_index=True)
    TE = R["test"][(R["test"].bar >= S23.START) & (R["test"].bar <= S23.END_BAR)].reset_index(drop=True)
    T = pd.Timestamp("2022-06-01")
    tr = TR[(TR.known6 < T) & TR.label6.notna()]
    assert (tr.bar < T).all()
    m = S23.fit(tr[S23.FEATS].values, tr.label6.values.astype(int))
    te = TE[(TE.bar >= T) & (TE.bar < T + pd.offsets.MonthBegin(1))]
    p = m.predict_proba(te[S23.FEATS].values)[:, 1]
    stored = d.loc[te.index, "new"].values
    assert (d.loc[te.index, "symbol"].values == te.symbol.values).all()
    diff = float(np.max(np.abs(p - stored)))
    assert diff < 1e-12, diff
    print(f"[V3 PASS] R6 2022-06 model re-trained from scratch ({len(tr)} rows, of which {int((tr.bar < Q.PRE_CUT).sum())} pre-2020): "
          f"{len(te)} predictions equal (max diff {diff:.1e})")


if __name__ == "__main__":
    for name in sys.argv[1:] or ["R6"]:
        d = check(name)
        if name == "R6":
            retrain_r6_month(d)
