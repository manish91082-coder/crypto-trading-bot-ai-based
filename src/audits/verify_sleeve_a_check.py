"""Independent verifier of the sleeve A consistency check (logs/paper_n1/SLEEVE_A_CHECK_PROTOCOL_PREREGISTERED.md).
  python src/audits/verify_sleeve_a_check.py recompute   (laptop) V1 live stats and V2 the T2 windows / shares recomputed by
                                                         plain loops, without the check's pandas code; V3 report SHA
  python src/audits/verify_sleeve_a_check.py fidelity <ledger_snapshot.jsonl>   (VM) T3: every live sleeve-A close in L and
          the open it closes: (a) prices == spot 4h opens fetched here, (b) signal state 1 at the open, 0 at the close,
          recomputed with tf_edge_map.conditions on bars fetched and resampled here (not the engine's code)"""
import bisect
import hashlib
import json
import sys
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

R_ = Path(__file__).resolve().parents[2]
OUT = R_ / "logs" / "paper_n1" / "sleeve_a_check"
L0, L1 = datetime(2026, 10, 21, 4), datetime(2026, 10, 24, 4)
TFH = {"4h": 4, "8h": 8, "12h": 12, "1D": 24}
res = []


def ok(t, c, m):
    res.append(bool(c)); print(f"[{t} {'PASS' if c else 'FAIL'}] {m}", flush=True)


def live_closes(path):
    out, opened = [], {}
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        T = datetime.fromisoformat(r["T"])
        if T > L1:
            continue
        for a in r["actions"]:
            if a["k"][0] != "A":
                continue
            if a["a"] == "open":
                opened[a["k"]] = (T, a["px"], a["why"])
            elif a["a"] == "close" and L0 < T <= L1:
                out.append(dict(k=a["k"], T=T, px=a["px"], entry=a["entry"], t_entry=datetime.fromisoformat(a["t_entry"]), open=opened.get(a["k"])))
    return out


