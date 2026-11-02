"""
E11 SHADOW line of the F4 paper log (protocol: logs/forward_ls_f4/shadow_e11/E11_SHADOW_PROTOCOL.md).
NO ORDERS, no keys, NO network: it reads only what F4 stored that day (16B prediction files, the F4 perp klines /
funding files, the live spot folders) and recomputes from PAPER_START, with the Round 1 engine:
  E11      = F7 RS rules, NEW longs on the coin's perp when the perp bar exists and the daily scale gate passes
             (cost 0.10 %, funding paid / received, liquidation rule on the bar low), otherwise on spot;
  C0 check = the same engine with perp longs OFF must equal F4's LS_RS sleeves of that day within $0.01.
Writes logs/forward_ls_f4/shadow_e11/{equity,positions}_<asof>.csv and appends a hash-chained ledger line that is
tied to the F4 ledger line of the same as-of day. F4 calls main(asof) after its own ledger line (failures are logged
there and never touch the F4 ledger). Manual: python shadow_e11_f4.py <asof>
"""
import sys
import json
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "pipeline_1d", SRC_DIR / "analytics", SRC_DIR / "execution", SRC_DIR / "research"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import forward_ls_f4 as Q
import r1_engine as E

FD, FB, CR, S23, S24, F2R, F7R = Q.FD, Q.FB, Q.CR, Q.S23, Q.S24, Q.F2R, Q.F7R
from config import LOGS_DIR
OUT = LOGS_DIR / "forward_ls_f4" / "shadow_e11"
PROTO = OUT / "E11_SHADOW_PROTOCOL.md"                  # fixed path (the output folder may be redirected in a sandbox)
LEDGER = OUT / "ledger.csv"
SLEEVES = ("D1", "H4", "H1")


def log(msg):
    OUT.mkdir(parents=True, exist_ok=True)
    line = f"[{pd.Timestamp.now('UTC').strftime('%Y-%m-%d %H:%M:%S')} UTC] {msg}"
    with open(OUT / "run_log.txt", "a", encoding="utf-8") as f:
        f.write(line + "\n")
    try:
        print(line, flush=True)
    except Exception:
        pass


def lines(start, asof, rows, data, last, dir_1h, perp_h, fund, gate):
    """(E11 sleeves, C0 sleeves with perp longs off). Same inputs and grids as forward_ls_f4.build_lines."""
    grids = dict(D1=pd.date_range(start, asof, freq="D"), H4=pd.date_range(start, asof + pd.Timedelta(hours=20), freq="4h"),
                 H1=pd.date_range(start, asof + pd.Timedelta(hours=23), freq="h"))
    decide = dict(D1=np.arange(len(grids["D1"])) % 5 == 0, H4=(np.arange(len(grids["H4"])) + 1) % 6 == 0,
                  H1=(np.arange(len(grids["H1"])) + 1) % 24 == 0)
    syms = sorted(set().union(*[set(r.symbol) for r in rows.values()]))
    bars4 = {s: S23.bars_4h(Path(dir_1h) / f"{s}_1h_full.csv.gz") for s in syms if (Path(dir_1h) / f"{s}_1h_full.csv.gz").exists()}
    bars1 = {s: S24.bars_1h(Path(dir_1h) / f"{s}_1h_full.csv.gz").astype("float64") for s in syms if (Path(dir_1h) / f"{s}_1h_full.csv.gz").exists()}
    spot = dict(D1=F2R.spot_arrays_daily(data, last, [s for s in rows["D1"].symbol.unique() if s in data], grids["D1"]),
                H4=F2R.spot_arrays_bars({s: b[["open", "close"]] for s, b in bars4.items()}, grids["H4"]),
                H1=F2R.spot_arrays_bars({s: b[["open", "close"]] for s, b in bars1.items()}, grids["H1"]))
    perp = {k: F2R.perp_arrays(perp_h, grids[k], F2R.STEP[k]) for k in grids}
    low = {}
    for k in grids:
        low[k] = {}
        for s, d in perp_h.items():
            a = d[["low"]] if F2R.STEP[k] == "h" else d.low.resample(F2R.STEP[k], label="left", closed="left").min().to_frame("low")
            low[k][s] = a.low.reindex(grids[k]).values
    out = {}
    for name, perp_longs in (("E11", True), ("C0", False)):
        sl = {}
        for k in SLEEVES:
            pa, gidx = perp[k], {t: i for i, t in enumerate(grids[k])}

            def shortable(s, t, pa=pa, gidx=gidx):
                return s in pa and np.isfinite(pa[s][2][gidx[t]]) and gate.get((s, t.normalize()), False)

            def long_perp_ok(s, t, k_, pa=pa, gidx=gidx):
                return s in pa and np.isfinite(pa[s][0][gidx[t]]) and gate.get((s, t.normalize()), False)
            kw = dict(F7R.RS)
            if perp_longs:
                kw.update(long_perp_ok=long_perp_ok, perp_low=low[k])
            sl[k] = E.sim_ls(rows[k], grids[k], decide[k], spot[k], pa, fund, F2R.F50, F2R.F50, F2R.N_HOLD, F2R.KEEP,
                             F2R.C_LONG, F2R.C_SHORT, shortable=shortable, **kw)
        out[name] = sl
    return out


