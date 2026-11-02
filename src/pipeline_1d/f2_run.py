"""
F2 runner: long-only (G0 reproduction) and long-short runs for D1 / H4 / H1 and the M_AI3 mix, MAIN 2021-26 (real
USD-M perpetual data) and PRE 2018-19 (synthetic short on spot). Protocol: logs/strategy_f2_longshort/F2_PROTOCOL_PREREGISTERED.md
"""
import sys
import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "pipeline_1d", SRC_DIR / "analytics", SRC_DIR / "execution", SRC_DIR / "research"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
import core_rows_1d as CR
import step13_unseen_coins_1d as S13
import step19_large_caps_1d as S19
import step22_pre2020_exam_1d as S22
import step23_4h_brain as S23
import step24_1h_brain as S24
import step27_combine as S27
import overfit_audit_s1 as S1
import f2_longshort as F
from config import DATA_DIR, LOGS_DIR

OUT = LOGS_DIR / "strategy_f2_longshort"
PROTO = "F2_PROTOCOL_PREREGISTERED.md"
FUM = DATA_DIR / "futures_um"
N_HOLD, KEEP, F50, C_LONG, C_SHORT, C_SHORT_STRESS = 5, 10, 0.5, 0.0025, 0.0010, 0.0020
STEP = {"D1": "1D", "H4": "4h", "H1": "h"}
HOUR_LAST = {"D1": 0, "H4": 20, "H1": 23}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def spot_arrays_bars(px, grid):
    """sim1h / sim4h construction: o = open filled by the previous close, c = close forward-filled."""
    out = {}
    for s, b in px.items():
        last_t = b.close.last_valid_index()
        cf = b.close.reindex(grid).ffill()
        out[s] = (b.open.reindex(grid).fillna(cf.shift(1)).values.astype(float), cf.values.astype(float), last_t)
    return out


def spot_arrays_daily(data, last, syms, grid):
    out = {}
    for s in syms:
        d = data[s].set_index("timestamp")
        out[s] = (d.open.reindex(grid).values.astype(float), d.close.reindex(grid).ffill().values.astype(float), last[s])
    return out


def load_perp(spot_close_1h):
    """{sym: hourly perp DataFrame scaled to spot units} for coins passing the scale gate; plus the gate table."""
    names = pd.read_csv(LOGS_DIR / "futures_um_download" / "perp_names.csv")
    perp, gate = {}, []
    for r in names.itertuples():
        f = FUM / f"{r.symbol}_perp_1h.csv.gz"
        if not isinstance(r.perp, str) or not f.exists():
            gate.append(dict(symbol=r.symbol, perp=r.perp, status="no perpetual"))
            continue
        d = pd.read_csv(f, parse_dates=["timestamp"]).set_index("timestamp")
        scale = 1e6 if r.perp.startswith("1000000") else 1e3 if r.perp.startswith("1000") and not r.symbol.startswith("1000") else 1.0
        for c in ("open", "high", "low", "close"):
            d[c] = d[c] / scale
        sc = spot_close_1h.get(r.symbol)
        ratio = np.nan
        if sc is not None:
            j = d.close.reindex(sc.index)
            m = j.notna() & sc.notna() & (sc > 0)
            ratio = float((j[m] / sc[m]).median()) if m.sum() > 100 else np.nan
        ok = np.isfinite(ratio) and 0.98 <= ratio <= 1.02
        gate.append(dict(symbol=r.symbol, perp=r.perp, scale=scale, hours=len(d), median_ratio=ratio, status="ok" if ok else "excluded"))
        if ok:
            perp[r.symbol] = d
    return perp, pd.DataFrame(gate)


def perp_arrays(perp, grid, step):
    out = {}
    for s, d in perp.items():
        if step == "h":
            a = d[["open", "high", "close"]]
        else:
            g = d.resample(step, label="left", closed="left")
            a = pd.DataFrame(dict(open=g.open.first(), high=g.high.max(), close=g.close.last())).dropna()
        out[s] = (a.open.reindex(grid).values, a.high.reindex(grid).values, a.close.reindex(grid).values, a.index.min(), a.index.max())
    return out


def funding_events(perp):
    out = {}
    for s, d in perp.items():
        f = FUM / f"{s}_funding.csv"
        if not f.exists():
            continue
        fr = pd.read_csv(f, parse_dates=["time"]).sort_values("time")
        px = d.close.reindex(pd.DatetimeIndex(fr.time.dt.floor("h")) - pd.Timedelta(hours=1)).values   # last close before the event
        ok = np.isfinite(px)
        out[s] = (fr.time.values[ok].astype("datetime64[ns]"), fr.funding_rate.values[ok], px[ok])
    return out


def synthetic_perp(spot_bars_or_daily, grid):
    out = {}
    for s, b in spot_bars_or_daily.items():
        out[s] = (b.open.reindex(grid).values, b.high.reindex(grid).values, b.close.reindex(grid).values, b.close.first_valid_index(), b.close.last_valid_index())
    return out


def daily_eq(e, sleeve):
    if sleeve == "D1":
        return e
    e = e[e.index.hour == HOUR_LAST[sleeve]]
    e.index = e.index.normalize()
    return e


