"""ECO E-1 (regenerate the N1 FINAL curve with the locked N1/N3/N6 code, reproduce the N6 claims) and E-2 (combination of
S_1D = F7 RS M_AI3 and S_N1 = N1 FINAL; candidates ECO-W1, ECO-W2). Protocol logs/eco/ECO_PROTOCOL_PREREGISTERED.md §5,
accounting per logs/eco/CODE_NOTES.md note 1. Historical only; no orders."""
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import n6_safety_sizing as S6          # installs the N6 overlay hook (cap) on N.apply_overlays

N, X = S6.N, S6.X
ROOT = N.ROOT
LOCK = ROOT / "logs" / "eco"
OUT = Path(os.environ.get("ECO_OUT", LOCK))                 # scratch override for smoke runs only
DER = Path(os.environ.get("ECO_DER", ROOT / "data" / "derived" / "eco"))
E2W = {"dev": ("2021-01-01", "2025-10-01"), "P1": ("2021-01-01", "2024-01-01"), "P2": ("2024-01-01", "2025-10-01"),
       "P3": ("2025-10-01", "2026-10-01")}
N_DSR = 27
E0 = 10_000.0


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def log(*a):
    print(*a, flush=True)


def wstats(v, t0, t1):
    """daily equity Series (end of day) of one window, started from E0 -> CAGR, MTM-DD, Calmar, monthly returns."""
    yrs = (pd.Timestamp(t1) - pd.Timestamp(t0)).days / 365.25
    final = float(v.iloc[-1])
    cagr = (final / E0) ** (1 / yrs) - 1 if final > 0 else -1.0
    run = np.maximum.accumulate(np.r_[E0, v.values])
    dd = float((1 - np.r_[E0, v.values] / run).max())
    me = v.groupby(v.index.to_period("M")).last()
    mret = me / me.shift(1).fillna(E0) - 1
    return dict(final=final, cagr=float(cagr), mtm_dd=dd, calmar=float(cagr / dd) if dd > 0 else np.nan,
                mean_month=float(mret.mean()), sharpe_month=float(mret.mean() / mret.std(ddof=1))), mret


def combine(r1d, rn1, wfun):
    """CODE_NOTES 1: E_d = E_{d-1} + E_m * sum_s a_s,m * r_s,d ; a and E_m fixed per calendar month."""
    E, Em, cur, out, wts = E0, E0, None, [], []
    for d in r1d.index:
        m = d.to_period("M")
        if m != cur:
            cur, Em = m, E
            a1 = wfun(d)
            wts.append((str(m), a1))
        E = E + Em * (a1 * r1d[d] + (1 - a1) * rn1[d])
        out.append(E)
    return pd.Series(out, index=r1d.index), wts


