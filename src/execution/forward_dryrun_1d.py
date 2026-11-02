"""
Step 16 forward dry-run logger (protocol: logs/strategy_1d_step16_forward/STEP16_PROTOCOL_PREREGISTERED.md).
NO ORDERS. Every run: update live data (Binance public REST, closed candles only) -> build the Step 13 core rows
as of the last closed UTC day -> load/train the month's B1 model -> log a score for every liquid coin -> append a
hash-chained ledger line.
Usage: pythonw forward_dryrun_1d.py            (scheduled, real forward run)
       python  forward_dryrun_1d.py --test     (technical test: as-of yesterday, written to test/, NOT the ledger)
"""
import sys
import csv
import gzip
import json
import time
import shutil
import hashlib
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
import requests

SRC_DIR = Path(__file__).resolve().parent.parent
for p in (SRC_DIR, SRC_DIR / "pipeline_1d", SRC_DIR / "analytics"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import core_rows_1d as CR
import step15_slow_relative_1d as S15
import step11_ai_confident_1d as S11
import step13_unseen_coins_1d as S13
from config import DATA_DIR, LOGS_DIR

FWD = DATA_DIR / "forward"
LIVE1D, LIVE1H, RAW, MODELS = FWD / "live_1d", FWD / "live_1h", FWD / "rest_raw", FWD / "models"
LOG = LOGS_DIR / "strategy_1d_step16_forward"
PRED, LEDGER, RUNLOG = LOG / "predictions", LOG / "ledger.csv", LOG / "run_log.txt"
REST = "https://api.binance.com/api/v3/klines"
FNG_URL = "https://api.alternative.me/fng/"
FNG_LOCK_LAST = pd.Timestamp("2026-10-12")          # dates <= this come from the SHA-locked research file
COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "trades",
        "taker_buy_base", "taker_buy_quote", "ignore"]
KEEP = ["timestamp", "open", "high", "low", "close", "volume", "quote_volume", "trades", "taker_buy_base", "taker_buy_quote"]
SESSION = requests.Session()


