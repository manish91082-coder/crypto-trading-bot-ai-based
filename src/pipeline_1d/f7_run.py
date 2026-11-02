"""
F7 runner: risk rules for the long-short book. Same inputs as F2 (loaders imported from f2_run, which writes nothing on
import); every output goes to logs/strategy_f7_risk. Protocol: logs/strategy_f7_risk/F7_PROTOCOL_PREREGISTERED.md
"""
import sys
import json
import time
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "pipeline_1d", SRC_DIR / "analytics", SRC_DIR / "execution", SRC_DIR / "research"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
import f2_run as F2R
import f7_risk as F
from config import LOGS_DIR

CR, S13, S19, S22, S23, S24, S27, S1 = F2R.CR, F2R.S13, F2R.S19, F2R.S22, F2R.S23, F2R.S24, F2R.S27, F2R.S1
OUT = LOGS_DIR / "strategy_f7_risk"
PROTO = "F7_PROTOCOL_PREREGISTERED.md"
F2_CLAIMS = F2R.OUT / "claims.json"
N_HOLD, KEEP, F50, C_LONG, C_SHORT, C_SHORT_STRESS = F2R.N_HOLD, F2R.KEEP, F2R.F50, F2R.C_LONG, F2R.C_SHORT, F2R.C_SHORT_STRESS
RS = dict(stop=1.50, stop_slip=0.01, cooldown_days=30)
K1 = 0.35
DSR_N = 83


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(per):
    """The F2 inputs for one period (copied from f2_run.run_period, no file writes)."""
    start, end = S27.PER[per]
    if per == "MAIN":
        dk, lk, dn, ln, _ = CR.load_folder(S13.UNI / "1d", S13.UNI / "1h", end)
        dir1h = S24.UNI1H
    else:
        dk, lk, dn, ln, _ = S22.load_pre(S22.PRE / "1d", S22.PRE / "1h", S22.ASOF_PRE)
        dir1h = S24.PRE1H
    data, last = {**dk, **dn}, {**lk, **ln}
    rows = {}
    if per == "MAIN":
        rows["AI"] = dict(D1=pd.read_csv(S19.OUT / "U_AI_predictions.csv", usecols=["symbol", "date", "score"], parse_dates=["date"]).rename(columns={"date": "t"}),
                          H4=pd.read_csv(S23.OUT / "test_predictions_4h.csv", usecols=["symbol", "bar", "R6_AI"], parse_dates=["bar"]).rename(columns={"bar": "t", "R6_AI": "score"}),
                          H1=pd.read_csv(S24.OUT / "test_predictions_1h.csv", usecols=["symbol", "bar", "R24_AI"], parse_dates=["bar"]).rename(columns={"bar": "t", "R24_AI": "score"}))
        rows["CONTROL"] = dict(D1=pd.read_csv(S19.OUT / "U_CONTROL_predictions.csv", usecols=["symbol", "date", "score"], parse_dates=["date"]).rename(columns={"date": "t"}),
                               H4=pd.read_csv(S23.OUT / "test_predictions_4h.csv", usecols=["symbol", "bar", "R6_CONTROL"], parse_dates=["bar"]).rename(columns={"bar": "t", "R6_CONTROL": "score"}),
                               H1=pd.read_csv(S24.OUT / "test_predictions_1h.csv", usecols=["symbol", "bar", "R24_CONTROL"], parse_dates=["bar"]).rename(columns={"bar": "t", "R24_CONTROL": "score"}))
    else:
        rows["AI"] = dict(D1=pd.read_csv(S22.OUT / "U_pre2020_predictions.csv", usecols=["symbol", "date", "score"], parse_dates=["date"]).rename(columns={"date": "t"}),
                          H4=pd.read_csv(S23.OUT / "pre2020_predictions_4h.csv", usecols=["symbol", "bar", "R6_FROZEN"], parse_dates=["bar"]).rename(columns={"bar": "t", "R6_FROZEN": "score"}),
                          H1=pd.read_csv(S24.OUT / "pre2020_predictions_1h.csv", usecols=["symbol", "bar", "R24_FROZEN"], parse_dates=["bar"]).rename(columns={"bar": "t", "R24_FROZEN": "score"}))
    syms = sorted(set().union(*[set(r.symbol) for b in rows.values() for r in b.values()]))
    grids = dict(D1=pd.date_range(start, end, freq="D"), H4=pd.date_range(start, end + pd.Timedelta(hours=20), freq="4h"),
                 H1=pd.date_range(start, end + pd.Timedelta(hours=23), freq="h"))
    decide = dict(D1=np.arange(len(grids["D1"])) % 5 == 0, H4=(np.arange(len(grids["H4"])) + 1) % 6 == 0,
                  H1=(np.arange(len(grids["H1"])) + 1) % 24 == 0)
    bars4 = {s: S23.bars_4h(dir1h / f"{s}_1h_full.csv.gz") for s in syms if (dir1h / f"{s}_1h_full.csv.gz").exists()}
    bars1 = {s: S24.bars_1h(dir1h / f"{s}_1h_full.csv.gz").astype("float64") for s in syms if (dir1h / f"{s}_1h_full.csv.gz").exists()}
    spot = dict(D1=F2R.spot_arrays_daily(data, last, [s for s in syms if s in data], grids["D1"]),
                H4=F2R.spot_arrays_bars({s: b[["open", "close"]] for s, b in bars4.items()}, grids["H4"]),
                H1=F2R.spot_arrays_bars({s: b[["open", "close"]] for s, b in bars1.items()}, grids["H1"]))
    if per == "MAIN":
        perp_h, gate = F2R.load_perp({s: b.close for s, b in bars1.items()})
        perp = {k: F2R.perp_arrays(perp_h, grids[k], F2R.STEP[k]) for k in grids}
        fund = F2R.funding_events(perp_h)
    else:
        daily_df = {s: data[s].set_index("timestamp")[["open", "high", "close"]].loc[:last[s]] for s in syms if s in data}
        perp = dict(D1=F2R.synthetic_perp(daily_df, grids["D1"]), H4=F2R.synthetic_perp(bars4, grids["H4"]), H1=F2R.synthetic_perp(bars1, grids["H1"]))
        fund = {}
    return dict(start=start, end=end, rows=rows, grids=grids, decide=decide, spot=spot, perp=perp, fund=fund)


