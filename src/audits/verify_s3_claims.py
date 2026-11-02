"""
Independent verifier for S3 (logs/research_s3_futures_features).
V1 protocol / predictions / scale-gate hashes.
V2 for 60 random test rows with a perpetual: basis_now, basis_7d, fund_24h, fund_7d re-derived with plain loops from
   the raw perp / spot / funding files (only data with time <= the row's bar end); xr ranks re-derived for 5 bars.
V3 AUCs (plain Mann-Whitney), the per-year differences and the gates re-derived.
Usage: python verify_s3_claims.py R6|R24|D1
"""
import sys
import json
import math
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parent.parent
for p in (SRC, SRC / "pipeline_1d", SRC / "analytics", SRC / "execution", SRC / "research", SRC / "audits"):
    sys.path.insert(0, str(p))
import s3_futures_features as Q
from verify_s2_claims import mw


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def close(a, b, tol=1e-9):
    return (math.isnan(a) and math.isnan(b)) or abs(a - b) <= tol * max(1.0, abs(b))


_RAW = {}


def raw(sym, gate):
    if sym not in _RAW:
        scale = float(gate.at[sym, "scale"]) if sym in gate.index and gate.at[sym, "status"] == "ok" else None
        if scale is None or not (Q.FUM / f"{sym}_perp_1h.csv.gz").exists():
            _RAW[sym] = None
        else:
            pp = pd.read_csv(Q.FUM / f"{sym}_perp_1h.csv.gz", usecols=["timestamp", "close"], parse_dates=["timestamp"])
            sp = pd.read_csv(Q.S24.UNI1H / f"{sym}_1h_full.csv.gz", usecols=["timestamp", "close"], parse_dates=["timestamp"])
            sp["timestamp"] = sp.timestamp.dt.floor("h")
            sp = sp.groupby("timestamp").close.last()
            ff = Q.FUM / f"{sym}_funding.csv"
            fr = pd.read_csv(ff, parse_dates=["time"]) if ff.exists() else None
            _RAW[sym] = (dict(zip(pp.timestamp, pp.close / scale)), dict(zip(sp.index, sp.values)), fr)
    return _RAW[sym]


def plain_feats(sym, t_end, gate):
    """basis_now, basis_7d, fund_24h, fund_7d with plain loops from the raw files (data with time <= t_end only)."""
    R = raw(sym, gate)
    if R is None:
        return (float("nan"),) * 4
    perp, spot, fr = R
    h0 = t_end - pd.Timedelta(hours=1)                                     # the hour bar ending at t_end
    b_now = perp[h0] / spot[h0] - 1 if h0 in perp and h0 in spot else float("nan")
    vals = []
    for k in range(168):
        hk = h0 - pd.Timedelta(hours=k)
        if hk in perp and hk in spot:
            vals.append(perp[hk] / spot[hk] - 1)
    b7 = sum(vals) / len(vals) if len(vals) >= 48 else float("nan")
    if fr is None or not (fr.time <= t_end).any():
        return b_now, b7, float("nan"), float("nan")
    f24 = sum(x.funding_rate for x in fr.itertuples() if t_end - pd.Timedelta(hours=24) < x.time <= t_end)
    f7 = sum(x.funding_rate for x in fr.itertuples() if t_end - pd.Timedelta(days=7) < x.time <= t_end)
    return b_now, b7, f24, f7


def pct_rank(vals):
    """pandas rank(pct=True) re-written: average rank of ties / number of non-NaN values; NaN stays NaN."""
    ok = [v for v in vals if not math.isnan(v)]
    out = []
    for v in vals:
        if math.isnan(v):
            out.append(float("nan"))
        else:
            out.append((sum(1 for w in ok if w < v) + (sum(1 for w in ok if w == v) + 1) / 2) / len(ok))
    return out


def d1_panels():
    """D1 only: the daily panels the S3 code ranks within (train = known coins + design-half coins, test = confirm-half
    coins). Membership is a fact of the research pipeline, so it is taken from the same loaders; features are not."""
    S2, CR, S13, S15, S19, S11 = Q.S2, Q.CR, Q.S13, Q.S15, Q.S19, Q.S11
    A, B = S2.split_sets()
    S15.ASOF = S19.ASOF
    data_k, last_k, data_n, last_n, _ = CR.load_folder(S13.UNI / "1d", S13.UNI / "1h", S19.ASOF)
    half = {s: ("A_design" if s in A else "B_confirm") for s in A | B}
    data_n = {s: data_n[s] for s in half if s in data_n}
    last_n = {s: last_n[s] for s in data_n}
    Pk, Pn, _ = CR.build(data_k, last_k, data_n, last_n, S13.UNI / "1h", S13.UNI / "1h", S19.ASOF, S11.fng_table())
    Pn["half"] = Pn.symbol.map(half)
    Pn["eligible"] = Pn.liquid & (Pn.idx + 1 >= S15.MIN_HIST)
    train = pd.concat([Pk, Pn[Pn.eligible & (Pn.half == "A_design")]])[["symbol", "date"]]
    test = Pn[Pn.eligible & (Pn.half == "B_confirm") & (Pn.date >= S19.OOS_START)][["symbol", "date"]]
    return train, test, B


