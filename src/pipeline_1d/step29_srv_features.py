"""
Step 29: do support/resistance + volume-at-price + swing-state features add to the 1h R24 brain?
Protocol: logs/strategy_1d_step29_srv/STEP29_PROTOCOL_PREREGISTERED.md (SHA256 locked before any Step 29 model).
Design = Step 25 (paired test on the identical rows and baseline predictions), only the added features differ.
"""
import sys
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "pipeline_1d", SRC_DIR / "analytics", SRC_DIR / "execution", SRC_DIR / "research"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import core_rows_1d as CR
import step13_unseen_coins_1d as S13
import step15_slow_relative_1d as S15
import step22_pre2020_exam_1d as S22
import step23_4h_brain as S23
import step24_1h_brain as S24
import step25_hf_features as S25
import swing_anatomy_phase1 as P
import swing_strategy_1d as E
from config import LOGS_DIR

OUT = LOGS_DIR / "strategy_1d_step29_srv"
PROTO_NAME = "STEP29_PROTOCOL_PREREGISTERED.md"
START, END, END_BAR, FINAL_T = S24.START, S24.END, S24.END_BAR, S24.FINAL_T
SRV = ["sup_dist_atr_1h", "res_dist_atr_1h", "vap_7d", "zz_state_1h", "zz_state_4h", "zz_state_1D"]
FEATS = S24.FEATS + SRV
assert len(FEATS) == 37
REF_R24 = S25.REF_R24
H = pd.Timedelta(hours=1)


def coin_srv(path, bars_needed):
    """SRV features for hour bars `bars_needed` (bar start t; everything known at t + 1h)."""
    d = pd.read_csv(path, usecols=["timestamp", "open", "high", "low", "close", "quote_volume"], parse_dates=["timestamp"])
    d = d.sort_values("timestamp")
    d["timestamp"] = d.timestamp.dt.floor("h")
    g = d.groupby("timestamp", sort=True)
    d = pd.DataFrame(dict(open=g.open.first(), high=g.high.max(), low=g.low.min(), close=g.close.last(),
                          quote_volume=g.quote_volume.sum())).reset_index()
    d["taker_buy_quote"] = 0.0                                    # not used here; P.agg expects the column
    b1, _ = P.clip_atr(d)
    sup, res = P.sr_nearest(b1)
    f = pd.DataFrame(index=pd.DatetimeIndex(b1.timestamp))
    f["sup_dist_atr_1h"] = (b1.close.values - sup) / b1.ATR_14.values
    f["res_dist_atr_1h"] = (res - b1.close.values) / b1.ATR_14.values
    f["zz_state_1h"] = E.zz(b1, 3.0)["state"]
    t_end = b1.timestamp.values + H.to_timedelta64()
    for tf, rule in (("4h", "4h"), ("1D", "1D")):
        bh, _ = P.clip_atr(P.agg(d, rule))
        st = (P.end_times(tf, bh.timestamp.values), E.zz(bh, 3.0)["state"])
        f[f"zz_state_{tf}"] = P.state_lookup(st, t_end)
    f = f.reindex(bars_needed)
    h1 = (b1.timestamp.values, b1.low.values, b1.high.values, b1.quote_volume.values)
    pos = {t: i for i, t in enumerate(b1.timestamp.values)}
    cl, atr = b1.close.values, b1.ATR_14.values
    vap = []
    for t in bars_needed.values:
        i = pos.get(t)
        vap.append(np.nan if i is None or not np.isfinite(atr[i]) else
                   P.vap_at(h1, t + H.to_timedelta64(), cl[i], 0.25 * atr[i], pd.Timedelta(days=7).to_timedelta64()))
    f["vap_7d"] = vap
    return f.replace([np.inf, -np.inf], np.nan)


