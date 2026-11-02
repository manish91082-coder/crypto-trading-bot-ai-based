"""NP3 (logs/research_nonprice/NP3_PROTOCOL_PREREGISTERED.md, SHA 8e4488b4...): NP2 composite signals with maker entry
(fill only on trade-through within 15 min) and taker (XT) or maker-with-fallback (XM) exit.
Usage: python src/research/nonprice_np3.py DV | H"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nonprice_np2 as N2  # noqa: E402
from nonprice_np1 import CL, FEES, OUT, cluster_t, log  # noqa: E402

MAKER = FEES["futures_usdm"]["bnb_maker"]
TAKER = FEES["rules"]["paper_futures_taker_per_side"]
HOURS = {"1h": 1, "4h": 4}


class Bars:
    def __init__(self):
        f = pd.read_parquet(CL / "fut5m.parquet").sort_values("time")
        self.t0 = f.time.iloc[0]
        assert (f.time.diff().dropna() == pd.Timedelta(minutes=5)).all()
        self.H, self.L, self.C = f.high.to_numpy(), f.low.to_numpy(), f.close.to_numpy()

    def i(self, t):
        return int((t - self.t0) / pd.Timedelta(minutes=5))


def execute(B, t, side, h, mode):
    it = B.i(t)
    P = B.C[it - 1]
    k = [j for j in range(it, it + 3) if (B.L[j] < P if side > 0 else B.H[j] > P)]
    if not k:
        return None
    ie = B.i(t + pd.Timedelta(hours=HOURS[h]))
    Q = B.C[ie - 1]
    if mode == "XT":
        x, xc = Q, TAKER
    else:
        kk = [j for j in range(ie, ie + 3) if (B.H[j] > Q if side > 0 else B.L[j] < Q)]
        x, xc = (Q, MAKER) if kk else (B.C[ie + 2], TAKER)
    g = side * (x / P - 1)
    return P, x, g * 100, (g - MAKER - xc) * 100, k[0] - it


def run(X, upto, cfgs, frozen=None):
    B = Bars()
    panels = {k: N2.panel(X, k[0], k[1], upto) for k in N2.SETS}
    rows, sigs, extras = [], [], {}
    for (h, s, kind, par) in cfgs:
        T, extra = N2.trades_for(panels[(h, s)], h, s, kind, par, (frozen or {}).get(f"{h}|{s}|{kind}|{par}"))
        extras[f"{h}|{s}|{kind}|{par}"] = extra
        for mode in ("XT", "XM"):
            cfg = f"{h}|{s}|{kind}|{par}|{mode}"
            for r in T.itertuples():
                e = execute(B, r.t, int(r.side), h, mode)
                sigs.append((cfg, r.t, r.period, int(r.side), e is not None))
                if e is not None:
                    rows.append(dict(cfg=cfg, t=r.t, period=r.period, side=int(r.side), entry=e[0], exit=e[1], gross=e[2], net=e[3], fill_bar=e[4]))
    return pd.DataFrame(rows), pd.DataFrame(sigs, columns=["cfg", "t", "period", "side", "filled"]), extras


def summ(Tr, Sg, cfg, period):
    g = Tr[(Tr.cfg == cfg) & (Tr.period == period)]
    s = Sg[(Sg.cfg == cfg) & (Sg.period == period)]
    mo = g.groupby(g.t.dt.to_period("M")).net.sum()
    return dict(cfg=cfg, period=period, signals=len(s), fills=int(s.filled.sum()), fill_rate=s.filled.mean() if len(s) else np.nan,
                trades=len(g), win=float((g.net > 0).mean()) if len(g) else np.nan, mean_gross_pct=g.gross.mean() if len(g) else np.nan,
                mean_net_pct=g.net.mean() if len(g) else np.nan, t_cluster=cluster_t(g) if len(g) > 2 else np.nan, total_pct=g.net.sum(),
                months_pos=int((mo > 0).sum()), months_traded=len(mo), worst_month_pct=float(mo.min()) if len(mo) else np.nan)


def stage_dv():
    X = pd.read_parquet(OUT / "np1_features_1h.parquet")
    X = X[X.t < N2.H0]
    log(f"NP3 DV start; nonprice_np2.py SHA {hashlib.sha256(Path(N2.__file__).read_bytes()).hexdigest()[:12]}")
    Tr, Sg, extras = run(X, N2.H0, list(N2.configs()))
    cfgs = sorted(Tr.cfg.unique().tolist() + [c for c in Sg.cfg.unique() if c not in set(Tr.cfg)])
    S = pd.DataFrame([summ(Tr, Sg, c, p) for c in cfgs for p in ("D", "V")])
    S.to_csv(OUT / "np3_dv_summary.csv", index=False)
    Tr.to_parquet(OUT / "np3_dv_trades.parquet", compression="zstd", index=False)
    d, v = S[S.period == "D"].set_index("cfg"), S[S.period == "V"].set_index("cfg")
    cand = d[(d.mean_net_pct > 0) & (d.t_cluster >= 2.0) & (v.mean_net_pct > 0)].sort_values("t_cluster", ascending=False)
    sel = cand.index[:3].tolist()
    sha = hashlib.sha256((OUT / "np3_dv_summary.csv").read_bytes()).hexdigest()
    (OUT / "np3_selection.json").write_text(json.dumps(dict(selected=sel, frozen={c: extras["|".join(c.split("|")[:4])] for c in sel},
                                                            dv_summary_sha256=sha, candidates=cand[["mean_net_pct", "t_cluster"]].round(5).reset_index().to_dict("records")),
                                                       indent=1), encoding="utf-8")
    log(f"NP3 DV: {len(cfgs)} configs; candidates {len(cand)}; selected {sel}")


def stage_h():
    sel = json.loads((OUT / "np3_selection.json").read_text(encoding="utf-8"))
    if not sel["selected"]:
        log("NP3 H: nothing selected, H stays sealed")
        return
    raise SystemExit("H stage: implement only if something is selected (protocol §H); not reached")


if __name__ == "__main__":
    {"DV": stage_dv, "H": stage_h}[sys.argv[1]]()
    outs = sorted(f for f in OUT.iterdir() if f.name.startswith("np3_") and f.suffix in (".parquet", ".csv", ".json"))
    (OUT / "NP3_OUTPUT_SHA256.txt").write_text("".join(f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.name}\n" for f in outs), encoding="utf-8")