def log(msg):
    line = f"[{pd.Timestamp.now('UTC').strftime('%Y-%m-%d %H:%M:%S')} UTC] {msg}"
    LOG.mkdir(parents=True, exist_ok=True)
    with open(RUNLOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    try:
        print(line, flush=True)
    except Exception:
        pass


def safe_replace(tmp, dst):
    """os.replace with retries: Windows can briefly lock a just-written file (antivirus / indexer)."""
    for k in range(20):
        try:
            tmp.replace(dst)
            return
        except PermissionError:
            time.sleep(0.5 * (k + 1))
    tmp.replace(dst)


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(p):
    return sha_bytes(Path(p).read_bytes())


def get(url, params):
    err = None
    for k in range(8):
        try:
            r = SESSION.get(url, params=params, timeout=30)
            if r.status_code == 200 or r.status_code == 400:
                return r
            err = f"HTTP {r.status_code}"
            if r.status_code in (418, 429):
                time.sleep(60)
        except requests.RequestException as e:
            err = str(e)
        time.sleep(3 * (k + 1))
    raise RuntimeError(f"{url} {params}: {err}")


# ----------------------------------------------------------------------------------------------
# Live data
# ----------------------------------------------------------------------------------------------
def init_live():
    if (FWD / "INIT_DONE.json").exists():
        return
    for src, dst in ((S13.UNI / "1d", LIVE1D), (S13.UNI / "1h", LIVE1H)):
        dst.mkdir(parents=True, exist_ok=True)
        for f in src.iterdir():
            shutil.copy2(f, dst / f.name)
    info = dict(time_utc=str(pd.Timestamp.now("UTC")), files_1d=len(list(LIVE1D.iterdir())), files_1h=len(list(LIVE1H.iterdir())),
                source="data/universe_all (Binance Vision, SHA256-verified, up to 2026-09-30)")
    (FWD / "INIT_DONE.json").write_text(json.dumps(info, indent=1))
    log(f"live folders initialised: {info}")


def fetch(sym, interval, start_ms, now_ms):
    out = []
    while start_ms < now_ms:
        r = get(REST, dict(symbol=sym, interval=interval, startTime=int(start_ms), limit=1000))
        if r.status_code == 400:                        # symbol no longer exists on Binance
            return out, r.text
        rows = r.json()
        if not rows:
            break
        out += rows
        start_ms = rows[-1][0] + 1
        if len(rows) < 1000:
            break
    return [x for x in out if x[6] < now_ms], None   # closed candles only


def to_df(rows):
    df = pd.DataFrame(rows, columns=COLS)
    df["timestamp"] = pd.to_datetime(df.open_time.astype("int64"), unit="ms")
    for c in KEEP[1:]:
        df[c] = pd.to_numeric(df[c], errors="raise")
    return df[KEEP]


def update_live(now):
    now_ms = int(now.timestamp() * 1000)
    raw, notes = {}, {}
    files = sorted(LIVE1D.glob("*_1d.csv"))
    for k, f in enumerate(files):
        s = f.name.split("_")[0]
        d1 = pd.read_csv(f, parse_dates=["timestamp"])
        last = d1.timestamp.max()
        if last < pd.Timestamp("2026-09-29"):            # ended before the forward period: nothing to fetch
            continue
        rows, err = fetch(s, "1d", (last + pd.Timedelta(days=1)).timestamp() * 1000, now_ms)
        raw[f"{s}_1d"] = rows
        if err:
            notes[s] = f"1d: {err[:80]}"
        if rows:
            new = to_df(rows)
            new = new[new.timestamp > last]
            exp = pd.date_range(last + pd.Timedelta(days=1), periods=len(new), freq="D")
            if len(new) and not (new.timestamp.values == exp.values).all():   # missing day -> keep only the run before it
                gap = int(np.argmax(new.timestamp.values != exp.values))
                notes[s] = f"1d gap after {new.timestamp.iloc[gap - 1] if gap else last}: kept {gap} new days"
                new = new.iloc[:gap]
            if len(new):
                out = pd.concat([d1, new], ignore_index=True)
                tmp = f.with_suffix(".tmp")
                out.assign(timestamp=out.timestamp.dt.strftime("%Y-%m-%d")).to_csv(tmp, index=False)
                safe_replace(tmp, f)
        hf = LIVE1H / f"{s}_1h_full.csv.gz"
        if hf.exists():
            h = pd.read_csv(hf, parse_dates=["timestamp"])
            hl = h.timestamp.max()
            rows, err = fetch(s, "1h", (hl + pd.Timedelta(hours=1)).timestamp() * 1000, now_ms)
            raw[f"{s}_1h"] = rows
            if rows:
                new = to_df(rows)
                new = new[new.timestamp > hl]
                if len(new):
                    out = pd.concat([h, new], ignore_index=True)
                    tmp = hf.with_suffix(".tmp")
                    out.to_csv(tmp, index=False, compression="gzip")
                    safe_replace(tmp, hf)
        if k % 100 == 0:
            log(f"update {k + 1}/{len(files)} {s}")
    return raw, notes


def fit_r5(Pk, Pn, data_k, last_k, data_n, last_n, F, month, asof):
    """Step 15 R5 brain for the month (exact research recipe: 30 reference coins + eligible A-half coins)."""
    from sklearn.ensemble import HistGradientBoostingClassifier
    S15.ASOF = pd.Timestamp(asof)
    split = pd.read_csv(S15.SPLIT)
    A = set(split[split.half == "A_design"].symbol)
    Pa = Pn[Pn.eligible & Pn.symbol.isin(A)].copy()
    Pk = Pk.copy()
    Pk["fwd_r5"], Pk["known_r5"] = S15.add_relative(Pk, data_k, last_k, 5)
    Pa["fwd_r5"], Pa["known_r5"] = S15.add_relative(Pa, {s: data_n[s] for s in A if s in data_n}, last_n, 5)
    med = Pk.dropna(subset=["fwd_r5"]).groupby("date").fwd_r5.median()
    for P in (Pk, Pa):
        rel = P.fwd_r5 - P.date.map(med)
        P["label_r5"] = np.where(rel.isna(), np.nan, (rel > 0).astype(float))
    train = pd.concat([Pk, Pa]).reset_index(drop=True)
    T = pd.Timestamp(month)
    tr = train[(train.known_r5 < T) & train.label_r5.notna()]
    assert (tr.date < T).all()
    m = HistGradientBoostingClassifier(random_state=0, **S11.KW).fit(tr[F].values, tr.label_r5.values.astype(int))
    return m, len(tr)


def read_ledger(path):
    """Ledger lines as a DataFrame. The append-only file keeps its original 19-column header; lines written after the
    2026-10-14 on_time fix carry one more field (written_utc, 2nd position). Rows are mapped by their field count."""
    with open(path, newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.reader(fh) if r]
    head = rows[0]
    new = head[:1] + ["written_utc"] + head[1:] if "written_utc" not in head else head
    out = []
    for r in rows[1:]:
        cols = head if len(r) == len(head) else new if len(r) == len(new) else None
        assert cols is not None, f"ledger line with {len(r)} fields"
        out.append(dict(zip(cols, r)))
    return pd.DataFrame(out)


def fng_table_live(now):
    r = get(FNG_URL, dict(limit=0, format="json"))
    blob = r.content
    d = pd.DataFrame(json.loads(blob)["data"])
    d["date"] = pd.to_datetime(d.timestamp.astype("int64"), unit="s").dt.normalize()
    new = d.set_index("date").value.astype(float).sort_index()
    lock_raw = json.loads(S11.FNG_FILE.read_bytes())
    assert sha_bytes(S11.FNG_FILE.read_bytes()) == S11.FNG_SHA
    ld = pd.DataFrame(lock_raw["data"])
    ld["date"] = pd.to_datetime(ld.timestamp, format="%d-%m-%Y")
    old = ld.set_index("date").value.astype(float).sort_index()
    s = pd.concat([old[old.index <= FNG_LOCK_LAST], new[new.index > FNG_LOCK_LAST]]).sort_index()
    s = s[~s.index.duplicated()]
    s = s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="D"))
    overlap = old.index.intersection(new.index)
    diff = int((old.loc[overlap] != new.loc[overlap]).sum())
    return pd.DataFrame(dict(fng=s, fng_chg7=s - s.shift(7),
                             fng_z30=(s - s.rolling(30, min_periods=20).mean()) / s.rolling(30, min_periods=20).std())), blob, diff