def run_period(per, brains):
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
    spot = dict(D1=spot_arrays_daily(data, last, [s for s in syms if s in data], grids["D1"]),
                H4=spot_arrays_bars({s: b[["open", "close"]] for s, b in bars4.items()}, grids["H4"]),
                H1=spot_arrays_bars({s: b[["open", "close"]] for s, b in bars1.items()}, grids["H1"]))
    info = {}
    if per == "MAIN":
        perp_h, gate = load_perp({s: b.close for s, b in bars1.items()})
        gate.to_csv(OUT / "F1_G2_scale_gate.csv", index=False)
        info["F1_G2"] = dict(coins=len(gate), ok=int((gate.status == "ok").sum()), excluded=gate[gate.status == "excluded"].symbol.tolist(),
                             no_perp=int((gate.status == "no perpetual").sum()))
        perp = {k: perp_arrays(perp_h, grids[k], STEP[k]) for k in grids}
        fund = funding_events(perp_h)
    else:
        daily_df = {s: data[s].set_index("timestamp")[["open", "high", "close"]].loc[:last[s]] for s in syms if s in data}
        perp = dict(D1=synthetic_perp(daily_df, grids["D1"]), H4=synthetic_perp(bars4, grids["H4"]), H1=synthetic_perp(bars1, grids["H1"]))
        fund = {}
    res = {}
    for brain, rb in rows.items():
        for mode, inv_s, cs in (("LO", 0.0, C_SHORT), ("LS", F50, C_SHORT)) + ((("LS_cost020", F50, C_SHORT_STRESS),) if brain == "AI" and per == "MAIN" else ()):
            sleeves = {}
            for k in ("D1", "H4", "H1"):
                r = F.sim_ls(rb[k], grids[k], decide[k], spot[k], perp[k], fund, F50, inv_s, N_HOLD, KEEP, C_LONG, cs)
                sleeves[k] = r
                if brain == "AI" and mode == "LS":
                    r["trades"].to_csv(OUT / f"trades_{per}_{k}_{brain}_{mode}.csv", index=False)
            eqd = pd.DataFrame({k: daily_eq(v["eq"], k) for k, v in sleeves.items()})
            mix_eq = eqd.mean(axis=1)
            mix_final = float(np.mean([v["final"] for v in sleeves.values()]))
            stats = S27.stats(mix_final, mix_eq, start, end)
            sh = pd.concat([v["trades"] for v in sleeves.values() if len(v["trades"])])
            sh = sh[sh.side == "short"] if len(sh) else sh
            res[f"{brain}_{mode}"] = dict(mix=stats, sleeves={k: S27.stats(v["final"], daily_eq(v["eq"], k), start, end) for k, v in sleeves.items()},
                                          short_trades=int(len(sh)), short_pnl=round(float(sh.pnl.sum()) / 3, 2) if len(sh) else 0.0,
                                          liquidations=int(sum(v["liquidations"] for v in sleeves.values())))
            eqd.assign(M_AI3=mix_eq).to_csv(OUT / f"equity_{per}_{brain}_{mode}.csv", index_label="date")
            print(per, brain, mode, json.dumps(res[f"{brain}_{mode}"]["mix"]), {k: round(v["final"], 2) for k, v in sleeves.items()}, flush=True)
    return res, info


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    h_ = sha(OUT / PROTO)
    assert h_ == (OUT / "F2_PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed after registration"
    flog = pd.read_csv(LOGS_DIR / "futures_um_download" / "files_log.csv")
    claims = dict(protocol_sha256=h_, F1_G1=dict(files=len(flog), ok=int((flog.status == "OK").sum()), not_found=int((flog.status == "404").sum()),
                                                  other=int((~flog.status.isin(["OK", "404"])).sum())))
    claims["F1_G1"]["pass"] = claims["F1_G1"]["other"] == 0
    ref = json.loads((S27.OUT / "claims.json").read_text())["sleeve_finals"]
    for per in ("MAIN", "PRE"):
        res, info = run_period(per, None)
        claims[per] = res
        claims.update(info)
        lo = res["AI_LO"]["sleeves"]
        claims[f"G0_{per}"] = {k: abs(lo[k]["final"] - ref[f"{per}_f50"][k]) < 0.01 for k in ("D1", "H4", "H1")}
    M, P = claims["MAIN"], claims["PRE"]
    lo, ls = M["AI_LO"]["mix"], M["AI_LS"]["mix"]
    g = dict(G0=all(claims["G0_MAIN"].values()) and all(claims["G0_PRE"].values()) and claims["F1_G1"]["pass"],
             G1=ls["final"] > lo["final"] and ls["calmar"] > lo["calmar"],
             G2=ls["max_dd_pct"] < lo["max_dd_pct"],
             G3=ls.get("ret_2022", -1) > 0,
             G4=ls["final"] > M["CONTROL_LS"]["mix"]["final"],
             G5=P["AI_LS"]["mix"]["final"] > P["AI_LO"]["mix"]["final"],
             G6=M["AI_LS_cost020"]["mix"]["final"] > lo["final"])
    g = {k: bool(v) for k, v in g.items()}
    g["decision"] = "INVALID_G0" if not g["G0"] else "PASS" if all(g[k] for k in ("G1", "G2", "G3", "G4", "G5", "G6")) else "FAIL"
    claims["gates"] = g
    # DSR (report only)
    c1 = json.loads((S1.OUT / "claims.json").read_text())
    e = pd.read_csv(OUT / "equity_MAIN_AI_LS.csv", parse_dates=["date"]).set_index("date").M_AI3
    r = e.pct_change().dropna().values
    import scipy.stats as ss
    sr = float(r.mean() / r.std(ddof=1))
    claims["DSR_LS_mix"] = dict(sr_annual_365=sr * np.sqrt(365), N=79,
                                dsr=S1.dsr(sr, len(r), float(ss.skew(r)), float(ss.kurtosis(r, fisher=False)), 79, c1["V_daily_sr"])[1])
    (OUT / "claims.json").write_text(json.dumps(claims, indent=2, default=str))
    print("G0", claims["G0_MAIN"], claims["G0_PRE"], "F1", claims["F1_G1"], claims.get("F1_G2"))
    print("GATES", json.dumps(g), "DSR", claims["DSR_LS_mix"])


if __name__ == "__main__":
    main()
