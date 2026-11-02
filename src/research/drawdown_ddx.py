"""DDX: verified ledger of past drawdown trials (Part A) + forward drawdown band for ECO-W2 (Part B).
Protocol logs/drawdown_ddx/DDX_PROTOCOL_PREREGISTERED.md. Descriptive only: nothing is fitted or selected.
Run: python src/research/drawdown_ddx.py"""
import hashlib, json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "logs" / "drawdown_ddx"
PROTO_SHA = (OUT / "PROTOCOL_SHA256.txt").read_text().split()[0]
SERIES = ROOT / "data/derived/eco/e2_daily_series.parquet"
CFG = ROOT / "deploy/eco_config.json"
E0 = 10_000.0
HS = (30, 90, 180, 365)
NPATH = 10_000
SEED = 20261027
L_MAIN = 20

# (id, lever, folder, sha files, claims file)
ROWS = [
    ("A01", "Step 19 base (RS top-20 long 80%)", "logs/strategy_1d_step19_largecap", ["PROTOCOL_SHA256.txt"], "claims.json"),
    ("A02", "Steps 17/18 market + veto brain", "logs/strategy_1d_step17_18", ["PROTOCOL_SHA256.txt"], "claims.json"),
    ("A03", "Step 20 large-cap market gate", "logs/strategy_1d_step20_largecap_gate", ["PROTOCOL_SHA256.txt"], "claims.json"),
    ("A04", "Step 21 crash brain", "logs/strategy_1d_step21_crash", ["PROTOCOL_SHA256.txt"], "claims.json"),
    ("A05", "Step 26 exit (tail) brain", "logs/strategy_1d_step26_exit", ["PROTOCOL_SHA256.txt"], "claims.json"),
    ("A06", "Step 27 exposure f (D1 sleeve)", "logs/strategy_1d_step27_combine", ["PROTOCOL_SHA256.txt"], "claims.json"),
    ("A07", "Step 28 vol sizing", "logs/strategy_1d_step28_volsize", ["PROTOCOL_SHA256.txt"], "claims.json"),
    ("A08", "F2 long-short", "logs/strategy_f2_longshort", ["F2_PROTOCOL_SHA256.txt"], "claims.json"),
    ("A09", "F7 stop rules", "logs/strategy_f7_risk", ["F7_PROTOCOL_SHA256.txt"], "claims.json"),
    ("A10", "R1 E1a/E1b BTC hedge", "logs/research_r1", ["R1_PROTOCOL_SHA256.txt"], "claims_E1.json"),
    ("A11", "R1 E4 inverse-vol weights", "logs/research_r1", ["R1_PROTOCOL_SHA256.txt"], "claims_E4.json"),
    ("A12", "ECO E-2 combination (W2, live)", "logs/eco", ["ECO_PROTOCOL_SHA256.txt"], "claims_eco_e2.json"),
    ("A13", "ECO-T4 profit lock", "logs/eco", ["ECO_PROTOCOL_SHA256.txt", "ECO_AMENDMENT_1_SHA256.txt"], "claims_eco_t4.json"),
    ("A14", "Master-audit G3 loss rules (R2 rule portfolio)", "logs/research_master_audit", ["PROTOCOL_SHA256.txt"], "claims_master_audit.json"),
    ("A15", "N2 regime gate (N1 system)", "logs/research_n2_regime", ["N2_PROTOCOL_SHA256.txt"], "claims_n2.json"),
    ("A16", "N6 = T19 safety sizing (N1 system)", "logs/research_n6_safety_sizing", ["N6_PROTOCOL_SHA256.txt"], "claims_n6.json"),
]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def dig(o, path):
    for k in path:
        o = o[k]
    return o


def dd_final(v, prepend=None):
    v = np.asarray(v, float)
    if prepend is not None:
        v = np.r_[prepend, v]
    run = np.maximum.accumulate(v)
    return float((1 - v / run).max()), float(v[-1])