def main(name):
    C = json.loads((Q.OUT / f"claims_{name}.json").read_text())
    assert sha(Q.OUT / Q.PROTO) == (Q.OUT / "S3_PROTOCOL_SHA256.txt").read_text().split()[0] == C["protocol_sha256"]
    f = Q.OUT / f"{name}_test_predictions.csv"
    assert sha(f) == C["predictions_sha256"] and sha(Q.GATE) == C["gate_file_sha256"]
    print(f"[V1 PASS] {name}: hashes")
    d = pd.read_csv(f, parse_dates=["bar"])
    bl = {"R6": pd.Timedelta(hours=4), "R24": pd.Timedelta(hours=1), "D1": pd.Timedelta(days=1)}[name]
    gate = pd.read_csv(Q.GATE).set_index("symbol")
    smp = d[d.basis_now.notna()].sample(60, random_state=13)
    for r in smp.itertuples():
        b_now, b7, f24, f7 = plain_feats(r.symbol, r.bar + bl, gate)
        assert close(b_now, r.basis_now) and close(b7, r.basis_7d, 1e-7), (r.symbol, r.bar, b_now, r.basis_now, b7, r.basis_7d)
        assert close(f24, r.fund_24h, 1e-7) and close(f7, r.fund_7d, 1e-7), (r.symbol, r.bar, f24, r.fund_24h, f7, r.fund_7d)
    if name != "D1":
        for t in d.bar.drop_duplicates().sample(5, random_state=2):
            g = d[d.bar == t]
            assert np.allclose(g.basis_now.rank(pct=True).values, g.xr_basis_now.values, equal_nan=True)
        xr_note = "xr ranks for 5 bars"
    else:
        train, test, B = d1_panels()
        nchk = 0
        for t in d.bar.drop_duplicates().sample(3, random_state=2):
            for panel, sel in ((test, d.symbol.isin(B)), (train, ~d.symbol.isin(B))):
                g = d[(d.bar == t) & sel]
                if g.empty:
                    continue
                mem = sorted(panel[panel.date == t].symbol)
                assert set(g.symbol) <= set(mem), (t, set(g.symbol) - set(mem))
                fe = {s_: plain_feats(s_, t + bl, gate) for s_ in mem}
                rb = dict(zip(mem, pct_rank([fe[s_][0] for s_ in mem])))
                rf = dict(zip(mem, pct_rank([fe[s_][2] for s_ in mem])))
                for r in g.itertuples():
                    assert close(rb[r.symbol], r.xr_basis_now, 1e-7) and close(rf[r.symbol], r.xr_fund_24h, 1e-7), (t, r.symbol)
                    nchk += 1
        xr_note = f"xr ranks for {nchk} rows on 3 days, re-ranked inside the rebuilt daily panels with plain loops"
    print(f"[V2 PASS] 60 rows: basis / funding features re-derived from raw files with plain loops; {xr_note}")
    lab = {"R6": "label6", "R24": "label24", "D1": "label_r5"}[name]
    basec = "score" if name == "D1" else "base"
    m = d[lab].notna() & d.new.notna()
    a_new, a_base = mw(d[lab][m].astype(int).values, d.new[m].values), mw(d[lab][m].astype(int).values, d[basec][m].values)
    assert abs(a_new - C["paired"]["auc_new"]) < 1e-9 and abs(a_base - C["paired"]["auc_base"]) < 1e-9
    yd = {}
    for y in range(2021, 2027):
        my = m & (d.bar.dt.year == y)
        yy = d[lab][my].astype(int).values
        yd[y] = mw(yy, d.new[my].values) - mw(yy, d[basec][my].values)
        assert abs(yd[y] - C["paired"]["years_diff"][str(y)]) < 1e-9
    pn, pb = C["portfolio_new"], C["portfolio_base"]
    g = dict(G1=C["paired"]["ci_low"] > 0, G2=pn["calmar"] > pb["calmar"] and pn["final"] > pb["final"], G3=sum(v > 0 for v in yd.values()) >= 4)
    assert all(C["gates"][k] == v for k, v in g.items())
    print(f"[V3 PASS] {name}: AUC new {a_new:.4f} base {a_base:.4f} (diff {a_new-a_base:+.4f}); years {[round(v,4) for v in yd.values()]}; "
          f"final {pn['final']} vs {pb['final']}; Calmar {pn['calmar']} vs {pb['calmar']}; decision {C['gates']['decision']}")


if __name__ == "__main__":
    main(sys.argv[1])
