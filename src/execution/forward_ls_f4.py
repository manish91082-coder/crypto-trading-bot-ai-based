"""
F4 long-short PAPER forward log (protocol: logs/forward_ls_f4/F4_PROTOCOL_PREREGISTERED.md).
NO ORDERS, no keys: public Binance USD-M market data only. Reads the Step 16B prediction files (read only) and every day:
  - downloads / extends the perp 1h klines and funding of the coins in those files (overlap re-check, never silent),
  - recomputes three paper lines from PAPER_START with the F7 engine: LS_RS (primary, F7 rules), LS_F2 (no rules),
    LO (check line; must equal the 16B paper sleeves -> C1),
  - appends a hash-chained ledger line.
Usage: pythonw forward_ls_f4.py          (scheduled forward run)
       python  forward_ls_f4.py --test   (technical test on 2026-09 with the research predictions; written to test/)
"""
import sys
import json
import time
import hashlib
import traceback
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "pipeline_1d", SRC_DIR / "analytics", SRC_DIR / "execution", SRC_DIR / "research"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import forward_dryrun_1d as FD
import forward_multi_16b as FB
import core_rows_1d as CR
import step23_4h_brain as S23
import step24_1h_brain as S24
import f2_run as F2R
import f7_risk as F
import f7_run as F7R
from config import DATA_DIR, LOGS_DIR

# fee amendment 2 (logs/fees, a111c707): the true fee for every F4 line and the E11 shadow (which imports this module); f2_run.py stays as locked
_FR = json.loads((Path(__file__).resolve().parents[2] / "deploy" / "fees.json").read_text())["rules"]
F2R.C_LONG, F2R.C_SHORT = _FR["paper_spot_per_side"], _FR["paper_futures_taker_per_side"]   # were 0.0025 / 0.0010

LOG = LOGS_DIR / "forward_ls_f4"
PROTO = LOG / "F4_PROTOCOL_PREREGISTERED.md"
LEDGER, RUNLOG = LOG / "ledger.csv", LOG / "run_log.txt"
PERP_DIR = DATA_DIR / "forward_f4" / "perp"
PAPER_START = FB.PAPER_START                       # 2026-10-15, as 16B
API = "https://fapi.binance.com"
H = pd.Timedelta(hours=1)
LINES = dict(LS_RS=(F2R.F50, F7R.RS), LS_F2=(F2R.F50, {}), LO=(0.0, {}))


def log(msg):
    line = f"[{pd.Timestamp.now('UTC').strftime('%Y-%m-%d %H:%M:%S')} UTC] {msg}"
    LOG.mkdir(parents=True, exist_ok=True)
    with open(RUNLOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    try:
        print(line, flush=True)
    except Exception:
        pass


def get(path, **q):
    url = API + path + ("?" + "&".join(f"{k}={v}" for k, v in q.items()) if q else "")
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "f4-paper-log"}), timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception:
            if i == 3:
                raise
            time.sleep(2 * (i + 1))