def k1_count(e):
    """K1 (report only): times the equity falls 35 % below its running peak (a new event after each recovery to a new peak)."""
    a = np.r_[F.CAP, e.values]
    pk, fired, n = a[0], False, 0
    for v in a:
        if v > pk:
            pk, fired = v, False
        if not fired and v <= (1 - K1) * pk:
            n, fired = n + 1, True
    return n


def run(I, per, brain, name, inv_s, cs, rules, save_trades=False):
    sleeves = {}
    for k in ("D1", "H4", "H1"):
        sleeves[k] = F.sim_ls(I["rows"][brain][k], I["grids"][k], I["decide"][k], I["spot"][k], I["perp"][k], I["fund"], F50, inv_s,
                              N_HOLD, KEEP, C_LONG, cs, **rules)
        if save_trades:
            sleeves[k]["trades"].to_csv(OUT / f"trades_{per}_{k}_{brain}_{name}.csv", index=False)
    eqd = pd.DataFrame({k: F2R.daily_eq(v["eq"], k) for k, v in sleeves.items()})
    mix_eq = eqd.mean(axis=1)
    eqd.assign(M_AI3=mix_eq).to_csv(OUT / f"equity_{per}_{brain}_{name}.csv", index_label="date")
    mix_final = float(np.mean([v["final"] for v in sleeves.values()]))
    sh = pd.concat([v["trades"] for v in sleeves.values() if len(v["trades"])])
    sh = sh[sh.side == "short"] if len(sh) else sh
    res = dict(mix=S27.stats(mix_final, mix_eq, I["start"], I["end"]),
               sleeves={k: dict(**S27.stats(v["final"], F2R.daily_eq(v["eq"], k), I["start"], I["end"]), liquidations=v["liquidations"],
                                stops=v["stops"], cooldown_blocks=v["cooldown_blocks"], age_blocks=v["age_blocks"]) for k, v in sleeves.items()},
               short_trades=int(len(sh)), short_pnl_mix=round(float(sh.pnl.sum()) / 3, 2) if len(sh) else 0.0,
               short_funding_mix=round(float(sh.funding.sum()) / 3, 2) if len(sh) else 0.0,
               liquidations=int(sum(v["liquidations"] for v in sleeves.values())), stops=int(sum(v["stops"] for v in sleeves.values())),
               K1_events=dict(mix=k1_count(mix_eq), **{k: k1_count(eqd[k]) for k in eqd}))
    print(per, brain, name, json.dumps(res["mix"]), "liq", res["liquidations"], "stops", res["stops"], flush=True)
    return res


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    h_ = sha(OUT / PROTO)
    assert h_ == (OUT / "F7_PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed after registration"
    t0 = time.time()
    f2 = json.loads(F2_CLAIMS.read_text())["MAIN"]
    I = load("MAIN")
    M = {}
    M["OFF_LO"] = run(I, "MAIN", "AI", "OFF_LO", 0.0, C_SHORT, {})
    M["OFF_LS"] = run(I, "MAIN", "AI", "OFF_LS", F50, C_SHORT, {})
    g0 = {k: abs(M["OFF_LS"]["sleeves"][k]["final"] - f2["AI_LS"]["sleeves"][k]["final"]) < 0.01 and
          abs(M["OFF_LO"]["sleeves"][k]["final"] - f2["AI_LO"]["sleeves"][k]["final"]) < 0.01 for k in ("D1", "H4", "H1")}
    print("G0", g0, flush=True)
    assert all(g0.values()), "G0 failed: the F7 engine with rules off does not reproduce F2 -> INVALID, stop here"
    M["RS"] = run(I, "MAIN", "AI", "RS", F50, C_SHORT, RS, save_trades=True)
    M["RS_cost020"] = run(I, "MAIN", "AI", "RS_cost020", F50, C_SHORT_STRESS, RS)
    M["RS_CONTROL"] = run(I, "MAIN", "CONTROL", "RS", F50, C_SHORT, RS)
    M["RS_stop30"] = run(I, "MAIN", "AI", "RS_stop30", F50, C_SHORT, dict(RS, stop=1.30))
    M["RS_stop75"] = run(I, "MAIN", "AI", "RS_stop75", F50, C_SHORT, dict(RS, stop=1.75))
    M["RS_age30"] = run(I, "MAIN", "AI", "RS_age30", F50, C_SHORT, dict(RS, min_age_days=30))
    del I
    IP = load("PRE")
    P = dict(LO=run(IP, "PRE", "AI", "LO", 0.0, C_SHORT, {}), RS=run(IP, "PRE", "AI", "RS", F50, C_SHORT, RS))
    lo, rs, f2ls = M["OFF_LO"]["mix"], M["RS"]["mix"], f2["AI_LS"]["mix"]
    g = dict(G0=all(g0.values()), G1=M["RS"]["liquidations"] <= 7, G2=rs["max_dd_pct"] <= f2ls["max_dd_pct"],
             G3=rs["final"] > lo["final"] and rs["calmar"] > lo["calmar"], G4=rs.get("ret_2022", -1) > 0,
             G5=M["RS_cost020"]["mix"]["final"] > lo["final"], G6=rs["final"] > M["RS_CONTROL"]["mix"]["final"])
    g = {k: bool(v) for k, v in g.items()}
    g["decision"] = "INVALID_G0" if not g["G0"] else "PASS" if all(g[k] for k in ("G1", "G2", "G3", "G4", "G5", "G6")) else "FAIL"
    c1 = json.loads((S1.OUT / "claims.json").read_text())
    e = pd.read_csv(OUT / "equity_MAIN_AI_RS.csv", parse_dates=["date"]).set_index("date").M_AI3
    r = e.pct_change().dropna().values
    import scipy.stats as ss
    sr = float(r.mean() / r.std(ddof=1))
    dsr = dict(sr_annual_365=sr * np.sqrt(365), N=DSR_N,
               dsr=S1.dsr(sr, len(r), float(ss.skew(r)), float(ss.kurtosis(r, fisher=False)), DSR_N, c1["V_daily_sr"])[1])
    claims = dict(protocol_sha256=h_, G0_detail=g0, F2_reference=dict(LS=f2ls, LO=f2["AI_LO"]["mix"], LS_liquidations=f2["AI_LS"]["liquidations"]),
                  MAIN=M, PRE=P, gates=g, DSR_RS_mix=dsr, seconds=round(time.time() - t0),
                  trades_sha256={k: sha(OUT / f"trades_MAIN_{k}_AI_RS.csv") for k in ("D1", "H4", "H1")})
    (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=str))
    print("GATES", json.dumps(g), "DSR", dsr)


if __name__ == "__main__":
    main()