def sha_checks():
    rows = []
    for rid, _, folder, files, claims in ROWS:
        d = ROOT / folder
        cj = json.loads((d / claims).read_text())
        csha = cj.get("protocol_sha256", cj.get("protocol_sha"))
        for sf in files:
            for line in (d / sf).read_text().splitlines():
                t = line.split()
                if len(t) < 2 or len(t[0]) != 64:
                    continue
                name = t[1].lstrip("*")
                p = d / name if (d / name).exists() else ROOT / name
                kind = "protocol" if "PREREGISTERED" in name else "other"
                got = sha(p) if p.exists() else "MISSING"
                rows.append(dict(id=rid, sha_file=f"{folder}/{sf}", file=name, kind=kind, stored=t[0], recomputed=got,
                                 ok=got == t[0],
                                 claims_match=(t[0] in (csha, cj.get("amendment_sha"))) if kind == "protocol" else ""))
    return pd.DataFrame(rows)


def ledger():
    L = []

    def add(rid, item, role, cdd, cfin, path=None, col=None, prepend=None, rel=False, decision="", note=""):
        r = dict(id=rid, item=item, role=role, claimed_dd_pct=cdd, claimed_final=cfin, recomputed_dd_pct=np.nan,
                 recomputed_final=np.nan, dd_ok="", final_ok="", decision=decision, note=note, equity_file=path or "")
        if path:
            p = ROOT / path
            v = pd.read_parquet(p)[col].dropna() if p.suffix == ".parquet" else pd.read_csv(p)[col]
            dd, fin = dd_final(v.to_numpy(), prepend)
            r["recomputed_dd_pct"], r["recomputed_final"] = dd * 100, fin
            if rel:
                r["dd_ok"] = abs(dd * 100 - cdd) <= 1e-9 * max(1, abs(cdd))
                r["final_ok"] = abs(fin - cfin) <= 1e-9 * max(1, abs(cfin)) if cfin == cfin else ""
            else:
                r["dd_ok"] = abs(dd * 100 - cdd) <= 0.01 + 1e-12
                r["final_ok"] = abs(fin - cfin) <= 0.01 + 1e-9 if cfin == cfin else ""
        L.append(r)

    def cl(folder, f):
        return json.loads((ROOT / folder / f).read_text())

    def port(rid, folder, names, files, base_keys=("portfolio",), decision_path=("gates", "decision")):
        c = cl(folder, "claims.json")
        dec = dig(c, decision_path)
        for n, role in names:
            x = dig(c, base_keys + (n,))
            add(rid, n, role, x["max_dd_pct"], x["final"], f"{folder}/{files[n]}" if n in files else None, "equity",
                decision=dec)

    port("A01", "logs/strategy_1d_step19_largecap", [("AI", "variant"), ("BTC_HOLD", "comparison")],
         {"AI": "AI_equity.csv", "BTC_HOLD": "BTC_HOLD_equity.csv"}, decision_path=("gates", "decision"))
    port("A02", "logs/strategy_1d_step17_18", [("FULL", "variant"), ("R5_ONLY", "comparison")],
         {"FULL": "FULL_equity.csv", "R5_ONLY": "R5_ONLY_equity.csv"})
    port("A03", "logs/strategy_1d_step20_largecap_gate", [("GATED", "variant"), ("UNGATED", "comparison")],
         {"GATED": "GATED_equity.csv", "UNGATED": "UNGATED_equity.csv"})
    port("A04", "logs/strategy_1d_step21_crash",
         [("ALARM", "variant"), ("ALARM_CONTROL", "control"), ("UNGATED", "comparison")],
         {"ALARM": "ALARM_equity.csv", "ALARM_CONTROL": "ALARM_CONTROL_equity.csv", "UNGATED": "UNGATED_equity.csv"})
    port("A05", "logs/strategy_1d_step26_exit", [("AI_VETO", "variant"), ("BASE", "comparison")],
         {"AI_VETO": "MAIN_2021_26_AI_VETO_daily_equity.csv"}, base_keys=("main",))
    # A06 exposure: decision table rows mix = D1
    dtab = pd.read_csv(ROOT / "logs/strategy_1d_step27_combine/decision_table.csv")
    for f, tag in ((1.0, "100"), (0.75, "75"), (0.5, "50"), (0.3, "30")):
        x = dtab[(dtab.mix == "D1") & (np.isclose(dtab.f, f))].iloc[0]
        add("A06", f"D1 f={f}", "comparison" if f == 1.0 else "variant", float(x.MAIN_max_dd_pct), float(x.MAIN_final),
            f"logs/strategy_1d_step27_combine/sleeves_MAIN_f{tag}.csv", "D1",
            decision="exposure table (no gate per f)")
    c = cl("logs/strategy_1d_step28_volsize", "claims.json")
    add("A07", "MAIN.VOL", "variant", c["MAIN"]["VOL"]["max_dd_pct"], c["MAIN"]["VOL"]["final"],
        "logs/strategy_1d_step28_volsize/vol_path_MAIN.csv", "equity", decision=c["gates"]["decision"])
    add("A07", "MAIN.FIXED_050", "comparison", c["MAIN"]["FIXED_050"]["max_dd_pct"], c["MAIN"]["FIXED_050"]["final"],
        decision=c["gates"]["decision"])
    c = cl("logs/strategy_f2_longshort", "claims.json")
    for n, role, f in (("AI_LS", "variant", "equity_MAIN_AI_LS.csv"), ("AI_LO", "comparison", "equity_MAIN_AI_LO.csv")):
        x = c["MAIN"][n]["mix"]
        add("A08", f"MAIN.{n}", role, x["max_dd_pct"], x["final"], f"logs/strategy_f2_longshort/{f}", "M_AI3",
            decision=c["gates"]["decision"])
    c = cl("logs/strategy_f7_risk", "claims.json")
    for n, role, f in (("RS", "variant", "equity_MAIN_AI_RS.csv"), ("OFF_LS", "comparison", "equity_MAIN_AI_OFF_LS.csv")):
        x = c["MAIN"][n]["mix"]
        add("A09", f"MAIN.{n}", role, x["max_dd_pct"], x["final"], f"logs/strategy_f7_risk/{f}", "M_AI3",
            decision=c["gates"]["decision"])
    for rid, cf, names in (("A10", "claims_E1.json", ("E1a", "E1b")), ("A11", "claims_E4.json", ("E4",))):
        c = cl("logs/research_r1", cf)
        for n in names:
            x = c["results"][n]["result"]["mix"]
            add(rid, n, "variant", x["max_dd_pct"], x["final"], f"logs/research_r1/equity_{n}.csv", "M_AI3",
                decision=c["results"][n]["gates"]["decision"])
        add(rid, "baseline F7 RS", "comparison", c["baseline"]["max_dd_pct"], c["baseline"]["final"],
            "logs/research_r1/equity_BASE_F7_RS.csv", "M_AI3", decision="baseline")
    c = cl("logs/eco", "claims_eco_e2.json")
    E2 = pd.read_csv(ROOT / "logs/eco/E2_results.csv").set_index(["window", "config"])
    for key, role in (("dev|ECO-W2", "variant"), ("dev|1D_alone_combo", "comparison"), ("dev|N1_alone", "comparison"),
                      ("P3|ECO-W2", "variant"), ("P3|1D_alone_combo", "comparison"), ("P3|N1_alone", "comparison")):
        w, cfg = key.split("|")
        add("A12", key, role, c["results"][key]["mtm_dd"] * 100, float(E2.loc[(w, cfg), "final"]),
            "data/derived/eco/e2_daily_series.parquet", key, prepend=E0, rel=True,
            decision="ECO-W2 adopted (E-2 gates)" if cfg == "ECO-W2" else "")
    c = cl("logs/eco", "claims_eco_t4.json")
    add("A13", "combined_T4 dev", "variant", c["combined_T4"]["dev"]["mtm_dd"] * 100, np.nan, decision=c["verdict"],
        note=f"comparison dev|ECO-W2 calmar {c['combined_ref_dev']:.4f} vs T4 {c['combined_T4']['dev']['calmar']:.4f}")
    add("A13", "combined_T4 P3", "variant", c["combined_T4"]["P3"]["mtm_dd"] * 100, np.nan, decision=c["verdict"])
    c = cl("logs/research_master_audit", "claims_master_audit.json")
    add("A14", "G1_f0.005_K6 (base)", "comparison", c["G1_f0.005_K6"]["maxdd"] * 100, c["G1_f0.005_K6"]["final"],
        decision="no decision field in claims")
    add("A14", "L1 (DD de-risk)", "variant", c["L1"]["maxdd"] * 100, c["L1"]["final"], decision="no decision field in claims")
    c = cl("logs/research_n2_regime", "claims_n2.json")
    for n, role in (("base", "comparison"), ("R1", "variant"), ("R2", "variant")):
        add("A15", f"{n} dev", role, c["mtm_dd"][f"{n}|dev"] * 100, np.nan, decision=c["verdict"],
            note=f"dev calmar {c['calmar'][f'{n}|dev']:.4f}")
    c = cl("logs/research_n6_safety_sizing", "claims_n6.json")
    for n in ("base", "S1", "S2", "S3"):
        add("A16", f"T19 {n}", "comparison" if n == "base" else "variant", np.nan, np.nan, decision=c["t19"]["verdict"],
            note=f"dev calmar {c['t19']['calmar'][f'{n}|dev']:.4f} (claims hold calmar, no DD)")
    T = pd.DataFrame(L)
    # report-only ratios: variant vs the first comparison row of the same id
    T["dd_ratio_vs_comparison"] = np.nan
    T["final_ratio_vs_comparison"] = np.nan
    for rid, g in T.groupby("id"):
        comp = g[g.role == "comparison"]
        if comp.empty:
            continue
        b = comp.iloc[0]
        for i in g.index[g.role != "comparison"]:
            T.loc[i, "dd_ratio_vs_comparison"] = T.loc[i, "claimed_dd_pct"] / b.claimed_dd_pct
            T.loc[i, "final_ratio_vs_comparison"] = T.loc[i, "claimed_final"] / b.claimed_final
    return T


