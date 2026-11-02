"""N6: T19 safety (S1 catastrophe stop 35%, S2 per-coin entry cap 0.20, S3 both) and T20 AI sizing (N5 model E) on the N3 FINAL
portfolio. Protocol logs/research_n6_safety_sizing/N6_PROTOCOL_PREREGISTERED.md. Reuses the verified N1/N3 simulator; the only hooks
are (i) the stop distance (pct of entry instead of ATR), (ii) a weight wrapper for the cap and the AI multiplier. Historical only."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import n1_portfolio as N
import n3_execution as X

OUT = N.ROOT / "logs" / "research_n6_safety_sizing"
PCT, CAP, SEED, NR = 0.35, 0.20, 20261028, 100
HOOK = {"cap": False, "m": None, "C": None}
LOG = []
_prev = N.apply_overlays


def log(*a):
    s = " ".join(str(x) for x in a); LOG.append(s); print(s, flush=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def key_of(L):
    return list(zip(L.sleeve.values, L.coin.values, L.tf.values, L.fam.values.astype(int), L.side.values.astype(int),
                    pd.DatetimeIndex(L.entry_time).values.astype("datetime64[ns]").astype(np.int64)))


def cap_weights(L, w, C):
    """S2: sequential per-coin entry cap on |net notional| / E_m <= CAP (D legs count but are never scaled)."""
    w = w.copy()
    abc = L.sleeve.isin(["A", "B", "C"]).values
    so = L.sleeve.map({"D": -1, "A": 0, "B": 1, "C": 2}).values
    tfi = L.tf.map(N.TFI).values
    for coin, idx in L.groupby("coin").indices.items():
        sub = pd.DataFrame(dict(i=idx, a=L.a.values[idx], so=so[idx], tfi=tfi[idx], fam=L.fam.values[idx]))
        order = sub.sort_values(["a", "so", "tfi", "fam"], kind="mergesort").i.values
        Cf = C[coin].Cf
        act = []                                   # (E, side*w/entry)
        for i in order:
            a = L.a.values[i]
            act = [(E, u) for E, u in act if E > a]
            s = L.side.values[i]
            if abc[i] and w[i] > 0:
                net = sum(u for _, u in act) * Cf[a]
                bound = CAP - net if s == 1 else CAP + net
                w[i] = float(np.clip(min(w[i], bound), 0.0, w[i]))
            if w[i] > 0:
                act.append((L.E.values[i], s * w[i] / L.entry.values[i]))
    return w


def overlays(L, w, cfg, wc):
    w = _prev(L, w, cfg, wc)
    if HOOK["m"] is not None:
        m = np.array([HOOK["m"].get(k, 1.0) for k in key_of(L)])
        w = np.where(L.sleeve.isin(["A", "B", "C"]).values, w * m, w)
    if HOOK["cap"]:
        w = cap_weights(L, w, HOOK["C"])
    return w


N.apply_overlays = overlays


def sim_pct(T, C):
    """N1 sim with the stop distance set to PCT x entry: ATR array replaced by PCT x next open / KATR (dist = KATR x A[e-1])."""
    saved = {}
    for coin in T.coin.unique():
        cd = C[coin]
        saved[coin] = dict(cd.tf)
        for tf, (ts, O, H, L_, Cl, A) in list(cd.tf.items()):
            A2 = PCT * np.r_[O[1:], np.nan] / N.KATR
            cd.tf[tf] = (ts, O, H, L_, Cl, A2)
    try:
        return N.sim(T, C, stop=True)
    finally:
        for coin, d in saved.items():
            C[coin].tf = d


def exposure(r, Wd, t0, t1):
    L = r["L"]; L = L[L.w > 0]; Em = r["Em"]
    h0, h1 = Wd.grid.get_loc(pd.Timestamp(t0)), Wd.grid.get_loc(pd.Timestamp(t1))
    H = h1 - h0; ms = N.month_starts(Wd.grid, h0, h1); curve = r["curve"]
    cmax = np.zeros(H); gross = np.zeros(H)
    for coin, idx in L.groupby("coin").indices.items():
        b = np.nan_to_num(Wd.C[coin].Cf[h0:h1])
        a = L.a.values[idx].astype(int) - h0; E = np.minimum(L.E.values[idx].astype(int) - h0, H)
        u = L.side.values[idx] * L.w.values[idx] / L.entry.values[idx] * Em[np.searchsorted(ms, a, side="right") - 1]
        d = np.zeros(H + 1); np.add.at(d, a, u); np.add.at(d, E, -u)
        net = np.abs(np.cumsum(d[:-1]) * b)
        cmax = np.maximum(cmax, net); gross += net
    return float((cmax / curve).max()), float((gross / curve).max())


def main():
    proto = OUT / "N6_PROTOCOL_PREREGISTERED.md"
    assert sha(proto) == (OUT / "N6_PROTOCOL_SHA256.txt").read_text().split()[0], "N6 protocol changed"
    x = X.setup()
    n3 = json.loads((X.OUT / "claims_n3.json").read_text())
    assert n3["adopted"] == ["X2", "X3"] and x.base_cfg == {"stop": False} and x.gname is None
    Wd = x.Wd
    HOOK["C"] = Wd.C
    allL0 = x.allL
    allS1 = pd.concat([sim_pct(Wd.T[s], Wd.C) for s in "ABC"], ignore_index=True)
    assert (allS1[["sleeve", "coin", "tf", "fam", "side", "entry_time"]].values == allL0[["sleeve", "coin", "tf", "fam", "side", "entry_time"]].values).all()
    log("S1 stopped share", round(allS1.stopped.mean(), 4))
    WINS = dict(dev=N.WIN["dev"], P1=N.WIN["P1"], P2=N.WIN["P2"], P3=N.WIN["P3"])

    def run(stop35, cap, t0, t1, want=False, m=None):
        x.allL = allS1 if stop35 else allL0
        HOOK["cap"], HOOK["m"] = cap, m
        try:
            return X.runv(x, X.variant(x, None, True, guard=True), t0, t1, want=want)
        finally:
            x.allL = allL0; HOOK["cap"], HOOK["m"] = False, None
    rows, cal, monthly, expo = [], {}, {}, {}
    for name, (s35, cp) in {"base": (False, False), "S1": (True, False), "S2": (False, True), "S3": (True, True)}.items():
        for wn, (t0, t1) in WINS.items():
            r = run(s35, cp, t0, t1, want=(wn == "dev"))
            cal[(name, wn)] = r["calmar"]
            if wn == "dev":
                expo[name] = exposure(r, Wd, t0, t1)
                monthly[name] = r.pop("monthly"); r.pop("curve"); r.pop("Em"); r.pop("L")
            rows.append(dict(trial="T19", variant=name, window=wn, **r))
        log(name, {wn: round(cal[(name, wn)], 3) for wn in WINS}, "max coin / max gross", tuple(round(v, 3) for v in expo[name]))
    assert abs(cal[("base", "dev")] - n3["combo"]["dev"]) < 1e-9, "base does not reproduce N3 FINAL"
    acc = {v: (cal[(v, "dev")] >= 0.9 * cal[("base", "dev")] and cal[(v, "P1")] >= 0.9 * cal[("base", "P1")]
               and cal[(v, "P2")] >= 0.9 * cal[("base", "P2")] and expo[v][0] < expo["base"][0]) for v in ("S1", "S2", "S3")}
    choice = "S3" if acc["S3"] else (max([v for v in ("S1", "S2") if acc[v]], key=lambda v: cal[(v, "dev")]) if (acc["S1"] or acc["S2"]) else None)
    s35, cp = {"S1": (True, False), "S2": (False, True), "S3": (True, True), None: (False, False)}[choice]
    log("T19 acceptable", acc, "choice", choice)
    # ---------------- T20 ----------------
    P = pd.read_parquet(N.ROOT / "logs" / "research_n5_ai" / "N5_predictions.parquet")
    P["entry_time"] = pd.to_datetime(P.entry_time)
    P = P[P.p_E.notna()].sort_values("entry_time").reset_index(drop=True)
    P["month"] = P.entry_time.dt.to_period("M")
    months = sorted(P.month.unique())
    mult = np.ones(len(P))
    for k, M in enumerate(months):
        if k < 3:
            continue
        prior = P.p_E.values[(P.month < M).values]
        med, sd = np.median(prior), prior.std()
        raw_prior = np.clip(1 + (prior - med) / (2 * sd), 0.5, 1.5)
        cur = (P.month == M).values
        mult[cur] = np.clip(1 + (P.p_E.values[cur] - med) / (2 * sd), 0.5, 1.5) / raw_prior.mean()
    P["m"] = mult
    P[["sleeve", "coin", "tf", "fam", "side", "entry_time", "p_E", "m"]].to_parquet(OUT / "N6_multipliers.parquet", index=False)
    mdict = dict(zip(key_of(P), mult))
    base2 = {wn: run(s35, cp, *w_, want=(wn == "dev")) for wn, w_ in (("dev", WINS["dev"]), ("P1", ("2021-01-01", "2024-01-01")), ("P2", WINS["P2"]), ("P3", WINS["P3"]))}
    ai = {wn: run(s35, cp, *w_, want=(wn == "dev"), m=mdict) for wn, w_ in (("dev", WINS["dev"]), ("P1", ("2021-01-01", "2024-01-01")), ("P2", WINS["P2"]), ("P3", WINS["P3"]))}
    monthly["AI_sizing"] = ai["dev"]["monthly"]
    for nm, d in (("base_T20", base2), ("AI_sizing", ai)):
        for wn, r in d.items():
            rows.append(dict(trial="T20", variant=nm, window=wn, **{k: v for k, v in r.items() if k not in ("monthly", "curve", "Em", "L")}))
    log("T20 base", {k: round(v["calmar"], 3) for k, v in base2.items()}, "AI", {k: round(v["calmar"], 3) for k, v in ai.items()})
    rnd = []
    keys = key_of(P)
    for i in range(NR):
        rng = np.random.default_rng(SEED + i)
        perm = mult.copy()
        for M in months:
            ii = np.flatnonzero((P.month == M).values)
            perm[ii] = mult[ii][rng.permutation(len(ii))]
        rr = run(s35, cp, *WINS["dev"], m=dict(zip(keys, perm)))
        rnd.append(dict(i=i, calmar=rr["calmar"]))
        if i % 10 == 0:
            log("random sizing", i, round(rr["calmar"], 3))
    R = pd.DataFrame(rnd); R.to_csv(OUT / "N6_random_sizing.csv", index=False)
    p95 = float(np.percentile(R.calmar, 95))
    Mx = pd.DataFrame(monthly); Mx.index = Mx.index.astype(str); Mx.to_csv(OUT / "N6_monthly_dev.csv")
    srs = []
    for f in (N.OUT / "N1_monthly_dev.csv", N.ROOT / "logs" / "research_n2_regime" / "N2_monthly_dev.csv", X.OUT / "N3_monthly_dev.csv"):
        M_ = pd.read_csv(f, index_col=0); srs += [M_[c].mean() / M_[c].std(ddof=1) for c in M_.columns if c != "base"]
    srs += [Mx[c].mean() / Mx[c].std(ddof=1) for c in ("S1", "S2", "S3", "AI_sizing")]
    sr_var = float(np.var(srs, ddof=1))
    dsr_v, sr, sr0 = N.dsr(pd.Series(Mx["AI_sizing"].values), sr_var, 39)
    g = {"dev>base": ai["dev"]["calmar"] > base2["dev"]["calmar"], "dev>random_p95": ai["dev"]["calmar"] > p95,
         "P1_P2>base": ai["P1"]["calmar"] > base2["P1"]["calmar"] and ai["P2"]["calmar"] > base2["P2"]["calmar"], "DSR>=0.95": dsr_v >= 0.95}
    t20 = "T20 PASS" if all(g.values()) else "T20 FAIL"
    t19 = f"T19 safety adopted: {choice}" if choice else "T19 no safety variant acceptable"
    pd.DataFrame(rows).to_csv(OUT / "N6_results.csv", index=False)
    claims = dict(protocol_sha=sha(proto), code_sha=sha(Path(__file__)), t19=dict(acceptable=acc, choice=choice, exposure=expo,
                  calmar={f"{k[0]}|{k[1]}": v for k, v in cal.items()}, s1_stopped_share=float(allS1.stopped.mean()), verdict=t19),
                  t20=dict(gates=g, random_p95=p95, dsr=dsr_v, sr=sr, sr0=sr0, sr_var=sr_var, verdict=t20,
                           calmar_ai={k: v["calmar"] for k, v in ai.items()}, calmar_base={k: v["calmar"] for k, v in base2.items()},
                           mult_mean=float(mult[np.array([m != 1.0 for m in mult])].mean()) if (mult != 1).any() else 1.0),
                  verdict=f"{t19}; {t20}",
                  files={f.name: sha(f) for f in sorted(OUT.glob("N6_*")) if f.is_file() and "stdout" not in f.name.lower()})
    (OUT / "claims_n6.json").write_text(json.dumps(claims, indent=1, default=float))
    log(json.dumps({k: v for k, v in claims.items() if k != "files"}, indent=1, default=float))
    (OUT / "run_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
