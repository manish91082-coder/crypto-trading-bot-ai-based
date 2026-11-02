"""
Step 16B forward logger (protocol: logs/forward_multi_16b/STEP16B_PROTOCOL_PREREGISTERED.md).
NO ORDERS. Runs after the Step 16 logger, reads its live folders and prediction file (read only), and every day:
  - scores the 4H R6 brain (Step 23 recipe) on the 6 four-hour bars of the as-of day,
  - scores the 1h R24 brain (Step 24 recipe) on the 24 hours of the as-of day,
  - recomputes the M_AI3 paper portfolio (D1 = Step 19 R5, H4 = R6, H1 = R24; 1/3 each, 50 % invested, cost 0.25 %)
    from PAPER_START with the research simulators (unchanged),
  - appends a hash-chained ledger line.
Usage: pythonw forward_multi_16b.py           (scheduled, real forward run)
       python  forward_multi_16b.py --test    (technical test: written to test/, NOT the ledger)
"""
import sys
import json
import hashlib
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "pipeline_1d", SRC_DIR / "analytics", SRC_DIR / "execution"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import forward_dryrun_1d as FD
import core_rows_1d as CR
import step15_slow_relative_1d as S15
import step22_pre2020_exam_1d as S22
import step23_4h_brain as S23
import step24_1h_brain as S24
from config import LOGS_DIR

LOG = LOGS_DIR / "forward_multi_16b"
PROTO = LOG / "STEP16B_PROTOCOL_PREREGISTERED.md"
PRED, PAPER, LEDGER, RUNLOG = LOG / "predictions", LOG / "paper", LOG / "ledger.csv", LOG / "run_log.txt"
S16_PRED = FD.PRED
PAPER_START = pd.Timestamp("2026-10-15")            # first as-of day that did not exist when the protocol was locked
F_INVEST, COST, N_HOLD, KEEP = 0.5, 0.00085, 5, 10        # fee amendment 2 (logs/fees, a111c707): true fee; research cost was 0.0025
assert COST == json.loads((Path(__file__).resolve().parents[2] / "deploy" / "fees.json").read_text())["rules"]["paper_spot_per_side"], "fee differs from deploy/fees.json"
U_SIZE, T_SIZE, TRAIN_FIRST = 20, 30, pd.Timestamp("2020-01-01")
SPLIT_SHA = "a16333402ed7d7137cf8ebc667b1cdc66e35e614d3369da065062fe7c960d2d0"