def eco_returns():
    d = pd.read_parquet(SERIES)
    out = {}
    for w in ("dev", "P3"):
        v = d[f"{w}|ECO-W2"].dropna()
        prev = np.r_[E0, v.to_numpy()[:-1]]
        out[w] = pd.Series(v.to_numpy() / prev - 1, index=v.index)
    out["ALL"] = pd.concat([out["dev"], out["P3"]]).sort_index()
    return out


def path_stats(R):
    """R: (paths, H) daily returns -> maxDD per path (incl. equity_0 = 1) and total return."""
    eq = np.cumprod(1 + R, axis=1)
    eq = np.concatenate([np.ones((R.shape[0], 1)), eq], axis=1)
    run = np.maximum.accumulate(eq, axis=1)
    return (1 - eq / run).max(axis=1), eq[:, -1] - 1


def stat_boot(r, H, L, rng):
    n = len(r)
    idx = np.empty((NPATH, H), dtype=np.int64)
    idx[:, 0] = rng.integers(0, n, NPATH)
    jump = rng.random((NPATH, H)) < 1.0 / L
    fresh = rng.integers(0, n, (NPATH, H))
    for t in range(1, H):
        idx[:, t] = np.where(jump[:, t], fresh[:, t], (idx[:, t - 1] + 1) % n)
    return path_stats(r[idx])