def main():
    proto = LOCK / "ECO_PROTOCOL_PREREGISTERED.md"
    OUT.mkdir(parents=True, exist_ok=True)
    assert sha(proto) == (LOCK / "ECO_PROTOCOL_SHA256.txt").read_text().split()[0], "ECO protocol changed"
    DER.mkdir(parents=True, exist_ok=True)
    # ---------------- E-1 ----------------
    x = X.setup()
    S6.HOOK["C"] = x.Wd.C
    n6 = pd.read_csv(ROOT / "logs" / "research_n6_safety_sizing" / "N6_results.csv")
    led = X.variant(x, None, True, guard=True)

    def run(t0, t1):
        S6.HOOK["cap"] = True
        try:
            return X.runv(x, led, t0, t1, want=True)
        finally:
            S6.HOOK["cap"] = False
    e1, curves = [], {}
    for wn, (t0, t1) in N.WIN.items():
        r = run(t0, t1)
        h0, h1 = x.Wd.grid.get_loc(pd.Timestamp(t0)), x.Wd.grid.get_loc(pd.Timestamp(t1))
        pd.Series(r["curve"], index=x.Wd.grid[h0:h1]).to_frame("equity").to_parquet(DER / f"n1_final_hourly_N6win_{wn}.parquet")
        ref = n6[(n6.trial == "T19") & (n6.variant == "S2") & (n6.window == wn)].iloc[0]
        e1.append(dict(window=wn, calmar=r["calmar"], ref_calmar=ref.calmar, cagr=r["cagr"], ref_cagr=ref.cagr,
                       mtm_dd=r["mtm_dd"], ref_dd=ref.mtm_dd, ok=bool(abs(r["calmar"] - ref.calmar) < 1e-9 and abs(r["mtm_dd"] - ref.mtm_dd) < 1e-12)))
        log("E-1", wn, round(r["calmar"], 6), "ref", round(ref.calmar, 6), e1[-1]["ok"])
    E1 = pd.DataFrame(e1)
    E1.to_csv(OUT / "E1_reproduction.csv", index=False)
    e1_pass = bool(E1.ok.all())
    for wn, (t0, t1) in E2W.items():
        r = run(t0, t1)
        h0, h1 = x.Wd.grid.get_loc(pd.Timestamp(t0)), x.Wd.grid.get_loc(pd.Timestamp(t1))
        c = pd.Series(r["curve"], index=x.Wd.grid[h0:h1])
        c.to_frame("equity").to_parquet(DER / f"n1_final_hourly_{wn}.parquet")
        curves[wn] = c
        log("N1 FINAL curve", wn, len(c), round(float(c.iloc[-1]), 2))
    # ---------------- E-2 ----------------
    rs = pd.read_csv(ROOT / "logs" / "strategy_f7_risk" / "equity_MAIN_AI_RS.csv", parse_dates=["date"]).set_index("date").M_AI3
    rows, monthly, series, weights = [], {}, {}, {}
    for wn, (t0, t1) in E2W.items():
        days = pd.date_range(t0, pd.Timestamp(t1) - pd.Timedelta(days=1), freq="D")
        c = curves[wn]
        n1d = c.groupby(c.index.normalize()).last().reindex(days)
        assert n1d.notna().all(), f"N1 daily gaps in {wn}"
        base1 = E0 if pd.Timestamp(t0) == rs.index[0] else float(rs.loc[pd.Timestamp(t0) - pd.Timedelta(days=1)])
        v1 = rs.reindex(days)
        assert v1.notna().all(), f"1D gaps in {wn}"
        r1d = v1 / pd.concat([pd.Series([base1], index=[days[0] - pd.Timedelta(days=1)]), v1]).shift(1).iloc[1:] - 1
        rn1 = n1d / pd.concat([pd.Series([E0], index=[days[0] - pd.Timedelta(days=1)]), n1d]).shift(1).iloc[1:] - 1
        r1d.index = days; rn1.index = days
        hist1 = (rs / rs.shift(1) - 1)
        rets = []
        for k in ("dev", "P3"):                      # returns per run (each run restarts at E0), then joined: no artificial boundary return
            dk_ = curves[k].groupby(curves[k].index.normalize()).last()
            rets.append(dk_ / pd.concat([pd.Series([E0], index=[dk_.index[0] - pd.Timedelta(days=1)]), dk_]).shift(1).iloc[1:] - 1)
        histN = pd.concat(rets).sort_index()         # inverse-vol look-back: daily N1 returns before the month

        def w_inv(d):
            prev1 = hist1[hist1.index < d].dropna().iloc[-126:]
            prevN = histN[histN.index < d].dropna().iloc[-126:]
            if len(prev1) < 126 or len(prevN) < 126:
                return 0.5
            a, b = 1 / prev1.std(ddof=1), 1 / prevN.std(ddof=1)
            return float(np.clip(a / (a + b), 0.2, 0.8))      # two weights: clipping a_1D to [0.2, 0.8] keeps a_N1 = 1 - a_1D in it
        cands = {"ECO-W1": lambda d: 0.5, "ECO-W2": w_inv, "N1_alone_combo": lambda d: 0.0, "1D_alone_combo": lambda d: 1.0}
        for name, wf in cands.items():
            v, wts = combine(r1d, rn1, wf)
            st, mret = wstats(v, t0, t1)
            rows.append(dict(window=wn, config=name, **st))
            monthly[(wn, name)] = mret; series[(wn, name)] = v; weights[(wn, name)] = wts
        st, mret = wstats(n1d, t0, t1)
        rows.append(dict(window=wn, config="N1_alone", **st)); monthly[(wn, "N1_alone")] = mret; series[(wn, "N1_alone")] = n1d
        st, mret = wstats(v1 / base1 * E0, t0, t1)
        rows.append(dict(window=wn, config="1D_alone", **st)); monthly[(wn, "1D_alone")] = mret
        if wn == "dev":
            corr_d = float(r1d.corr(rn1)); corr_m = float(monthly[("dev", "1D_alone")].corr(monthly[("dev", "N1_alone")]))
    R = pd.DataFrame(rows)
    R.to_csv(OUT / "E2_results.csv", index=False)
    pd.DataFrame({f"{w}|{c}": s for (w, c), s in series.items()}).to_parquet(DER / "e2_daily_series.parquet")
    pd.DataFrame([dict(window=w, config=c, month=m, a_1D=a) for (w, c), l in weights.items() for m, a in l if c == "ECO-W2"]).to_csv(OUT / "E2_weights_W2.csv", index=False)
    cal = {(r.window, r.config): r for r in R.itertuples()}
    srs = [monthly[("dev", c)] for c in ("ECO-W1", "ECO-W2", "N1_alone")]
    sr_var = float(np.var([s.mean() / s.std(ddof=1) for s in srs], ddof=1))
    acc, dsrs = {}, {}
    for c in ("ECO-W1", "ECO-W2"):
        p, sr, sr0 = N.dsr(monthly[("dev", c)], sr_var, N_DSR)
        dsrs[c] = dict(dsr=p, sr=sr, sr0=sr0)
        acc[c] = dict(a=bool(cal[("dev", c)].calmar >= 0.90 * cal[("dev", "N1_alone")].calmar),
                      b=bool(cal[("dev", c)].mtm_dd <= cal[("dev", "N1_alone")].mtm_dd),
                      c=bool(cal[("P1", c)].calmar > 0 and cal[("P2", c)].calmar > 0),
                      d=bool(p >= 0.95))
    ok = [c for c in acc if all(acc[c].values())]
    choice = max(ok, key=lambda c: cal[("dev", c)].calmar) if ok else None
    K = max(0.30, 1.25 * cal[("dev", choice)].mtm_dd) if choice else max(0.30, 1.25 * cal[("dev", "N1_alone")].mtm_dd)
    years = {}
    for c in ("ECO-W1", "ECO-W2", "N1_alone"):
        v = series[("dev", c)]                       # calendar years inside dev only (2025 = Jan-Sep); P3 is reported as its own window
        years[c] = {str(y): float(g.iloc[-1] / (v[v.index.year < y].iloc[-1] if (v.index.year < y).any() else E0) - 1) for y, g in v.groupby(v.index.year)}
    claims = dict(protocol_sha=sha(proto), notes_sha=sha(LOCK / "CODE_NOTES.md"), code_sha=sha(__file__),
                  e1_pass=e1_pass, e1=E1.to_dict("records"),
                  results={f"{w}|{c}": dict(calmar=r.calmar, cagr=r.cagr, mtm_dd=r.mtm_dd) for (w, c), r in cal.items()},
                  acceptance=acc, dsr=dsrs, sr_var=sr_var, n_dsr=N_DSR, choice=choice,
                  a_1D=(0.5 if choice == "ECO-W1" else "inverse-vol monthly" if choice == "ECO-W2" else 0.0), kill_K=K,
                  corr_daily_dev=corr_d, corr_monthly_dev=corr_m, years=years, years_note="calendar years of the dev run (2025 = Jan-Sep)",
                  verdict=(f"E-2: {choice} adopted" if choice else "E-2: no candidate acceptable -> a_1D = 0") if e1_pass else "E-1 FAIL: no E-2 claim",
                  files={k: sha(OUT / k) for k in ("E1_reproduction.csv", "E2_results.csv", "E2_weights_W2.csv")},
                  derived={p.name: sha(p) for p in sorted(DER.glob("*.parquet"))})
    (OUT / "claims_eco_e2.json").write_text(json.dumps(claims, indent=1, default=str))
    log(R.round(4).to_string())
    log("acceptance", acc, "dsr", {k: round(v["dsr"], 4) for k, v in dsrs.items()}, "choice", choice, "K", round(K, 4))
    log("corr daily", round(corr_d, 3), "monthly", round(corr_m, 3))
    log("years", json.dumps({c: {y: round(v, 3) for y, v in d.items()} for c, d in years.items()}))
    log(claims["verdict"])


if __name__ == "__main__":
    main()