# ----------------------------------------------------------------------------------------------
def main(test=False):
    import joblib
    now = pd.Timestamp.now("UTC").tz_localize(None)
    asof = now.normalize() - pd.Timedelta(days=1)
    out_dir = LOG / "test" if test else PRED
    out_dir.mkdir(parents=True, exist_ok=True)
    pred_file = out_dir / f"pred_{asof.date()}.csv"
    if pred_file.exists():
        log(f"as-of {asof.date()} already logged -> nothing to do")
        return
    log(f"RUN start (test={test}) as-of {asof.date()}")
    init_live()
    raw, notes = update_live(now)
    RAW.mkdir(parents=True, exist_ok=True)
    raw_bytes = gzip.compress(json.dumps(raw).encode())
    raw_path = RAW / f"rest_{now.strftime('%Y%m%dT%H%M%S')}.json.gz"
    raw_path.write_bytes(raw_bytes)
    btc = pd.read_csv(LIVE1D / "BTCUSDT_1d.csv", parse_dates=["timestamp"])
    assert btc.timestamp.max() == asof, f"BTC last closed day {btc.timestamp.max()} != as-of {asof} (data not ready)"
    fng, fng_blob, fng_diff = fng_table_live(now)
    (RAW / f"fng_{now.strftime('%Y%m%dT%H%M%S')}.json").write_bytes(fng_blob)
    data_k, last_k, data_n, last_n, sel = CR.load_folder(LIVE1D, LIVE1H, asof)
    Pk, Pn, F = CR.build(data_k, last_k, data_n, last_n, LIVE1H, LIVE1H, asof, fng)
    assert Pk.date.max() <= asof and Pn.date.max() <= asof
    month = asof.replace(day=1)
    MODELS.mkdir(parents=True, exist_ok=True)
    mp = MODELS / f"b1_{month.strftime('%Y-%m')}.joblib"
    if not mp.exists():
        m, ntr = CR.fit_b1(Pk, F, month)
        joblib.dump(m, mp)
        log(f"trained B1 for {month.date()} on {ntr} rows -> {mp.name}")
    m = joblib.load(mp)
    Pn["eligible"] = Pn.liquid & (Pn.idx + 1 >= S15.MIN_HIST)
    Pk["eligible"] = Pk.liquid & (Pk.idx + 1 >= S15.MIN_HIST)
    mp5 = MODELS / f"r5_{month.strftime('%Y-%m')}.joblib"
    if not mp5.exists():
        m5, ntr5 = fit_r5(Pk, Pn, data_k, last_k, data_n, last_n, F, month, asof)
        joblib.dump(m5, mp5)
        log(f"trained R5 for {month.date()} on {ntr5} rows -> {mp5.name}")
    m5 = joblib.load(mp5)
    rows = pd.concat([Pk[(Pk.date == asof) & Pk.liquid].assign(known=True), Pn[(Pn.date == asof) & Pn.liquid].assign(known=False)])
    rows["p1"] = m.predict_proba(rows[F].values)[:, 1]
    rows["p_r5"] = m5.predict_proba(rows[F].values)[:, 1]
    rows[["symbol", "date", "known", "eligible", "p1", "p_r5"]].sort_values("p1", ascending=False).to_csv(pred_file, index=False)
    written = pd.Timestamp.now("UTC").tz_localize(None)            # the moment the prediction file exists
    line = dict(run_utc=str(now), written_utc=str(written), asof=str(asof.date()), test=test, n_coins=len(rows),
                on_time=bool(written <= asof + pd.Timedelta(days=1, hours=3)),
                pred_sha256=sha_file(pred_file), rest_raw_sha256=sha_bytes(raw_bytes), fng_raw_sha256=sha_bytes(fng_blob),
                fng_hist_diff_vs_lock=fng_diff, model_file=mp.name, model_sha256=sha_file(mp), model_r5_file=mp5.name, model_r5_sha256=sha_file(mp5),
                code_sha256=sha_file(__file__), core_sha256=sha_file(CR.__file__),
                protocol_sha256=sha_file(LOG / "STEP16_PROTOCOL_PREREGISTERED.md"), notes=json.dumps(notes)[:2000])
    led = LOG / "test" / "ledger_test.csv" if test else LEDGER
    prev = read_ledger(led).line_sha256.iloc[-1] if led.exists() else "GENESIS"
    line["prev_sha256"] = prev
    line["line_sha256"] = sha_bytes(json.dumps(line, sort_keys=True).encode())
    pd.DataFrame([line]).to_csv(led, mode="a", index=False, header=not led.exists())
    log(f"RUN done: {len(rows)} coins logged for {asof.date()} (on_time={line['on_time']}), notes {len(notes)}")


if __name__ == "__main__":
    try:
        main(test="--test" in sys.argv)
    except Exception:
        log("RUN FAILED:\n" + traceback.format_exc())
        sys.exit(1)
