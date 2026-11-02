"""FWD-WATCH (logs/fwd_watch/FWD_WATCH_PROTOCOL_PREREGISTERED.md): forward PAPER tracking of FW1 (bench ConnorsRSI follow 4h X3)
and FW2 (NP3 4h|NODEPTH|RIDGE|0.9|XM) on data from 2026-10-01. No orders. Public data only.
The rule code below is a verbatim copy of the research definitions; identity checks reproduce the stored research trades exactly
before any forward number is written (protocol §2, §3).
Usage: python src/forward/fwd_watch.py [--no-fetch] [--root data/fwd_watch]"""
import argparse
import csv
import hashlib
import io
import json
import re
import time
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

PROJ = Path(__file__).resolve().parents[2]
FEES = json.loads((PROJ / "deploy/fees.json").read_text(encoding="utf-8"))
FUT_RT = 2 * FEES["rules"]["paper_futures_taker_per_side"]
MAKER = FEES["futures_usdm"]["bnb_maker"]
TAKER = FEES["rules"]["paper_futures_taker_per_side"]
FWD0 = pd.Timestamp("2026-10-01")
SEED_END = pd.Timestamp("2026-09-30 23:55")
CAP = 2016
BETA = np.array([-8.449163524227228e-05, -0.00039878595881818915, -0.00011428329656457703])
THR = 0.00021482419836031948
LIST = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?prefix={p}&marker={m}"
DAILY = {"spot": "data/spot/daily/klines/BTCUSDT/5m/", "fut": "data/futures/um/daily/klines/BTCUSDT/5m/", "metrics": "data/futures/um/daily/metrics/BTCUSDT/"}
KL = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore"]
M5 = pd.Timedelta(minutes=5)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def get(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except Exception:                      # noqa: BLE001  (network retry)
            if i == tries - 1:
                raise
            time.sleep(3 * (i + 1))


# ------------------------------------------------------------------ store
def fetch(root, log):
    for ds, pre in DAILY.items():
        out = root / "daily" / ds
        out.mkdir(parents=True, exist_ok=True)
        mf = out / "MANIFEST.csv"
        have = {r["key"]: r for r in csv.DictReader(open(mf, encoding="utf-8"))} if mf.exists() else {}
        keys, marker = [], pre + "BTCUSDT-" + ("metrics-" if ds == "metrics" else "5m-") + "2026-09-30"
        while True:
            x = get(LIST.format(p=pre, m=marker)).decode()
            ks = re.findall(r"<Key>([^<]+)</Key>", x)
            keys += [k for k in ks if k.endswith(".zip")]
            if "<IsTruncated>true" not in x or not ks:
                break
            marker = ks[-1]
        new = 0
        for k in sorted(keys):
            if k in have and have[k]["checksum_ok"] == "True" and (out / k.rsplit("/", 1)[1]).exists():
                continue
            want = get("https://data.binance.vision/" + k + ".CHECKSUM").decode().split()[0]
            data = get("https://data.binance.vision/" + k)
            ok = sha(data) == want
            if ok:
                (out / k.rsplit("/", 1)[1]).write_bytes(data)
                new += 1
            have[k] = dict(key=k, bytes=len(data), sha256=sha(data), checksum_ok=str(ok), checked_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        with open(mf, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["key", "bytes", "sha256", "checksum_ok", "checked_utc"])
            w.writeheader()
            for k in sorted(have):
                w.writerow(have[k])
        bad = [k for k, r in have.items() if r["checksum_ok"] != "True"]
        log(f"fetch {ds}: listed {len(keys)}, new {new}, checksum fails {bad}")
    fr = json.loads(get("https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&startTime=1788220800000&limit=1000"))
    (root / "funding_api.json").write_text(json.dumps(fr), encoding="utf-8")
    log(f"fetch funding API: {len(fr)} rows, last {fr[-1]['fundingTime'] if fr else None}")


def read_zip(f, names=None):
    z = zipfile.ZipFile(f)
    raw = z.read(z.namelist()[0]).decode()
    hdr = not raw[:1].isdigit()
    df = pd.read_csv(io.StringIO(raw), header=0 if hdr else None)
    if names is not None and not hdr:
        df.columns = names
    return df


def to_time(v):
    v = pd.to_numeric(v)
    return pd.to_datetime(v, unit="us" if v.max() > 10 ** 14 else "ms")


def daily_frames(root, ds):
    fs = sorted((root / "daily" / ds).glob("*.zip"))
    return [read_zip(f, None if ds == "metrics" else KL) for f in fs]


def load_spot(root):
    s = pd.read_csv(root / "seed/spot5m_seed.csv.gz", parse_dates=["timestamp"]).drop_duplicates("timestamp").set_index("timestamp").sort_index()
    s = s.loc[:SEED_END, ["open", "high", "low", "close", "volume", "taker_buy_base"]]
    add = []
    for df in daily_frames(root, "spot"):
        df["timestamp"] = to_time(df.open_time)
        add.append(df.set_index("timestamp")[["open", "high", "low", "close", "volume", "taker_buy_volume"]].rename(columns={"taker_buy_volume": "taker_buy_base"}))
    if add:
        a = pd.concat(add)
        s = pd.concat([s, a[a.index > SEED_END]])
    s.index = s.index.as_unit("ns")
    return s[~s.index.duplicated()].sort_index()


def load_fut(root):
    f = pd.read_parquet(root / "seed/fut5m_seed.parquet")
    f = f[f.time <= SEED_END][["time", "open", "high", "low", "close", "volume", "taker_buy_volume"]]
    add = []
    for df in daily_frames(root, "fut"):
        df["time"] = to_time(df.open_time)
        add.append(df[["time", "open", "high", "low", "close", "volume", "taker_buy_volume"]])
    if add:
        a = pd.concat(add)
        f = pd.concat([f, a[a.time > SEED_END]])
    f["time"] = f.time.dt.as_unit("ns")
    return f.drop_duplicates("time").sort_values("time").reset_index(drop=True)


def load_metrics(root):
    m = pd.read_parquet(root / "seed/metrics5m_seed.parquet")
    m = m[m.time <= SEED_END][["time", "sum_open_interest_value"]]
    add = []
    for df in daily_frames(root, "metrics"):
        df["time"] = pd.to_datetime(df.create_time)
        df["sum_open_interest_value"] = pd.to_numeric(df.sum_open_interest_value, errors="coerce")
        add.append(df[["time", "sum_open_interest_value"]])
    if add:
        a = pd.concat(add)
        m = pd.concat([m, a[a.time > SEED_END]])
    m["time"] = m.time.dt.as_unit("ns")
    return m.drop_duplicates("time").sort_values("time").reset_index(drop=True)


def load_funding(root):
    f = pd.read_parquet(root / "seed/funding_seed.parquet")[["time", "funding_rate"]]
    api = root / "funding_api.json"
    if api.exists():
        a = pd.DataFrame(json.loads(api.read_text(encoding="utf-8")))
        if len(a):
            a = pd.DataFrame({"time": pd.to_datetime(a.fundingTime.astype("int64"), unit="ms"), "funding_rate": a.fundingRate.astype(float)})
            f = pd.concat([f, a[a.time > f.time.max()]])
    f["time"] = f.time.dt.as_unit("ns")
    return f.drop_duplicates("time").sort_values("time").reset_index(drop=True)


# ------------------------------------------------------------------ FW1 (verbatim from src/research/methods_bench.py / btc_entry_study.py)
def agg(d, rule):
    a = d.resample(rule, label="right", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last",
                                                             "volume": "sum", "taker_buy_base": "sum"})
    return a.dropna(subset=["open", "high", "low", "close"])


def to5m(x, d):
    x = pd.Series(x)
    return x.reindex(d.index + pd.Timedelta(minutes=5), method="ffill").set_axis(d.index).values


def wilder(s, n):
    return s.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def rsi(c, n=14):
    dl = c.diff()
    au, ad = wilder(dl.clip(lower=0), n), wilder((-dl).clip(lower=0), n)
    return 100 - 100 / (1 + au / ad)


def connors(c):
    st = np.zeros(len(c)); dc = c.diff().values
    for i in range(1, len(c)):
        st[i] = (st[i - 1] + 1 if st[i - 1] > 0 else 1) if dc[i] > 0 else ((st[i - 1] - 1 if st[i - 1] < 0 else -1) if dc[i] < 0 else 0)
    roc = c.pct_change()
    pr = roc.rolling(100).apply(lambda x: (x[:-1] < x[-1]).mean() * 100, raw=True)
    return (rsi(c, 3) + rsi(pd.Series(st, index=c.index), 2) + pr) / 3


def cum_funding(d, fu):
    fu = fu.set_index("time").funding_rate.astype(float).sort_index()
    fu = fu[~fu.index.duplicated()]
    close_t = d.index + pd.Timedelta(minutes=5)
    cs = np.r_[0.0, np.cumsum(fu.values)]
    return cs[np.searchsorted(fu.index.values, close_t.values, side="left")]


def sim_reversal(dirn, d, cost, cum_f, rng_):
    i0, i1 = rng_
    O, C = d.open.values, pd.Series(d.close.values).ffill().values
    N = len(O)
    nxt = {}
    for s in (1, -1):
        idx = np.where(dirn == s, np.arange(N), N)
        nxt[s] = np.minimum.accumulate(idx[::-1])[::-1]
    out = []
    free = i0
    for t in np.flatnonzero(dirn[i0:i1] != 0) + i0:
        if t < free:
            continue
        dd = int(dirn[t])
        e = O[t + 1] if t + 1 < N else np.nan
        if not np.isfinite(e):
            continue
        k = nxt[-dd][t + 1] if t + 1 < N else N
        if k < N and k <= t + CAP:
            xbar = k + 1 if k + 1 < N else k
            px = O[xbar] if np.isfinite(O[xbar]) else C[k]
            ex = k
            closed = k + 1 < N
        else:
            ex = min(N - 1, t + CAP); px = C[ex]
            closed = t + CAP <= N - 1
        g = dd * (px / e - 1)
        fund = (cum_f[ex] - cum_f[t]) * dd
        out.append(dict(t=int(t), dir=dd, gross=g, net=g - cost - fund, exit=int(ex), closed=bool(closed)))
        free = ex
    return out


def fw1(spot, fund, start):
    d = spot.reindex(pd.date_range("2020-01-01", spot.index.max(), freq="5min").as_unit("ns"))
    a = agg(d, "4h")
    crsi = connors(a.close)
    fade = np.where(crsi < 10, 1, np.where(crsi > 90, -1, 0))
    s5 = np.nan_to_num(to5m(pd.Series(fade, index=a.index), d)).astype(np.int8)
    dirn = (-s5).astype(np.int8)
    cum_f = cum_funding(d, fund)
    i0 = int(d.index.searchsorted(start))
    tr = sim_reversal(dirn, d, FUT_RT, cum_f, (i0, len(d) - 1))
    for r in tr:
        r["time"] = d.index[r["t"]]
        r["exit_time"] = d.index[r["exit"]]
    return tr, d


# ------------------------------------------------------------------ FW2 (NP1 features, NP1 S2 percentile, NP2 ridge, NP3 XM execution)
def trailing_pct(t, x, days=90, min_past=30):
    import bisect
    out = np.full(len(x), np.nan)
    win, j = [], 0
    for i in range(len(x)):
        while j < i and t[j] < t[i] - np.timedelta64(days, "D"):
            win.pop(bisect.bisect_left(win, x[j])); j += 1
        if len(win) >= min_past:
            out[i] = bisect.bisect_left(win, x[i]) / len(win)
        bisect.insort(win, x[i])
    return out


def fw2_features(fut, spot, met, end):
    t0 = pd.Timestamp("2020-07-01")
    T = pd.date_range("2020-09-01", end, freq="1h").as_unit("ns")
    T = T[T.hour % 4 == 0]
    g = fut.set_index("time")[["close"]].reindex(pd.date_range(t0, fut.time.max(), freq="5min").as_unit("ns"))
    g.index = g.index + M5
    fc = g.close
    sp = spot[["volume", "taker_buy_base"]].reindex(pd.date_range(t0, spot.index.max(), freq="5min").as_unit("ns"))
    sp.index = sp.index + M5
    mt = met.copy()
    mt["avail"] = (mt.time + M5).dt.as_unit("ns")

    def m_at(times):
        return pd.merge_asof(pd.DataFrame({"t": times}), mt[["avail", "sum_open_interest_value"]].rename(columns={"avail": "t"}), on="t", direction="backward")
    oi = m_at(T).sum_open_interest_value.to_numpy()
    oi24 = m_at(T - pd.Timedelta(hours=24)).sum_open_interest_value.to_numpy()
    X = pd.DataFrame(index=T)
    X["px"] = fc.reindex(T).to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        X["OI_CHG_24H"] = np.log(oi / oi24)
    X["SPOT_TAKER_1H"] = (sp.taker_buy_base.rolling(12, min_periods=12).sum() / sp.volume.rolling(12, min_periods=12).sum()).reindex(T).to_numpy() - 0.5
    X["CTRL_RET_24H"] = X.px / fc.reindex(T - pd.Timedelta(hours=24)).to_numpy() - 1
    return X.replace([np.inf, -np.inf], np.nan)


def fw2(fut, spot, met, end, t_from, t_to):
    X = fw2_features(fut, spot, met, end)
    feats = ["OI_CHG_24H", "SPOT_TAKER_1H", "CTRL_RET_24H"]
    cols = {}
    for f in feats:
        d = X[[f]].dropna()
        cols[f] = pd.Series(trailing_pct(d.index.to_numpy(), d[f].to_numpy()), index=d.index)
    U = pd.DataFrame(cols).dropna() - 0.5
    U = U[(U.index >= t_from) & (U.index < t_to)]
    pred = U[feats].to_numpy() @ BETA
    side = np.where(np.abs(pred) >= THR, np.sign(pred), 0)
    f5 = fut.set_index("time")
    full = pd.date_range(f5.index.min(), f5.index.max(), freq="5min").as_unit("ns")
    f5 = f5.reindex(full)
    H, L, C = f5.high.to_numpy(), f5.low.to_numpy(), f5.close.to_numpy()
    t00 = full[0]
    ix = lambda t: int((t - t00) / M5)
    out = []
    for t, sd in zip(U.index[side != 0], side[side != 0]):
        it = ix(t)
        ie = ix(t + pd.Timedelta(hours=4))
        if ie + 2 >= len(C):
            out.append(dict(t=t, side=int(sd), closed=False))
            continue
        P = C[it - 1]
        k = [j for j in range(it, it + 3) if (L[j] < P if sd > 0 else H[j] > P)]
        if not k:
            continue
        Q = C[ie - 1]
        kk = [j for j in range(ie, ie + 3) if (H[j] > Q if sd > 0 else L[j] < Q)]
        x, xc = (Q, MAKER) if kk else (C[ie + 2], TAKER)
        g = sd * (x / P - 1)
        out.append(dict(t=t, side=int(sd), entry=P, exit=x, gross=g * 100, net=(g - MAKER - xc) * 100, closed=True))
    return out


# ------------------------------------------------------------------ identity checks (protocol §2, §3)
def identity(spot, fut, met, fund):
    tr, _ = fw1(spot[spot.index <= SEED_END], fund[fund.time <= SEED_END + pd.Timedelta(hours=1)], pd.Timestamp("2025-01-01"))
    ref = pd.read_csv(PROJ / "logs/research_methods_bench/batch1_H_trades_A2.01b_ConnorsRSI_follow_4h_X3.csv")
    ok1 = len(tr) == len(ref) and all(a["t"] == b.t and a["dir"] == b.dir and abs(a["gross"] - b.gross) < 1e-12 and abs(a["net"] - b.net) < 1e-12
                                      and a["exit"] == b.exit for a, b in zip(tr, ref.itertuples()))
    m2 = fw2(fut[fut.time <= SEED_END], spot[spot.index <= SEED_END], met[met.time <= SEED_END], pd.Timestamp("2024-12-31 23:00"),
             pd.Timestamp("2020-09-01"), pd.Timestamp("2025-01-01"))
    ref2 = pd.read_parquet(PROJ / "logs/research_nonprice/np3_dv_trades.parquet")
    ref2 = ref2[ref2.cfg == "4h|NODEPTH|RIDGE|0.9|XM"]
    m2 = [r for r in m2 if r["closed"]]
    ok2 = len(m2) == len(ref2) and all(a["t"] == b.t and a["side"] == b.side and abs(a["entry"] - b.entry) < 1e-9 and abs(a["exit"] - b.exit) < 1e-9
                                       and abs(a["net"] - b.net) < 1e-9 for a, b in zip(m2, ref2.itertuples()))
    return ok1, len(tr), len(ref), ok2, len(m2), len(ref2)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/fwd_watch")
    ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--selftest", action="store_true", help="identity checks only")
    a = ap.parse_args()
    root = PROJ / a.root
    (root / "out").mkdir(parents=True, exist_ok=True)

    def log(msg):
        line = f"{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ} {msg}"
        print(line, flush=True)
        with open(root / "out" / "run_log.txt", "a", encoding="utf-8") as f:
            f.write(line + "\n")

    log(f"fwd_watch start; code {sha(Path(__file__).read_bytes())[:12]}; protocol "
        f"{sha((PROJ / 'logs/fwd_watch/FWD_WATCH_PROTOCOL_PREREGISTERED.md').read_bytes())[:12]}")
    if not a.no_fetch and not a.selftest:
        fetch(root, log)
    spot, fut, met, fund = load_spot(root), load_fut(root), load_metrics(root), load_funding(root)
    log(f"data: spot to {spot.index.max()}, fut to {fut.time.max()}, metrics to {met.time.max()}, funding to {fund.time.max()}")
    ok1, n1, r1, ok2, n2, r2 = identity(spot, fut, met, fund)
    log(f"identity FW1 {ok1} ({n1} vs {r1} bench H trades); FW2 {ok2} ({n2} vs {r2} NP3 DV trades)")
    status = dict(run_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), identity_fw1=ok1, identity_fw2=ok2,
                  data_end=dict(spot=str(spot.index.max()), fut=str(fut.time.max()), metrics=str(met.time.max()), funding=str(fund.time.max())))
    if a.selftest:
        print(json.dumps(status))
        return 0 if (ok1 and ok2) else 1
    rows = []
    if ok1:
        tr, _ = fw1(spot, fund, FWD0)
        rows += [dict(cand="FW1", time=r["time"], side=r["dir"], net_pct=r["net"] * 100, gross_pct=r["gross"] * 100, exit_time=r["exit_time"], closed=r["closed"]) for r in tr]
    if ok2:
        end = min(fut.time.max(), spot.index.max()).floor("1h")
        for r in fw2(fut, spot, met, end, FWD0, end + pd.Timedelta(hours=1)):
            rows.append(dict(cand="FW2", time=r["t"], side=r["side"], net_pct=r.get("net"), gross_pct=r.get("gross"),
                             exit_time=r["t"] + pd.Timedelta(hours=4) if r["closed"] else None, closed=r["closed"]))
    T = pd.DataFrame(rows, columns=["cand", "time", "side", "net_pct", "gross_pct", "exit_time", "closed"])
    T.to_csv(root / "out/fw_trades_all.csv", index=False)
    C = T[T.closed]
    C.to_csv(root / "out/fw_trades.csv", index=False)
    last_day = min(spot.index.max(), fut.time.max()).normalize()
    days = pd.DataFrame({"date": pd.date_range(FWD0, last_day, freq="D")})
    daily, monthly, summ = [], [], {}
    for cand in ("FW1", "FW2"):
        g = C[C.cand == cand]
        dd = days.merge(g.assign(date=pd.to_datetime(g.exit_time).dt.normalize()).groupby("date").net_pct.sum().reset_index(), on="date", how="left").fillna({"net_pct": 0.0})
        dd["cand"] = cand
        daily.append(dd)
        mo = dd.groupby(dd.date.dt.to_period("M")).net_pct.sum()
        monthly.append(mo.rename("net_pct").reset_index().assign(cand=cand))
        summ[cand] = dict(closed_trades=len(g), open_trades=int(((T.cand == cand) & ~T.closed).sum()), sum_net_pct=float(g.net_pct.sum()),
                          mean_net_pct=float(g.net_pct.mean()) if len(g) else None, wins=int((g.net_pct > 0).sum()),
                          verdict_at=80 if cand == "FW1" else 200)
    pd.concat(daily).to_csv(root / "out/fw_daily.csv", index=False)
    pd.concat(monthly).to_csv(root / "out/fw_monthly.csv", index=False)
    status.update(summary=summ, days=len(days))
    (root / "out/fw_status.json").write_text(json.dumps(status, indent=1, default=str), encoding="utf-8")
    log(f"forward: {json.dumps(summ)}")
    return 0 if (ok1 and ok2) else 1


if __name__ == "__main__":
    raise SystemExit(main())