def log(msg):
    line = f"[{pd.Timestamp.now('UTC').strftime('%Y-%m-%d %H:%M:%S')} UTC] {msg}"
    LOG.mkdir(parents=True, exist_ok=True)
    with open(RUNLOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    try:
        print(line, flush=True)
    except Exception:
        pass


def candidates(data_k, data_n):
    """Exactly the research universes: test = reference 30 + half B, train = reference 30 + half A."""
    assert FD.sha_file(S15.SPLIT) == SPLIT_SHA
    split = pd.read_csv(S15.SPLIT)
    A, B = set(split[split.half == "A_design"].symbol), set(split[split.half == "B_confirm"].symbol)
    allc = set(data_k) | set(data_n)
    known = list(data_k)
    return known + sorted(B & allc), known + sorted(A & allc)


def month_model(kind, month, data, last, cand_train, dir_1h, models_dir, asof):
    """R6 / R24 brain for `month`: research recipe, trained on rows whose label was known before the month start."""
    import joblib
    mp = Path(models_dir) / f"{kind}_{month.strftime('%Y-%m')}.joblib"
    if mp.exists():
        return joblib.load(mp), mp
    Utr = S23.daily_members(data, last, cand_train, T_SIZE, TRAIN_FIRST, asof - pd.Timedelta(days=1))
    if kind == "h4_r6":
        btc = S23.bars_4h(Path(dir_1h) / "BTCUSDT_1h_full.csv.gz").close
        R, _, _ = S23.build_rows(dict(train=Utr), Path(dir_1h), btc)
        feats, label, known = S23.FEATS, "label6", "known6"
    else:
        btc = S24.bars_1h(Path(dir_1h) / "BTCUSDT_1h_full.csv.gz").close
        R, _, _ = S24.build_rows(dict(train=Utr), Path(dir_1h), btc, hour_filter=dict(train=lambda hr: hr % 3 == 0))
        feats, label, known = S24.FEATS, "label24", "known24"
    TR = R["train"]
    tr = TR[(TR[known] < month) & TR[label].notna()]
    assert (tr.bar < month).all()
    m = S23.fit(tr[feats].values, tr[label].values.astype(int))
    Path(models_dir).mkdir(parents=True, exist_ok=True)
    joblib.dump(m, mp)
    log(f"trained {kind} for {month.date()} on {len(tr)} rows -> {mp.name}")
    return m, mp


def score_day(asof, dir_1d, dir_1h, models_dir):
    """Members of day asof-1 (top 20 by 30-day USD volume) and their R6 / R24 scores on the bars of day asof."""
    asof = pd.Timestamp(asof)
    month = asof.replace(day=1)
    data_k, last_k, data_n, last_n, _ = CR.load_folder(dir_1d, dir_1h, asof)
    data, last = {**data_k, **data_n}, {**last_k, **last_n}
    cand_test, cand_train = candidates(data_k, data_n)
    d0 = asof - pd.Timedelta(days=1)
    Ute = S23.daily_members(data, last, cand_test, U_SIZE, d0, d0)
    out = {}
    for kind, mod, feats in (("h4_r6", S23, S23.FEATS), ("h1_r24", S24, S24.FEATS)):
        m, mp = month_model(kind, month, data, last, cand_train, dir_1h, models_dir, asof)
        bars = S23.bars_4h if kind == "h4_r6" else S24.bars_1h
        btc = bars(Path(dir_1h) / "BTCUSDT_1h_full.csv.gz").close
        R, _, _ = mod.build_rows(dict(test=Ute), Path(dir_1h), btc)
        T = R["test"]
        T = T[T.bar.dt.normalize() == asof].reset_index(drop=True)
        T["score"] = m.predict_proba(T[feats].values)[:, 1]
        out[kind] = (T, mp)
    return Ute, out, data, last, cand_test


def load_scores(kind, upto, pred_dir=PRED):
    """All logged scores from PAPER_START to `upto`; a missing day is filled with the previous day's scores (protocol)."""
    parts, notes, prev = [], [], None
    for d in pd.date_range(PAPER_START, upto, freq="D"):
        f = Path(pred_dir) / f"{kind}_{d.date()}.csv"
        if f.exists():
            prev = pd.read_csv(f, parse_dates=["bar"] if kind != "d1" else ["date"])
            parts.append(prev)
        elif prev is not None:
            notes.append(f"{kind} {d.date()} missing -> previous day carried")
            col = "date" if kind == "d1" else "bar"
            parts.append(prev.assign(**{col: prev[col] + (d - prev[col].dt.normalize().max())}))
        else:
            notes.append(f"{kind} {d.date()} missing")
    return (pd.concat(parts, ignore_index=True) if parts else None), notes


def paper(asof, data, last, dir_1h, pred_dir=PRED):
    """M_AI3 paper portfolio from PAPER_START to asof with the unchanged research simulators (each sleeve $10k at
    50 % invested; the mix = mean of the three sleeves)."""
    asof = pd.Timestamp(asof)
    if asof == PAPER_START:                        # first decision is taken at the end of PAPER_START: nothing filled yet
        eq = pd.DataFrame(dict(date=[asof], D1=[S22.CAP], H4=[S22.CAP], H1=[S22.CAP]))
        return eq.assign(M_AI3=S22.CAP), pd.DataFrame(), []
    d1, n1 = load_scores("d1", asof, pred_dir)
    h4, n4 = load_scores("h4_r6", asof, pred_dir)
    h1, nh = load_scores("h1_r24", asof, pred_dir)
    eq, pos = paper_from_rows(PAPER_START, asof, d1, h4, h1, data, last, dir_1h)
    return eq, pos, n1 + n4 + nh


def paper_from_rows(start, asof, d1, h4, h1, data, last, dir_1h):
    px1 = {s: data[s].set_index("timestamp")[["open", "low", "close"]] for s in set(d1.symbol)}
    r1 = S22.simulate(d1[["symbol", "date", "score"]], start, asof, px1, last, F_INVEST, N_HOLD, KEEP, cost=COST)
    px4 = {s: S23.bars_4h(Path(dir_1h) / f"{s}_1h_full.csv.gz")[["open", "close"]] for s in h4.symbol.unique()}
    pxh = {s: S24.bars_1h(Path(dir_1h) / f"{s}_1h_full.csv.gz")[["open", "close"]].astype("float64") for s in h1.symbol.unique()}
    S23.START, S23.END_BAR = start, asof + pd.Timedelta(hours=20)
    S24.START, S24.END_BAR = start, asof + pd.Timedelta(hours=23)
    r4 = S23.sim4h(h4[["symbol", "bar", "score"]], 6, px4, COST, invest=F_INVEST)
    rh = S24.sim1h(h1[["symbol", "bar", "score"]], 24, pxh, COST, invest=F_INVEST)

    def day(e):
        e = e[e.index.hour == e.index.hour.max()]
        e.index = e.index.normalize()
        return e

    eq = pd.DataFrame(dict(D1=r1["eq"].set_index("date").equity, H4=day(r4["eq"]), H1=day(rh["eq"])))
    eq["M_AI3"] = eq[["D1", "H4", "H1"]].mean(axis=1)
    eq = eq.rename_axis("date").reset_index()
    pos = []
    for name, r, tcol in (("D1", r1, "entry_date"), ("H4", r4, "entry_time"), ("H1", rh, "entry_time")):
        t = r["trades"]
        if len(t):
            t = t[t.reason == "end_of_test"]
            pos += [dict(sleeve=name, symbol=x.symbol, entry=str(getattr(x, tcol)), cost=x.cost) for x in t.itertuples()]
    finals = dict(D1=float(r1["final"]), H4=float(r4["final"]), H1=float(rh["final"]))
    return eq.assign(**{f"final_{k}": v for k, v in finals.items()}), pd.DataFrame(pos)


def main(test=False):
    now = pd.Timestamp.now("UTC").tz_localize(None)
    asof = now.normalize() - pd.Timedelta(days=1)
    base = LOG / "test" if test else LOG
    pred_dir, paper_dir = (base / "predictions", base / "paper") if test else (PRED, PAPER)
    pred_dir.mkdir(parents=True, exist_ok=True)
    paper_dir.mkdir(parents=True, exist_ok=True)
    f4, f1, fd = (pred_dir / f"{k}_{asof.date()}.csv" for k in ("h4_r6", "h1_r24", "d1"))
    if f4.exists() and f1.exists() and fd.exists():
        log(f"as-of {asof.date()} already logged -> nothing to do")
        return
    if not test:
        assert asof >= PAPER_START, f"as-of {asof.date()} is before PAPER_START"
    log(f"RUN start (test={test}) as-of {asof.date()}")
    s16 = S16_PRED / f"pred_{asof.date()}.csv"
    if not test:
        import time as _t
        for _ in range(90):                                     # after a late wake every task fires at once: wait for Step 16
            if s16.exists():
                break
            _t.sleep(60)
    assert s16.exists(), f"Step 16 prediction file for {asof.date()} not written yet"
    btc1h = pd.read_csv(FD.LIVE1H / "BTCUSDT_1h_full.csv.gz", usecols=["timestamp"], parse_dates=["timestamp"]).timestamp.max()
    assert btc1h >= asof + pd.Timedelta(hours=23), f"BTC last 1h bar {btc1h} < {asof} 23:00 (data not ready)"
    late_data = btc1h > asof + pd.Timedelta(hours=23)          # late run: newer bars exist; every use below is cut at the as-of day

    Ute, sc, data, last, cand_test = score_day(asof, FD.LIVE1D, FD.LIVE1H, FD.MODELS)
    notes = [f"late run: live 1h data reaches {btc1h} (> as-of 23:00); scoring, members and paper are cut at the as-of day"] if late_data else []
    s = pd.read_csv(s16)
    s = s[s.date == str(asof.date())].set_index("symbol")
    Ud = S23.daily_members(data, last, cand_test, U_SIZE, asof, asof)
    miss = sorted(set(Ud.symbol) - set(s.index))
    if miss:
        notes.append(f"d1 members without a Step 16 p_r5: {miss}")
    D1 = Ud[["symbol", "date"]].assign(score=[s.p_r5.get(x, np.nan) for x in Ud.symbol]).dropna(subset=["score"])
    D1.to_csv(fd, index=False)
    for kind, (T, _) in sc.items():
        col = ["symbol", "bar", "score"]
        T[col].sort_values(["bar", "score"], ascending=[True, False]).to_csv(pred_dir / f"{kind}_{asof.date()}.csv", index=False)
        short = sorted(set(Ute.symbol) - set(T[T.bar == T.bar.max()].symbol))
        if short:
            notes.append(f"{kind}: members without the last bar: {short}")
    inp = []
    for x in sorted(Ute.symbol):
        h = pd.read_csv(FD.LIVE1H / f"{x}_1h_full.csv.gz", parse_dates=["timestamp"])
        inp.append(h[h.timestamp.dt.normalize() == asof].assign(symbol=x))
    inputs = pd.concat(inp, ignore_index=True)
    inp_file = pred_dir / f"inputs_1h_{asof.date()}.csv"
    inputs.to_csv(inp_file, index=False)

    if test and asof < PAPER_START:
        eq, pos, pn = pd.DataFrame(dict(date=[asof], M_AI3=[np.nan])), pd.DataFrame(), ["test before PAPER_START: no paper"]
    else:
        eq, pos, pn = paper(asof, data, last, FD.LIVE1H, pred_dir)
    notes += pn
    eq_file, pos_file = paper_dir / f"equity_{asof.date()}.csv", paper_dir / f"positions_{asof.date()}.csv"
    eq.to_csv(eq_file, index=False)
    pos.to_csv(pos_file, index=False)

    written = pd.Timestamp.now("UTC").tz_localize(None)
    last_eq = eq.iloc[-1]
    line = dict(run_utc=str(now), written_utc=str(written), asof=str(asof.date()), test=test,
                on_time=bool(written <= asof + pd.Timedelta(days=1, hours=3)),
                n_members=len(Ute), n_h4_rows=len(sc["h4_r6"][0]), n_h1_rows=len(sc["h1_r24"][0]), n_d1=len(D1),
                h4_sha256=FD.sha_file(f4), h1_sha256=FD.sha_file(f1), d1_sha256=FD.sha_file(fd), inputs_sha256=FD.sha_file(inp_file),
                step16_pred_sha256=FD.sha_file(s16), model_h4=sc["h4_r6"][1].name, model_h4_sha256=FD.sha_file(sc["h4_r6"][1]),
                model_h1=sc["h1_r24"][1].name, model_h1_sha256=FD.sha_file(sc["h1_r24"][1]),
                paper_M_AI3=round(float(last_eq.get("M_AI3", np.nan)), 2), paper_equity_sha256=FD.sha_file(eq_file),
                code_sha256=FD.sha_file(__file__), s22_sha256=FD.sha_file(S22.__file__), s23_sha256=FD.sha_file(S23.__file__),
                s24_sha256=FD.sha_file(S24.__file__), protocol_sha256=FD.sha_file(PROTO), notes=json.dumps(notes)[:2000])
    led = base / "ledger_test.csv" if test else LEDGER
    line["prev_sha256"] = pd.read_csv(led).line_sha256.iloc[-1] if led.exists() else "GENESIS"
    line["line_sha256"] = FD.sha_bytes(json.dumps(line, sort_keys=True).encode())
    pd.DataFrame([line]).to_csv(led, mode="a", index=False, header=not led.exists())
    log(f"RUN done as-of {asof.date()}: {len(Ute)} members, paper M_AI3 {line['paper_M_AI3']} (on_time={line['on_time']}), notes {len(notes)}")


if __name__ == "__main__":
    try:
        main(test="--test" in sys.argv)
    except Exception:
        log("RUN FAILED:\n" + traceback.format_exc())
        sys.exit(1)