def ms(t):
    return int(pd.Timestamp(t).value // 1_000_000)


# ------------------------------------------------------------------ perpetual names and data
def perp_names(symbols):
    """symbol -> (perp name, scale) or None. F1 list first; otherwise exchangeInfo (TRADING perpetuals)."""
    f1 = pd.read_csv(LOGS_DIR / "futures_um_download" / "perp_names.csv").set_index("symbol").perp
    out, info = {}, None
    for s in sorted(symbols):
        p = f1.get(s) if s in f1.index else None
        if s not in f1.index:
            if info is None:
                info = {x["symbol"]: x for x in get("/fapi/v1/exchangeInfo")["symbols"]
                        if x.get("contractType") == "PERPETUAL" and x.get("status") == "TRADING"}
            base = s[:-4]
            p = next((c for c in (s, f"1000{base}USDT", f"1000000{base}USDT") if c in info), None)
        if not isinstance(p, str):
            out[s] = None
            continue
        scale = 1e6 if p.startswith("1000000") else 1e3 if p.startswith("1000") and not s.startswith("1000") else 1.0
        out[s] = (p, scale)
    return out


def fetch_klines(perp, t0, t1):
    rows, cur = [], ms(t0)
    end = ms(t1 + H) - 1
    while cur <= end:
        k = get("/fapi/v1/klines", symbol=perp, interval="1h", startTime=cur, endTime=end, limit=1500)
        if not k:
            break
        rows += k
        cur = k[-1][0] + 3_600_000
        if len(k) < 1500:
            break
    d = pd.DataFrame([r[:6] for r in rows], columns=["timestamp", "open", "high", "low", "close", "volume"])
    d["timestamp"] = pd.to_datetime(d.timestamp, unit="ms")
    for c in ("open", "high", "low", "close", "volume"):
        d[c] = d[c].astype(float)
    return d.drop_duplicates("timestamp")


def fetch_funding(perp, t0, t1):
    rows, cur, end = [], ms(t0), ms(t1 + H) - 1
    while cur <= end:
        f = get("/fapi/v1/fundingRate", symbol=perp, startTime=cur, endTime=end, limit=1000)
        if not f:
            break
        rows += f
        cur = f[-1]["fundingTime"] + 1
        if len(f) < 1000:
            break
    d = pd.DataFrame([(x["fundingTime"], float(x["fundingRate"])) for x in rows], columns=["time", "funding_rate"])
    d["time"] = pd.to_datetime(d.time, unit="ms")
    return d.drop_duplicates("time")


def update_perp(sym, perp, asof, start, pdir, notes):
    """Extend the stored klines / funding up to asof 23:00; the last 48 stored hours are re-downloaded and compared."""
    pdir.mkdir(parents=True, exist_ok=True)
    fk, ff = pdir / f"{sym}_perp_1h.csv", pdir / f"{sym}_funding.csv"
    t_end = asof + pd.Timedelta(hours=23)
    first = start - pd.Timedelta(days=7)
    old = pd.read_csv(fk, parse_dates=["timestamp"]) if fk.exists() else None
    t0 = max(first, old.timestamp.max() - pd.Timedelta(hours=47)) if old is not None and len(old) else first
    new = fetch_klines(perp, t0, t_end)
    new["perp"] = perp
    if old is not None and len(old):
        m = old.merge(new, on="timestamp", suffixes=("", "_n"))
        bad = m[(m[["open", "high", "low", "close"]].values != m[["open_n", "high_n", "low_n", "close_n"]].values).any(axis=1)]
        if len(bad):
            notes.append(f"{sym}: {len(bad)} stored kline hours differ on re-download (kept stored): {bad.timestamp.astype(str).tolist()[:5]}")
        new = pd.concat([old, new[new.timestamp > old.timestamp.max()]], ignore_index=True)
    new = new[(new.timestamp >= first) & (new.timestamp <= t_end)].sort_values("timestamp")
    new.to_csv(fk, index=False)
    oldf = pd.read_csv(ff, parse_dates=["time"]) if ff.exists() else None
    f = fetch_funding(perp, first, t_end)
    if oldf is not None and len(oldf):
        m = oldf.merge(f, on="time", suffixes=("", "_n"))
        if (m.funding_rate != m.funding_rate_n).any():
            notes.append(f"{sym}: funding differs on re-download (kept stored)")
        f = pd.concat([oldf, f[f.time > oldf.time.max()]], ignore_index=True)
    f.sort_values("time").to_csv(ff, index=False)
    return fk, ff


def load_perp_dir(pdir, names):
    perp, fund = {}, {}
    for s, nm in names.items():
        fk, ff = pdir / f"{s}_perp_1h.csv", pdir / f"{s}_funding.csv"
        if nm is None or not fk.exists():
            continue
        d = pd.read_csv(fk, parse_dates=["timestamp"]).set_index("timestamp")
        for c in ("open", "high", "low", "close"):
            d[c] = d[c] / nm[1]
        perp[s] = d
        if ff.exists():
            fr = pd.read_csv(ff, parse_dates=["time"]).sort_values("time")
            px = d.close.reindex(pd.DatetimeIndex(fr.time.dt.floor("h")) - H).values      # last close before the event (F2 rule)
            ok = np.isfinite(px)
            fund[s] = (fr.time.values[ok].astype("datetime64[ns]"), fr.funding_rate.values[ok], px[ok])
    return perp, fund


def gate_table(perp, spot_close_1h, days):
    """Forward scale gate per (symbol, day): median perp/spot close over the 7 days ending at that day's end (>= 24 h)."""
    ok = {}
    for s, d in perp.items():
        sc = spot_close_1h.get(s)
        if sc is None:
            continue
        j = d.close.reindex(sc.index)
        r = (j / sc).where(j.notna() & sc.notna() & (sc > 0))
        for day in days:
            w = r[(r.index >= day - pd.Timedelta(days=6)) & (r.index < day + pd.Timedelta(days=1))].dropna()
            ok[(s, day)] = bool(len(w) >= 24 and 0.98 <= float(w.median()) <= 1.02)
    return ok


# ------------------------------------------------------------------ paper lines
def build_lines(start, asof, rows, data, last, dir_1h, perp_h, fund, gate):
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
    out, detail = {}, {}
    for line, (inv_s, rules) in LINES.items():
        sl = {}
        for k in ("D1", "H4", "H1"):
            pa, gidx = perp[k], {t: i for i, t in enumerate(grids[k])}

            def shortable(s, t, pa=pa, gidx=gidx):
                return s in pa and np.isfinite(pa[s][2][gidx[t]]) and gate.get((s, t.normalize()), False)
            sl[k] = F.sim_ls(rows[k], grids[k], decide[k], spot[k], pa, fund, F2R.F50, inv_s, F2R.N_HOLD, F2R.KEEP,
                             F2R.C_LONG, F2R.C_SHORT, shortable=shortable, **rules)
        eqd = pd.DataFrame({k: F2R.daily_eq(v["eq"], k) for k, v in sl.items()})
        out[line] = eqd.assign(M_AI3=eqd.mean(axis=1))
        detail[line] = sl
    return out, detail


def open_positions(detail):
    pos = []
    for line, sl in detail.items():
        for k, r in sl.items():
            t = r["trades"]
            if len(t):
                for x in t[t.reason == "end_of_test"].itertuples():
                    pos.append(dict(line=line, sleeve=k, side=x.side, symbol=x.symbol, entry=str(x.entry_time), cost=round(x.cost, 2),
                                    entry_px=getattr(x, "entry_px", np.nan)))
    return pd.DataFrame(pos)


def rows_16b(asof):
    d1, n1 = FB.load_scores("d1", asof, FB.PRED)
    h4, n4 = FB.load_scores("h4_r6", asof, FB.PRED)
    h1, nh = FB.load_scores("h1_r24", asof, FB.PRED)
    rows = dict(D1=d1.rename(columns={"date": "t"})[["symbol", "t", "score"]], H4=h4.rename(columns={"bar": "t"})[["symbol", "t", "score"]],
                H1=h1.rename(columns={"bar": "t"})[["symbol", "t", "score"]])
    return rows, n1 + n4 + nh


# ------------------------------------------------------------------ forward run
def already_logged(asof, ledger=None):
    """F4 amendment 1: skip only if the ledger holds a row for this as-of."""
    ledger = LEDGER if ledger is None else ledger
    return ledger.exists() and str(pd.Timestamp(asof).date()) in set(pd.read_csv(ledger)["asof"].astype(str))


def main(asof=None):
    now = pd.Timestamp.now("UTC").tz_localize(None)
    asof = now.normalize() - pd.Timedelta(days=1) if asof is None else pd.Timestamp(asof)   # asof: pre-flight test only
    eq_file = LOG / "paper" / f"equity_{asof.date()}.csv"
    if already_logged(asof):                                         # amendment 1: the ledger row, not the equity file
        log(f"as-of {asof.date()} already logged -> nothing to do")
        return
    if eq_file.exists():
        log(f"as-of {asof.date()}: paper files exist but no ledger row (an earlier run stopped) -> recomputed")
    assert asof >= PAPER_START, f"as-of {asof.date()} is before PAPER_START"
    assert FD.sha_file(PROTO) == (LOG / "F4_PROTOCOL_SHA256.txt").read_text().split()[0], "protocol changed after registration"
    led16 = FB.LEDGER

    def l16_rows():
        if not led16.exists():
            return None
        L = pd.read_csv(led16)
        return L[(L["asof"] == str(asof.date())) & (~L.test.astype(bool))]
    for _ in range(90):                                         # after a late wake every task fires at once: wait for 16B
        L16 = l16_rows()
        if L16 is not None and len(L16) == 1:
            break
        time.sleep(60)
    assert led16.exists(), "16B ledger missing"
    L16 = l16_rows()
    assert len(L16) == 1, f"16B has not logged as-of {asof.date()} yet"
    l16 = L16.iloc[-1]
    notes = []
    for kind, col in (("d1", "d1_sha256"), ("h4_r6", "h4_sha256"), ("h1_r24", "h1_sha256")):
        assert FD.sha_file(FB.PRED / f"{kind}_{asof.date()}.csv") == l16[col], f"16B {kind} file hash != 16B ledger"
    log(f"RUN start as-of {asof.date()}")
    rows, n16 = rows_16b(asof)
    notes += n16
    data_k, last_k, data_n, last_n, _ = CR.load_folder(FD.LIVE1D, FD.LIVE1H, asof)
    data, last = {**data_k, **data_n}, {**last_k, **last_n}
    syms = sorted(set().union(*[set(r.symbol) for r in rows.values()]))
    names = perp_names(syms)
    for s, nm in names.items():
        if nm is not None:
            update_perp(s, nm[0], asof, PAPER_START, PERP_DIR, notes)
    perp_h, fund = load_perp_dir(PERP_DIR, names)
    spot1h = {s: S24.bars_1h(FD.LIVE1H / f"{s}_1h_full.csv.gz").close.astype("float64") for s in perp_h if (FD.LIVE1H / f"{s}_1h_full.csv.gz").exists()}
    days = list(pd.date_range(PAPER_START, asof, freq="D"))
    gate = gate_table(perp_h, spot1h, days)
    if asof == PAPER_START:
        lines = {ln: pd.DataFrame(dict(D1=[F.CAP], H4=[F.CAP], H1=[F.CAP], M_AI3=[F.CAP]), index=[asof]) for ln in LINES}
        detail = {}
    else:
        lines, detail = build_lines(PAPER_START, asof, rows, data, last, FD.LIVE1H, perp_h, fund, gate)
    # C1: LO line == 16B paper sleeves
    p16 = pd.read_csv(FB.PAPER / f"equity_{asof.date()}.csv", parse_dates=["date"]).set_index("date")
    lo = lines["LO"]
    c1 = bool(all(abs(float(lo.loc[d, k]) - float(p16.loc[d, k])) < 0.01 for d in p16.index for k in ("D1", "H4", "H1")))
    if not c1:
        notes.append("C1_FAIL: LO line != 16B paper sleeves -> LS numbers of this day untrusted")
    (LOG / "paper").mkdir(parents=True, exist_ok=True)
    allq = pd.concat({ln: e for ln, e in lines.items()}, axis=1)
    allq.columns = [f"{a}_{b}" for a, b in allq.columns]
    allq.rename_axis("date").to_csv(eq_file)
    pos_file = LOG / "paper" / f"positions_{asof.date()}.csv"
    open_positions(detail).to_csv(pos_file, index=False)
    tl = [r["trades"].assign(line=ln, sleeve=k) for ln, sl in detail.items() for k, r in sl.items() if len(r["trades"])]
    (pd.concat(tl, ignore_index=True) if tl else pd.DataFrame()).to_csv(LOG / "paper" / f"trades_{asof.date()}.csv", index=False)  # every trade since PAPER_START (2026-10-17)
    orders_file = LOG / "paper" / f"orders_{asof.date()}.json"
    orders = {ln: {k: dict(r["pending"], equity_close=float(lines[ln][k].iloc[-1])) for k, r in sl.items()} for ln, sl in detail.items()}
    orders_file.write_text(json.dumps(orders, indent=1, default=str))
    gate_ok = sorted(s for (s, d), v in gate.items() if d == asof and v)
    written = pd.Timestamp.now("UTC").tz_localize(None)
    stops = {ln: int(sum(r["stops"] for r in sl.values())) for ln, sl in detail.items()}
    line = dict(run_utc=str(now), written_utc=str(written), asof=str(asof.date()),
                on_time=bool(written <= asof + pd.Timedelta(days=1, hours=3)), C1=c1,
                LS_RS=round(float(lines["LS_RS"].M_AI3.iloc[-1]), 2), LS_F2=round(float(lines["LS_F2"].M_AI3.iloc[-1]), 2),
                LO=round(float(lines["LO"].M_AI3.iloc[-1]), 2), stops_LS_RS=stops.get("LS_RS", 0),
                n_symbols=len(syms), n_perp=len(perp_h), n_shortable_today=len(gate_ok),
                d1_sha256=l16.d1_sha256, h4_sha256=l16.h4_sha256, h1_sha256=l16.h1_sha256, ledger16b_line_sha256=l16.line_sha256,
                perp_files_sha256=FD.sha_bytes("".join(FD.sha_file(PERP_DIR / f"{s}_perp_1h.csv") for s in sorted(perp_h)).encode()),
                equity_sha256=FD.sha_file(eq_file), positions_sha256=FD.sha_file(pos_file), orders_sha256=FD.sha_file(orders_file),
                code_sha256=FD.sha_file(__file__), engine_sha256=FD.sha_file(F.__file__), protocol_sha256=FD.sha_file(PROTO),
                notes=json.dumps(notes)[:3000])
    line["prev_sha256"] = pd.read_csv(LEDGER).line_sha256.iloc[-1] if LEDGER.exists() else "GENESIS"
    line["line_sha256"] = FD.sha_bytes(json.dumps(line, sort_keys=True).encode())
    pd.DataFrame([line]).to_csv(LEDGER, mode="a", index=False, header=not LEDGER.exists())
    log(f"RUN done as-of {asof.date()}: LS_RS {line['LS_RS']} LS_F2 {line['LS_F2']} LO {line['LO']} C1={c1} "
        f"shortable {len(gate_ok)} notes {len(notes)}")
    if LOG == LOGS_DIR / "forward_ls_f4":                      # E11 shadow line (own protocol + ledger); never in a sandbox
        try:
            import shadow_e11_f4 as SH
            SH.main(asof)
        except Exception:
            log("E11 SHADOW FAILED (the F4 ledger line above is unaffected): " + traceback.format_exc())


# ------------------------------------------------------------------ technical test (no ledger)
def test():
    """2026-09-01..2026-09-30 with the stored research predictions:
    T1 API klines / funding == F1 archive files (data.binance.vision) for every coin and hour (two sources);
    T2 the three lines computed from the API files == the same computed from the F1 files;
    T3 LO line == the research long-only simulators (S22 / sim4h / sim1h) on the same rows."""
    start, asof = pd.Timestamp("2026-09-01"), pd.Timestamp("2026-09-30")
    tdir = LOG / "test"
    pdir = tdir / "perp_api"
    I = F7R.load("MAIN")
    rows = {k: r[(r.t >= start) & (r.t <= asof + pd.Timedelta(hours=23))].reset_index(drop=True) for k, r in I["rows"]["AI"].items()}
    del I
    dk, lk, dn, ln_, _ = CR.load_folder(F2R.S13.UNI / "1d", F2R.S13.UNI / "1h", asof)
    data, last = {**dk, **dn}, {**lk, **ln_}
    syms = sorted(set().union(*[set(r.symbol) for r in rows.values()]))
    names = perp_names(syms)
    notes = []
    for s, nm in names.items():
        if nm is not None and (F2R.FUM / f"{s}_perp_1h.csv.gz").exists():
            update_perp(s, nm[0], asof, start, pdir, notes)
    # T1: two sources
    nh, nf, bad = 0, 0, []
    for s, nm in names.items():
        if nm is None or not (pdir / f"{s}_perp_1h.csv").exists():
            continue
        a = pd.read_csv(pdir / f"{s}_perp_1h.csv", parse_dates=["timestamp"]).set_index("timestamp")
        b = pd.read_csv(F2R.FUM / f"{s}_perp_1h.csv.gz", parse_dates=["timestamp"]).set_index("timestamp")
        j = a.join(b, rsuffix="_v", how="inner")
        j = j[(j.index >= start - pd.Timedelta(days=7)) & (j.index <= asof + pd.Timedelta(hours=23))]
        nh += len(j)
        for c in ("open", "high", "low", "close"):
            if not np.allclose(j[c], j[f"{c}_v"], rtol=0, atol=0):
                bad.append((s, c, int((j[c] != j[f"{c}_v"]).sum())))
        fa = pd.read_csv(pdir / f"{s}_funding.csv", parse_dates=["time"]).set_index("time").funding_rate
        fb = pd.read_csv(F2R.FUM / f"{s}_funding.csv", parse_dates=["time"]).set_index("time").funding_rate
        fj = pd.concat([fa, fb], axis=1, join="inner").dropna()
        fj = fj[(fj.index >= start - pd.Timedelta(days=7)) & (fj.index <= asof + pd.Timedelta(hours=23))]
        nf += len(fj)
        if (abs(fj.iloc[:, 0] - fj.iloc[:, 1]) > 1e-12).any():
            bad.append((s, "funding", int((abs(fj.iloc[:, 0] - fj.iloc[:, 1]) > 1e-12).sum())))
    print(f"T1 API vs archive: {nh} hours, {nf} funding events compared; mismatches: {bad}")
    # T2 / T3
    spot1h = {s: S24.bars_1h(F2R.S24.UNI1H / f"{s}_1h_full.csv.gz").close.astype("float64") for s in syms if (F2R.S24.UNI1H / f"{s}_1h_full.csv.gz").exists()}
    days = list(pd.date_range(start, asof, freq="D"))
    res = {}
    for src, loader in (("api", lambda: load_perp_dir(pdir, names)), ("archive", lambda: arch(names))):
        ph, fu = loader()
        res[src] = build_lines(start, asof, rows, data, last, F2R.S24.UNI1H, ph, fu, gate_table(ph, spot1h, days))[0]
    t2 = all(np.allclose(res["api"][ln].values, res["archive"][ln].values, rtol=0, atol=1e-6) for ln in LINES)
    S23.START, S23.END_BAR = start, asof + pd.Timedelta(hours=20)
    S24.START, S24.END_BAR = start, asof + pd.Timedelta(hours=23)
    eq16, _ = FB.paper_from_rows(start, asof, rows["D1"].rename(columns={"t": "date"}), rows["H4"].rename(columns={"t": "bar"}),
                                 rows["H1"].rename(columns={"t": "bar"}), data, last, F2R.S24.UNI1H)
    eq16 = eq16.set_index("date")
    lo = res["api"]["LO"]
    t3 = all(abs(float(lo.loc[d, k]) - float(eq16.loc[d, k])) < 0.01 for d in eq16.index for k in ("D1", "H4", "H1"))
    tdir.mkdir(parents=True, exist_ok=True)
    summ = dict(T1_hours=nh, T1_funding=nf, T1_mismatches=bad, T2_api_equals_archive=bool(t2), T3_LO_equals_research_sims=bool(t3),
                notes=notes, final={ln: round(float(e.M_AI3.iloc[-1]), 2) for ln, e in res["api"].items()})
    (tdir / "test_summary.json").write_text(json.dumps(summ, indent=2, default=str))
    print(json.dumps(summ, default=str))


def arch(names):
    perp, fund = {}, {}
    f1 = {s: nm for s, nm in names.items() if nm is not None and (F2R.FUM / f"{s}_perp_1h.csv.gz").exists()}
    for s, nm in f1.items():
        d = pd.read_csv(F2R.FUM / f"{s}_perp_1h.csv.gz", parse_dates=["timestamp"]).set_index("timestamp")
        for c in ("open", "high", "low", "close"):
            d[c] = d[c] / nm[1]
        perp[s] = d
        ff = F2R.FUM / f"{s}_funding.csv"
        if ff.exists():
            fr = pd.read_csv(ff, parse_dates=["time"]).sort_values("time")
            px = d.close.reindex(pd.DatetimeIndex(fr.time.dt.floor("h")) - H).values
            ok = np.isfinite(px)
            fund[s] = (fr.time.values[ok].astype("datetime64[ns]"), fr.funding_rate.values[ok], px[ok])
    return perp, fund


if __name__ == "__main__":
    if "--test" in sys.argv:
        test()
    else:
        try:
            main()
        except Exception:
            log("RUN FAILED:\n" + traceback.format_exc())
            sys.exit(1)