def summarise(dd, ret, kill):
    s = {f"dd_p{q}": float(np.percentile(dd, q)) for q in (50, 75, 90, 95, 99)}
    s.update({f"ret_p{q}": float(np.percentile(ret, q)) for q in (1, 5, 25, 50, 75, 95)})
    s["P_dd_ge_kill"] = float((dd >= kill).mean())
    s["P_ret_lt_0"] = float((ret < 0).mean())
    return s


def main():
    assert sha(OUT / "DDX_PROTOCOL_PREREGISTERED.md") == PROTO_SHA
    kill = float(json.loads(CFG.read_text())["kill_K"])
    pd.DataFrame([{"file": str(p.relative_to(ROOT)), "sha256": sha(p)} for p in (SERIES, CFG)]).to_csv(
        OUT / "input_manifest.csv", index=False)
    S = sha_checks()
    S.to_csv(OUT / "sha_checks.csv", index=False)
    T = ledger()
    T.to_csv(OUT / "ledger.csv", index=False)
    rets = eco_returns()
    # Part B bootstrap: one parent generator, fresh child per (L, base, H) in protocol order
    rng = np.random.default_rng(SEED)
    jobs = [(L_MAIN, b, H) for b in ("ALL", "P3", "DEV") for H in HS] + \
           [(L, b, H) for L in (5, 60) for b in ("ALL", "P3") for H in HS]
    kids = rng.spawn(len(jobs))
    band, sens = [], []
    for (L, b, H), kid in zip(jobs, kids):
        r = rets["dev" if b == "DEV" else b].to_numpy()
        dd, ret = stat_boot(r, H, L, kid)
        row = dict(base=b, H=H, L=L, n_base=len(r), **summarise(dd, ret, kill))
        (band if L == L_MAIN else sens).append(row)
        print(f"boot L{L} {b} H{H}: dd p95 {row['dd_p95']:.4f} p99 {row['dd_p99']:.4f} ret p50 {row['ret_p50']:.4f}", flush=True)
    B = pd.DataFrame(band)
    B.to_csv(OUT / "band_bootstrap.csv", index=False)
    pd.DataFrame(sens).to_csv(OUT / "band_sensitivity.csv", index=False)
    # historical rolling windows
    roll = []
    for b in ("ALL", "P3", "DEV"):
        s = rets["dev" if b == "DEV" else b]
        r, ix = s.to_numpy(), s.index
        for H in HS:
            if len(r) < H:
                continue
            W = np.lib.stride_tricks.sliding_window_view(r, H)
            dd, ret = path_stats(W)
            k = int(np.argmax(dd))
            roll.append(dict(base=b, H=H, n_windows=len(dd), dd_p50=float(np.percentile(dd, 50)),
                             dd_p95=float(np.percentile(dd, 95)), dd_max=float(dd.max()),
                             worst_start=str(ix[k].date()), worst_end=str(ix[k + H - 1].date()),
                             ret_p5=float(np.percentile(ret, 5)), ret_p50=float(np.percentile(ret, 50)),
                             ret_min=float(ret.min()), share_ret_lt_0=float((ret < 0).mean()),
                             share_dd_ge_kill=float((dd >= kill).mean())))
    pd.DataFrame(roll).to_csv(OUT / "rolling_windows.csv", index=False)
    A = B[B.base == "ALL"][["H", "dd_p95", "dd_p99"]].rename(columns={"dd_p95": "yellow_dd", "dd_p99": "red_dd"})
    A.insert(0, "age_days_up_to", A.H)
    A.to_csv(OUT / "alarm_thresholds.csv", index=False)
    # statements fixed in protocol §3
    ver = bool(S[S.kind == "protocol"].ok.all() and (S[S.kind == "protocol"].claims_match.astype(str) != "False").all()
               and (T.dd_ok.astype(str) != "False").all() and (T.final_ok.astype(str) != "False").all())
    p_kill = float(B[(B.base == "ALL") & (B.H == 365)].P_dd_ge_kill.iloc[0])
    p3_med = float(B[(B.base == "P3") & (B.H == 365)].ret_p50.iloc[0])
    res = dict(protocol_sha=PROTO_SHA, code_sha=sha(Path(__file__)), kill_K=kill, seed=SEED, n_paths=NPATH, L=L_MAIN,
               partA_verified=ver,
               partA_mismatches=T[(T.dd_ok.astype(str) == "False") | (T.final_ok.astype(str) == "False")][
                   ["id", "item"]].to_dict("records"),
               sha_failures=S[~S.ok].to_dict("records"),
               P_kill_365_ALL=p_kill, statement2="realistic within a year" if p_kill > 0.10 else "tail event (<=10%)",
               P3_median_365_return=p3_med, statement3=p3_med <= 0)
    json.dump(res, open(OUT / "RESULTS.json", "w"), indent=1, default=str)
    names = ["input_manifest.csv", "sha_checks.csv", "ledger.csv", "band_bootstrap.csv", "band_sensitivity.csv",
             "rolling_windows.csv", "alarm_thresholds.csv", "RESULTS.json"]
    (OUT / "OUTPUT_SHA256.txt").write_text("".join(f"{sha(OUT / x)}  {x}\n" for x in names))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