def recompute():
    import pandas as pd                                  # only for reading parquet; the arithmetic below is plain python
    rep = json.loads((OUT / "SLEEVE_A_CHECK_REPORT.json").read_text())
    ok("V3", hashlib.sha256((OUT / "SLEEVE_A_CHECK_REPORT.json").read_bytes()).hexdigest() == (OUT / "SLEEVE_A_CHECK_REPORT_SHA256.txt").read_text().split()[0], "report SHA == SHA file")
    lc = live_closes(OUT / "ledger_snapshot.jsonl")
    rs = [c["px"] / c["entry"] - 1 for c in lc]
    wr, mr = sum(r > 0 for r in rs) / len(rs), sum(rs) / len(rs)
    spot = json.loads((OUT / "spot_4h_live.json").read_text())["data"]
    o = {c: {int(k[0]): float(k[1]) for k in v} for c, v in spot.items()}
    ms = lambda t: int((t - datetime(1970, 1, 1)).total_seconds() * 1000)
    ml = sum(o[c][ms(L1)] / o[c][ms(L0)] - 1 for c in o) / len(o)
    L = rep["live"]
    ok("V1", len(rs) == L["n"] and abs(wr - L["win_rate"]) < 1e-12 and abs(mr - L["mean_r"]) < 1e-12 and abs(ml - L["M_live"]) < 1e-12,
       f"live: n {len(rs)} win rate {wr:.6f} mean r {mr:.6f} M_live {ml:.6f}")
    tr = pd.read_parquet(R_ / "data" / "derived" / "n1" / "trades_K1.parquet", columns=["sleeve", "tf", "entry_time", "hold", "entry", "X"])
    tr = tr[tr.sleeve == "A"]
    S0, W, SEND = datetime(2020, 3, 1, 4), timedelta(hours=72), datetime(2025, 9, 1)
    nwin = 0
    while S0 + (nwin + 1) * W <= SEND:
        nwin += 1
    agg = [[0, 0, 0.0] for _ in range(nwin)]
    for tf, et, h, en, x in zip(tr.tf, tr.entry_time, tr.hold, tr.entry, tr.X):
        ex = et.to_pydatetime() + timedelta(hours=int(h) * TFH[tf])
        j = 0 if ex <= S0 else -(-(ex - S0) // W) - 1           # ceil((ex - S0) / W) - 1
        if ex <= S0 or j >= nwin:
            continue
        r = x / en - 1
        agg[j][0] += 1; agg[j][1] += r > 0; agg[j][2] += r
    core = list(o)
    op = {}
    for c in core:
        b = pd.read_parquet(R_ / "data" / "derived" / "n1" / "bars1h" / f"{c}.parquet")["open"]
        op[c] = dict(zip([t.to_pydatetime() for t in b.index], b.values.tolist()))
    win = []
    for j in range(nwin):
        s = S0 + j * W
        vals = [op[c].get(s + W, float("nan")) / op[c].get(s, float("nan")) - 1 for c in core]
        M = sum(vals) / len(vals)
        n, w_, sr = agg[j]
        if n >= 20 and M == M:
            win.append((abs(M - ml), s, w_ / n, sr / n, M))
    win.sort(key=lambda z: (z[0], z[1]))
    m = max(30, -(-len(win) * 2 // 10))
    comp = win[:m]
    p_wr = sum(z[2] <= wr for z in comp) / m
    p_ret = sum(z[3] <= mr for z in comp) / m
    T2 = rep["T2"]
    ok("V2", len(win) == T2["n_eligible"] and m == T2["n_comparable"] and abs(p_wr - T2["p_wr"]) < 1e-12 and abs(p_ret - T2["p_ret"]) < 1e-12
       and abs(min(z[2] for z in comp) - T2["min_win_rate_comparable"]) < 1e-12,
       f"T2 by loops: eligible {len(win)} comparable {m} p_wr {p_wr:.4f} p_ret {p_ret:.4f} min comparable win rate {min(z[2] for z in comp):.4f}; "
       f"verdict {'consistent' if p_wr >= 0.05 and p_ret >= 0.05 else 'not consistent'} vs report {rep['verdict']}")


def fidelity(path):
    import numpy as np
    import pandas as pd
    sys.path.insert(0, str(R_ / "src" / "research"))
    from tf_edge_map import conditions
    FAM = ["TSMOM", "EMAX", "MACD", "DONCH", "RSI", "BB"]
    cache = {}

    def get(url):
        for k in range(4):
            try:
                return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "verify-sleeve-a"}), timeout=30).read())
            except Exception:                                    # noqa: BLE001 - network retry
                time.sleep(2 * (k + 1))
        raise RuntimeError(url)

    def bars(c, iv, T, n):                                       # n bars whose open time <= T, like the engine's request
        key = (c, iv, T)
        if key not in cache:
            step = {"4h": 14_400_000, "1d": 86_400_000}[iv]
            end, rows = int(pd.Timestamp(T).timestamp() * 1000) + step - 1, []
            while len(rows) < n:
                k = get(f"https://api.binance.com/api/v3/klines?symbol={c}&interval={iv}&endTime={end}&limit={min(1000, n - len(rows))}")
                if not k:
                    break
                rows = k + rows; end = k[0][0] - 1
                if len(k) < 1000:
                    break
            d = pd.DataFrame([r[:5] for r in rows], columns=["t", "open", "high", "low", "close"])
            d["t"] = pd.to_datetime(d.t, unit="ms")
            cache[key] = d.drop_duplicates("t").set_index("t").astype(float).sort_index()
        return cache[key]

    def sig(c, tf, fi, T):
        T = pd.Timestamp(T)
        b4 = bars(c, "4h", T, 2000); b1 = bars(c, "1d", T, 1000)
        px = float(b4.loc[T, "open"])
        b4 = b4[b4.index < T]; b1 = b1[b1.index + pd.Timedelta(days=1) <= T]
        if tf == "1D":
            b = b1
        elif tf == "4h":
            b = b4
        else:
            b = b4.resample(f"{TFH[tf]}h", label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
        b = b[b.index + pd.Timedelta(hours=TFH[tf]) <= T]
        le, lx, _, _ = conditions(b, FAM[fi])
        st, ev = 0.0, []
        for e_, x_ in zip(le.fillna(False).values, lx.fillna(False).values):  # entry wins over exit on the same bar, as defined
            st = 1.0 if e_ else (0.0 if x_ else st)
            ev.append(st)
        return px, ev, b.index[-1] + pd.Timedelta(hours=TFH[tf]) == T

    lc = live_closes(path)
    bad_px, bad_sig = [], []
    for c in lc:
        _, coin, tf, fi = c["k"].split("|")
        fi = int(fi)
        px_x, ev_x, aligned_x = sig(coin, tf, fi, c["T"])
        px_e, ev_e, aligned_e = sig(coin, tf, fi, c["t_entry"])
        if abs(px_x / c["px"] - 1) > 1e-9 or abs(px_e / c["entry"] - 1) > 1e-9:
            bad_px.append((c["k"], str(c["T"]), px_x, c["px"], px_e, c["entry"]))
        why = c["open"][2] if c["open"] else None
        good_open = ev_e[-1] == 1.0 and (ev_e[-2] == 0.0 or why == "init") and aligned_e
        good_close = ev_x[-1] == 0.0 and aligned_x
        if not (good_open and good_close):
            bad_sig.append((c["k"], str(c["t_entry"]), str(c["T"]), why, ev_e[-2:], ev_x[-2:]))
    ok("T3a", not bad_px, f"{len(lc)} closes: entry and exit prices == spot 4h opens: mismatches {len(bad_px)} {bad_px[:3]}")
    ok("T3b", not bad_sig, f"{len(lc)} closes: state 1 at the open (fresh or init), 0 at the close: mismatches {len(bad_sig)} {bad_sig[:3]}")


if __name__ == "__main__":
    if sys.argv[1] == "recompute":
        recompute()
    else:
        if len(sys.argv) > 4:                                   # forward windows (SLEEVE_A_FORWARD protocol): fidelity <ledger> <L0> <L1>
            L0, L1 = datetime.fromisoformat(sys.argv[3]), datetime.fromisoformat(sys.argv[4])
            print(f"window ({L0}, {L1}]")
        fidelity(sys.argv[2])
    print(f"TOTAL {len(res)} checks, FAIL {res.count(False)}")
    sys.exit(1 if False in res else 0)
