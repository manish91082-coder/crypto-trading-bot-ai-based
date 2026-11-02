"""ECO-T4 (amendment 1 §1): break-even profit lock on N1 A/C trades, on the N1 FINAL (K1 + X2 + X3 + S2 cap) portfolio,
plus the ECO W2 combination with the T4 N1 curve. Reuses the verified N1/N3/N6 machinery; the only change is the exit of
A/C trades: armed after a +3 ATR(TF, signal bar) favourable 1h excursion, then exit when a later 1h bar touches the entry
(fill min/max(open, entry)). Historical only."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "eco"))
import n6_safety_sizing as S6
import eco_core as EC

N, X = S6.N, S6.X
ROOT = N.ROOT
OUT = ROOT / "logs" / "eco"
DER = ROOT / "data" / "derived" / "eco"
E2W = {"dev": ("2021-01-01", "2025-10-01"), "P1": ("2021-01-01", "2024-01-01"), "P2": ("2024-01-01", "2025-10-01"),
       "P3": ("2025-10-01", "2026-10-01")}
KARM = 3.0
E0 = 10_000.0


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sim_be(T, C):
    """N.sim without stops, then the break-even exit for every trade (A/C callers only)."""
    L = N.sim(T, C, stop=False)
    E, Xp, armed, be = L.E.values.copy(), L.X.values.copy(), np.zeros(len(L), bool), np.zeros(len(L), bool)
    h1s = np.full(len(L), -1)
    for coin, idx in L.groupby("coin").indices.items():
        cd = C[coin]
        tabH = N.sparse(np.where(np.isnan(cd.H), -np.inf, cd.H), np.maximum)
        tabL = N.sparse(np.where(np.isnan(cd.L), np.inf, cd.L), np.minimum)
        for tf, jj in L.iloc[idx].groupby("tf").indices.items():
            ii = idx[jj]
            A = cd.tf[tf][5]
            e = L.e.values[ii].astype(int)
            a, b = L.a.values[ii].astype(np.int64), L.E.values[ii].astype(np.int64)
            en, s = L.entry.values[ii], L.side.values[ii]
            dist = KARM * A[e - 1]
            for side in (1, -1):
                q = np.flatnonzero(s == side)
                if not len(q):
                    continue
                thr = en[q] + side * dist[q]
                p1 = N.first_hit(tabH if side == 1 else tabL, a[q], b[q], thr, side != 1)     # arming
                arm = p1 < b[q]
                qa = q[arm]
                if not len(qa):
                    continue
                start = np.minimum(p1[arm] + 1, b[qa])
                p2 = N.first_hit(tabL if side == 1 else tabH, start, b[qa], en[qa], side == 1)  # touch entry
                hit = p2 < b[qa]
                qh = qa[hit]
                g = ii[qh]
                armed[ii[qa]] = True; h1s[ii[qa]] = p1[arm]
                be[g] = True
                E[g] = p2[hit]
                Xp[g] = np.minimum(cd.O[p2[hit]], en[qh]) if side == 1 else np.maximum(cd.O[p2[hit]], en[qh])
    L["E"], L["X"], L["armed"], L["be_exit"], L["h_arm"] = E, Xp, armed, be, h1s
    for coin, idx in L.groupby("coin").indices.items():
        cd = C[coin]
        a, Ee, s = L.a.values[idx].astype(np.int64), L.E.values[idx].astype(np.int64), L.side.values[idx]
        L.loc[L.index[idx], "fsum"] = s * (cd.cumrate[Ee + 1] - cd.cumrate[a + 1])
    L["gross"] = L.side * (L.X - L.entry) / L.entry
    L["stopped"] = L.be_exit
    return L


def main():
    for f, s_ in (("ECO_PROTOCOL_PREREGISTERED.md", "ECO_PROTOCOL_SHA256.txt"), ("ECO_AMENDMENT_1_PREREGISTERED.md", "ECO_AMENDMENT_1_SHA256.txt")):
        assert sha(OUT / f) == (OUT / s_).read_text().split()[0], f"{f} changed"
    x = X.setup()
    S6.HOOK["C"] = x.Wd.C
    allL0 = x.allL
    Wd = x.Wd
    parts = []
    for s in "ABC":
        parts.append(sim_be(Wd.T[s], Wd.C) if s in "AC" else N.sim(Wd.T[s], Wd.C, stop=False).assign(armed=False, be_exit=False, h_arm=-1))
    allBE = pd.concat(parts, ignore_index=True)
    keys = ["sleeve", "coin", "tf", "fam", "side", "entry_time"]
    assert (allBE[keys].values == allL0[keys].values).all(), "trade order differs from the N1 ledger"
    unchanged = ~allBE.be_exit.values
    assert np.allclose(allBE.X.values[unchanged], allL0.X.values[unchanged]) and (allBE.E.values[unchanged] == allL0.E.values[unchanged]).all(), \
        "non-break-even trades must equal the base ledger"
    ac = allBE.sleeve.isin(["A", "C"])
    rep = dict(n_ac=int(ac.sum()), armed_share=float(allBE.armed[ac].mean()), be_share=float(allBE.be_exit[ac].mean()),
               per_sleeve={s: dict(armed=float(allBE.armed[allBE.sleeve == s].mean()), be=float(allBE.be_exit[allBE.sleeve == s].mean())) for s in "AC"})
    print("T4 trades", rep, flush=True)
    allBE[keys + ["e", "a", "E", "entry", "X", "armed", "be_exit", "h_arm"]][ac].to_parquet(DER / "t4_trades_AC.parquet")

    def run(L, t0, t1):
        x.allL = L
        S6.HOOK["cap"] = True
        try:
            return X.runv(x, X.variant(x, None, True, guard=True), t0, t1, want=True)
        finally:
            x.allL = allL0; S6.HOOK["cap"] = False
    rows, mon, curves = [], {}, {}
    for wn, (t0, t1) in N.WIN.items():
        for name, L in (("base", allL0), ("T4", allBE)):
            r = run(L, t0, t1)
            rows.append(dict(window=wn, config=name, calmar=r["calmar"], cagr=r["cagr"], mtm_dd=r["mtm_dd"], n_trades=r["n_trades"]))
            mon[(wn, name)] = r["monthly"]
            print(wn, name, round(r["calmar"], 4), flush=True)
    for wn, (t0, t1) in E2W.items():
        r = run(allBE, t0, t1)
        h0, h1 = Wd.grid.get_loc(pd.Timestamp(t0)), Wd.grid.get_loc(pd.Timestamp(t1))
        c = pd.Series(r["curve"], index=Wd.grid[h0:h1])
        c.to_frame("equity").to_parquet(DER / f"t4_n1_hourly_{wn}.parquet")
        curves[wn] = c
    R = pd.DataFrame(rows)
    cal = {(r.window, r.config): r.calmar for r in R.itertuples()}
    base_ref = {"dev": 4.160747, "P1": 5.096377, "P2": 3.220073}
    assert all(abs(cal[(w, "base")] - v) < 5e-7 for w, v in base_ref.items()), "base does not reproduce E-1"
    srs = [mon[("dev", c)] for c in ("base", "T4")]
    sr_var = float(np.var([s.mean() / s.std(ddof=1) for s in srs], ddof=1))
    p, sr, sr0 = N.dsr(mon[("dev", "T4")], sr_var, 28)
    # ECO W2 combination with the T4 N1 curve (E-2 accounting, CODE_NOTES 1)
    rs = pd.read_csv(ROOT / "logs" / "strategy_f7_risk" / "equity_MAIN_AI_RS.csv", parse_dates=["date"]).set_index("date").M_AI3
    r1_all = (rs / rs.shift(1) - 1).dropna()
    rets = []
    for k in ("dev", "P3"):
        d = curves[k].groupby(curves[k].index.normalize()).last()
        rets.append(d / np.r_[E0, d.values[:-1]] - 1)
    rn_all = pd.concat(rets).sort_index()
    comb = {}
    for wn, (t0, t1) in E2W.items():
        days = pd.date_range(t0, pd.Timestamp(t1) - pd.Timedelta(days=1))
        n1 = curves[wn].groupby(curves[wn].index.normalize()).last().reindex(days)
        rn = n1 / np.r_[E0, n1.values[:-1]] - 1
        base1 = E0 if days[0] == rs.index[0] else float(rs.loc[days[0] - pd.Timedelta(days=1)])
        v1 = rs.reindex(days)
        r1 = v1 / np.r_[base1, v1.values[:-1]] - 1
        E, Em, cm, vals = E0, E0, None, []
        for d in days:
            if d.to_period("M") != cm:
                cm, Em = d.to_period("M"), E
                a1 = EC.inv_vol_weight(r1_all, rn_all, d)
            E += Em * (a1 * r1[d] + (1 - a1) * rn[d])
            vals.append(E)
        v = pd.Series(vals, index=days)
        yrs = (pd.Timestamp(t1) - pd.Timestamp(t0)).days / 365.25
        xx = np.r_[E0, v.values]
        dd = float((1 - xx / np.maximum.accumulate(xx)).max())
        cg = (v.iloc[-1] / E0) ** (1 / yrs) - 1
        comb[wn] = dict(calmar=float(cg / dd), cagr=float(cg), mtm_dd=dd)
    e2 = json.loads((OUT / "claims_eco_e2.json").read_text())
    comb_ref = e2["results"]["dev|ECO-W2"]["calmar"]
    acc = dict(a=bool(all(cal[(w, "T4")] > cal[(w, "base")] for w in ("dev", "P1", "P2"))), b=bool(p >= 0.95),
               c=bool(comb["dev"]["calmar"] >= comb_ref))
    verdict = "ECO-T4 ADOPTED" if all(acc.values()) else "ECO-T4 FAIL: not adopted"
    R.to_csv(OUT / "T4_results.csv", index=False)
    claims = dict(amendment_sha=sha(OUT / "ECO_AMENDMENT_1_PREREGISTERED.md"), protocol_sha=sha(OUT / "ECO_PROTOCOL_PREREGISTERED.md"),
                  code_sha=sha(__file__), trades=rep, results={f"{w}|{c}": v for (w, c), v in cal.items()}, dsr=dict(p=p, sr=sr, sr0=sr0, n=28, sr_var=sr_var),
                  combined_T4=comb, combined_ref_dev=comb_ref, acceptance=acc, verdict=verdict,
                  files={k: sha(OUT / k) for k in ("T4_results.csv",)}, derived={q.name: sha(q) for q in sorted(DER.glob("t4_*.parquet"))})
    (OUT / "claims_eco_t4.json").write_text(json.dumps(claims, indent=1, default=str))
    print(R.round(4).to_string())
    print("combined with T4", {k: round(v["calmar"], 4) for k, v in comb.items()}, "ref dev", round(comb_ref, 4))
    print("dsr", round(p, 4), "acceptance", acc, verdict)


if __name__ == "__main__":
    main()