def main(asof):
    asof = pd.Timestamp(asof)
    assert FD.sha_file(PROTO) == (OUT / "E11_SHADOW_PROTOCOL_SHA256.txt").read_text().split()[0], "shadow protocol changed"
    eqf = OUT / f"equity_{asof.date()}.csv"
    if eqf.exists():
        log(f"as-of {asof.date()} already logged -> nothing to do")
        return
    L4 = pd.read_csv(Q.LEDGER)
    L4 = L4[L4["asof"] == str(asof.date())]
    assert len(L4) == 1, f"F4 has no ledger line for {asof.date()}"
    l4 = L4.iloc[-1]
    rows, notes = Q.rows_16b(asof)
    data_k, last_k, data_n, last_n, _ = CR.load_folder(FD.LIVE1D, FD.LIVE1H, asof)
    data, last = {**data_k, **data_n}, {**last_k, **last_n}
    syms = sorted(set().union(*[set(r.symbol) for r in rows.values()]))
    names = Q.perp_names(syms)
    perp_h, fund = Q.load_perp_dir(Q.PERP_DIR, names)
    h = FD.sha_bytes("".join(FD.sha_file(Q.PERP_DIR / f"{s}_perp_1h.csv") for s in sorted(perp_h)).encode())
    assert h == l4.perp_files_sha256, "F4 perp files changed since the F4 line of this day"
    spot1h = {s: S24.bars_1h(FD.LIVE1H / f"{s}_1h_full.csv.gz").close.astype("float64") for s in perp_h
              if (FD.LIVE1H / f"{s}_1h_full.csv.gz").exists()}
    gate = Q.gate_table(perp_h, spot1h, list(pd.date_range(Q.PAPER_START, asof, freq="D")))
    f4eq = pd.read_csv(Q.LOG / "paper" / f"equity_{asof.date()}.csv", parse_dates=["date"]).set_index("date")
    if asof == Q.PAPER_START:
        eq = pd.DataFrame(dict(D1=[10_000.0], H4=[10_000.0], H1=[10_000.0], M_AI3=[10_000.0]), index=[asof])
        c0, n_perp, n_spot, fund_paid, pos = True, 0, 0, 0.0, pd.DataFrame()
    else:
        res = lines(Q.PAPER_START, asof, rows, data, last, FD.LIVE1H, perp_h, fund, gate)
        d0 = pd.DataFrame({k: F2R.daily_eq(v["eq"], k) for k, v in res["C0"].items()})
        c0 = bool(all(abs(float(d0.loc[d, k]) - float(f4eq.loc[d, f"LS_RS_{k}"])) < 0.01 for d in f4eq.index for k in SLEEVES))
        if not c0:
            notes.append("C0_FAIL: shadow engine with perp longs off != F4 LS_RS -> E11 numbers of this day untrusted")
        eqd = pd.DataFrame({k: F2R.daily_eq(v["eq"], k) for k, v in res["E11"].items()})
        eq = eqd.assign(M_AI3=eqd.mean(axis=1))
        n_perp = int(sum(v["perp_longs"] for v in res["E11"].values()))
        n_spot = int(sum(v["spot_longs"] for v in res["E11"].values()))
        tr = pd.concat([v["trades"] for v in res["E11"].values()], ignore_index=True) if any(len(v["trades"]) for v in res["E11"].values()) else pd.DataFrame()
        fund_paid = float(tr[(tr.side == "long") & (tr.get("venue") == "perp")].funding.sum()) if len(tr) and "venue" in tr else 0.0
        pos = pd.DataFrame([dict(sleeve=k, side=x.side, venue=(getattr(x, "venue", None) if isinstance(getattr(x, "venue", None), str)
                                                              else ("perp" if x.side == "short" else "spot")),
                                 symbol=x.symbol, entry=str(x.entry_time), cost=round(x.cost, 2), entry_px=getattr(x, "entry_px", np.nan))
                            for k, v in res["E11"].items() if len(v["trades"])
                            for x in v["trades"][v["trades"].reason == "end_of_test"].itertuples()])
    OUT.mkdir(parents=True, exist_ok=True)
    eq.rename_axis("date").to_csv(eqf)
    pf = OUT / f"positions_{asof.date()}.csv"
    pos.to_csv(pf, index=False)
    if asof != Q.PAPER_START:                                  # every trade since PAPER_START, E11 line (2026-10-17)
        tl = [v["trades"].assign(sleeve=k) for k, v in res["E11"].items() if len(v["trades"])]
        (pd.concat(tl, ignore_index=True) if tl else pd.DataFrame()).to_csv(OUT / f"trades_{asof.date()}.csv", index=False)
    written = pd.Timestamp.now("UTC").tz_localize(None)
    line = dict(run_utc=str(written), asof=str(asof.date()), on_time=bool(written <= asof + pd.Timedelta(days=1, hours=3)),
                C0=c0, E11=round(float(eq.M_AI3.iloc[-1]), 2), LS_RS=float(l4.LS_RS), perp_longs=n_perp, spot_longs=n_spot,
                long_funding_closed=round(fund_paid, 2), f4_line_sha256=l4.line_sha256, equity_sha256=FD.sha_file(eqf),
                positions_sha256=FD.sha_file(pf), code_sha256=FD.sha_file(__file__), engine_sha256=FD.sha_file(E.__file__),
                protocol_sha256=FD.sha_file(PROTO), notes=json.dumps(notes)[:2000])
    line["prev_sha256"] = pd.read_csv(LEDGER).line_sha256.iloc[-1] if LEDGER.exists() else "GENESIS"
    line["line_sha256"] = FD.sha_bytes(json.dumps(line, sort_keys=True).encode())
    pd.DataFrame([line]).to_csv(LEDGER, mode="a", index=False, header=not LEDGER.exists())
    log(f"E11 shadow as-of {asof.date()}: E11 {line['E11']} vs LS_RS {line['LS_RS']}, C0={c0}, perp longs {n_perp}, spot longs {n_spot}")


if __name__ == "__main__":
    try:
        main(sys.argv[1])
    except Exception:
        log("RUN FAILED:\n" + traceback.format_exc())
        sys.exit(1)