def add_srv(R, folder):
    parts = []
    for s, g in R.groupby("symbol", sort=False):
        need = pd.DatetimeIndex(g.bar.unique())
        f = coin_srv(folder / f"{s}_1h_full.csv.gz", need)
        x = f.loc[g.bar.values]
        parts.append(pd.DataFrame(x.values, index=g.index, columns=SRV))
    A = pd.concat(parts).reindex(R.index)
    return pd.concat([R.drop(columns=[c for c in SRV if c in R]), A.astype("float64")], axis=1)


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
    TR = add_srv(TR, S24.UNI1H)
    TE = add_srv(TE, S24.UNI1H)
    claims["srv_missing_share_test"] = {c: float(TE[c].isna().mean()) for c in SRV}
    g0["b_missing_lt_10pct"] = all(v < 0.10 for v in claims["srv_missing_share_test"].values())
    print("SRV added", claims["srv_missing_share_test"], f"({time.time()-t0:.0f}s)", flush=True)

    p = S24.wf(TR, TE, FEATS, "label24", "known24")
    m = TE.label24.notna() & p.notna()
    claims["R24_SRV_skill"] = S23.auc_ci(TE, p, "label24")
    claims["R24_base_skill_same_rows"] = S23.auc_ci(TE, pd.Series(base.R24_AI.values, index=TE.index), "label24")
    claims["paired_auc_diff"] = S25.paired_auc_diff(TE.label24[m].values.astype(int), p[m].values, base.R24_AI.values[m.values],
                                                    TE.bar[m].dt.to_period("M").astype(str).values)
    print("skill", claims["R24_SRV_skill"], claims["R24_base_skill_same_rows"]["auc"], claims["paired_auc_diff"], f"({time.time()-t0:.0f}s)", flush=True)
    out = TE[["symbol", "bar", "label24"]].assign(R24_SRV=p.values, R24_base=base.R24_AI.values)
    out.to_csv(OUT / "test_predictions_srv.csv", index=False)

    runs = {}
    for name, cost in (("R24_SRV", 0.0025), ("R24_SRV_cost040", 0.0040)):
        res = S24.sim1h(TE[["symbol", "bar"]].assign(score=p.values), 24, px, cost)
        res["trades"].to_csv(OUT / f"{name}_trades.csv", index=False)
        runs[name] = S24.summarize1h(res)
        print(name, runs[name], flush=True)
    claims["portfolio"] = runs

    U22 = pd.read_csv(S22.OUT / "U_pre2020_predictions.csv", usecols=["symbol", "date"], parse_dates=["date"])
    btc_pre = S24.bars_1h(S24.PRE1H / "BTCUSDT_1h_full.csv.gz").close
    Rp, _, _ = S24.build_rows(dict(pre=U22), S24.PRE1H, btc_pre)
    Pp = Rp["pre"]
    Pp = Pp[(Pp.bar >= S24.PRE_START) & (Pp.bar <= S24.PRE_END + pd.Timedelta(hours=23))].reset_index(drop=True)
    pb = pd.read_csv(S24.OUT / "pre2020_predictions_1h.csv", usecols=["symbol", "bar", "R24_FROZEN"], parse_dates=["bar"])
    g0["c_pre_rows_identical"] = len(pb) == len(Pp) and (pb.symbol.values == Pp.symbol.values).all() and (pb.bar.values == Pp.bar.values).all()
    Pp = add_srv(Pp, S24.PRE1H)
    tr = TR[(TR.known24 < FINAL_T) & TR.label24.notna()]
    mf = S23.fit(tr[FEATS].values, tr.label24.values.astype(int))
    pp = pd.Series(mf.predict_proba(Pp[FEATS].values)[:, 1], index=Pp.index)
    claims["pre2020_SRV"] = S23.auc_ci(Pp, pp, "label24")
    claims["pre2020_base"] = S23.auc_ci(Pp, pd.Series(pb.R24_FROZEN.values, index=Pp.index), "label24")
    print("2018-19", claims["pre2020_SRV"], claims["pre2020_base"]["auc"], flush=True)
    Pp[["symbol", "bar", "label24"]].assign(R24_SRV_FROZEN=pp.values, R24_FROZEN=pb.R24_FROZEN.values).to_csv(OUT / "pre2020_predictions_srv.csv", index=False)

    gates = {f"G0{k[0]}_{k[2:]}": bool(v) for k, v in g0.items()}
    gates["G0"] = all(g0.values())
    r = runs["R24_SRV"]
    gates.update(G2_added_skill=claims["paired_auc_diff"]["ci_low"] > 0,
                 G3a_calmar=r["calmar"] > REF_R24[1], G3b_trade_ci=r["trade_ci_low_pct"] > 0,
                 G3c_cost040=runs["R24_SRV_cost040"]["cagr_pct"] > 0,
                 G4_pre2020=claims["pre2020_SRV"]["auc"] > claims["pre2020_base"]["auc"] and claims["pre2020_SRV"]["ci_low"] > 0.50)
    gates = {k: bool(v) for k, v in gates.items()}
    rest = all(gates[k] for k in ("G3a_calmar", "G3b_trade_ci", "G3c_cost040", "G4_pre2020"))
    gates["decision"] = ("INVALID_G0" if not gates["G0"] else "PASS_SRV_ADDS" if gates["G2_added_skill"] and rest else
                         "SKILL_ADD_ONLY" if gates["G2_added_skill"] else "FAIL_SRV_ADDS_NOTHING")
    claims["gates"] = gates
    claims["test_predictions_sha256"] = S23.sha_file(OUT / "test_predictions_srv.csv")
    (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=str))
    print("\nGATES:", json.dumps(gates), f"({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
